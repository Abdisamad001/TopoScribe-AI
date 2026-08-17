from app.graph.state import NetworkDesignState
from app.models.network import Topology
from app.utils.llm import call_llm
from app.utils.dept_labels import sanitize_department_name, sanitize_topology_node_labels
from app.agents.planning_agent import LITERAL_HOST_NODE_THRESHOLD
from typing import Dict, Any, List, Optional, Tuple
import json

# Escalated retries allowed after the initial primary-tier attempt.
MAX_TOPOLOGY_RETRIES = 3

# HostNode.tsx uses Tailwind `w-48` (12rem = 192px at the default 16px root).
# React Flow positions are the node's top-left, so sibling centers/left-edges
# must be at least this wide plus a small gutter or the cards overlap.
HOST_CARD_WIDTH_PX = 192
HOST_GAP_MARGIN_PX = 16
HOST_CLUSTER_GUTTER_PX = 24
DEFAULT_COLUMN_SPACING_PX = 300


def _host_center_gap() -> int:
    """Left-edge to left-edge distance that keeps two host cards from overlapping."""
    return HOST_CARD_WIDTH_PX + HOST_GAP_MARGIN_PX


def _departmental_column_spacing(max_hosts_in_cluster: int) -> int:
    """
    Access-switch column spacing so the widest host cluster still clears
    its neighbor. Shrinking host_gap below card width would reintroduce
    intra-cluster overlap, so wide clusters widen the columns instead.
    """
    n = max(1, int(max_hosts_in_cluster))
    needed = (n - 1) * _host_center_gap() + HOST_CARD_WIDTH_PX + HOST_CLUSTER_GUTTER_PX
    return max(DEFAULT_COLUMN_SPACING_PX, needed)


def _plan_mode(design_plan: Optional[Dict[str, Any]]) -> str:
    """Return 'flat_inventory' or 'departmental'."""
    if isinstance(design_plan, dict) and design_plan.get("mode") == "flat_inventory":
        return "flat_inventory"
    return "departmental"


def _effective_department_count(design_plan: Optional[Dict[str, Any]]) -> int:
    """How many department segments the SME layout should have (min 1)."""
    if not isinstance(design_plan, dict):
        return 3
    raw = design_plan.get("departments")
    if isinstance(raw, list) and raw:
        n = sum(1 for d in raw if isinstance(d, dict))
        return max(n, 1)
    return 3


def _host_nodes_for_department(dept: Dict[str, Any]) -> int:
    """
    How many host nodes to draw for one department.
    Small literal device counts use host_nodes; otherwise one representative.
    """
    raw = dept.get("host_nodes") if isinstance(dept, dict) else None
    if raw is None:
        return 1
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 1
    if 1 <= n <= LITERAL_HOST_NODE_THRESHOLD:
        return n
    return 1


def _expected_departmental_hosts(design_plan: Optional[Dict[str, Any]]) -> int:
    if not isinstance(design_plan, dict):
        return _effective_department_count(design_plan)
    raw = design_plan.get("departments")
    if not isinstance(raw, list) or not raw:
        return _effective_department_count(design_plan)
    total = 0
    for d in raw:
        if isinstance(d, dict):
            total += _host_nodes_for_department(d)
    return max(total, 1)


def _flat_inventory_targets(
    design_plan: Optional[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """Stated (routers, switches, hosts) for flat_inventory plans."""
    if not isinstance(design_plan, dict):
        return 0, 0, 0
    try:
        r = max(0, int(design_plan.get("router_count") or 0))
    except (TypeError, ValueError):
        r = 0
    try:
        s = max(0, int(design_plan.get("switch_count") or 0))
    except (TypeError, ValueError):
        s = 0
    try:
        h = max(0, int(design_plan.get("host_count") or 0))
    except (TypeError, ValueError):
        h = 0
    return r, s, h


def _count_roles_in_nodes(nodes: Any) -> Tuple[int, int, int]:
    """Returns (router_count, switch_count, host_count)."""
    r, s, h = 0, 0, 0
    if not isinstance(nodes, list):
        return r, s, h
    for n in nodes:
        if not isinstance(n, dict):
            continue
        t = str(n.get("type", "")).lower()
        if "router" in t or "gateway" in t or "firewall" in t:
            r += 1
        elif "switch" in t or "hub" in t:
            s += 1
        elif "host" in t or "pc" in t or "server" in t or "laptop" in t:
            h += 1
    return r, s, h


def _sparse_reason(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    Returns what is missing vs the plan shape, or None when the inventory fits.
    Flat inventory plans are checked against stated device counts; departmental
    plans keep the SME 1-router / core+access / host-nodes-per-dept formula.
    """
    nodes = topology_dict.get("nodes")
    if _plan_mode(design_plan) == "flat_inventory":
        er, es, eh = _flat_inventory_targets(design_plan)
        expected_nodes = er + es + eh
        if not isinstance(nodes, list) or not nodes:
            return (
                f"No nodes were returned; flat inventory needs {er} router(s), "
                f"{es} switch(es), and {eh} host(s) ({expected_nodes} nodes)."
            )
        ar, asw, ah = _count_roles_in_nodes(nodes)
        missing = []
        if ar < er:
            missing.append(f"routers {ar}/{er}")
        if asw < es:
            missing.append(f"switches {asw}/{es}")
        if ah < eh:
            missing.append(f"hosts {ah}/{eh}")
        if missing:
            return "Flat inventory short of stated device counts: " + ", ".join(missing) + "."
        return None

    n_depts = _effective_department_count(design_plan)
    expected_hosts = _expected_departmental_hosts(design_plan)
    expected_switches = n_depts + 1
    expected_nodes = 1 + expected_switches + expected_hosts
    if not isinstance(nodes, list) or not nodes:
        return (
            f"No nodes were returned; {n_depts} department(s) need at least "
            f"{expected_nodes} nodes."
        )
    if len(nodes) < expected_nodes:
        return (
            f"Only {len(nodes)} nodes for {n_depts} department(s); expected at least "
            f"{expected_nodes} (1 router + 1 core switch + 1 access switch per "
            f"department and {expected_hosts} host node(s) total)."
        )
    _r, sw, ho = _count_roles_in_nodes(nodes)
    if ho < expected_hosts:
        return (
            f"Only {ho} host(s); expected at least {expected_hosts} host node(s) "
            f"for {n_depts} department(s)."
        )
    if sw < expected_switches:
        return (
            f"Only {sw} switch(es) for {n_depts} department(s); expected {expected_switches} "
            f"(1 core switch + 1 access switch per department)."
        )
    return None


def _topology_too_sparse_for_plan(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> bool:
    return _sparse_reason(topology_dict, design_plan) is not None


def _allowed_department_names(design_plan: Optional[Dict[str, Any]]) -> set:
    allowed: set = set()
    if not isinstance(design_plan, dict):
        return allowed
    raw = design_plan.get("departments")
    if not isinstance(raw, list):
        return allowed
    for d in raw:
        if not isinstance(d, dict):
            continue
        nm = d.get("name") or d.get("department")
        if nm:
            allowed.add(str(nm).strip().lower())
    return allowed


def _is_core_infrastructure_node(node: Dict[str, Any]) -> bool:
    t = str(node.get("type", "")).lower()
    lbl = str(node.get("label", "")).lower()
    if "router" in t or "gateway" in t or "firewall" in t:
        return True
    if ("switch" in t or "hub" in t) and "core" in lbl:
        return True
    return False


def _node_vlan_department(node: Dict[str, Any]) -> Optional[str]:
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
    vn = cfg.get("vlan_name")
    if vn is not None and str(vn).strip():
        return str(vn).strip().lower()
    return None


def _department_scope_items(
    topology_dict: Dict[str, Any], allowed: set
) -> Tuple[List[str], set]:
    """Returns (out-of-scope descriptions, department names actually present)."""
    unexpected: List[str] = []
    present: set = set()

    md = topology_dict.get("metadata")
    if isinstance(md, dict):
        vlans = md.get("vlans")
        if isinstance(vlans, list):
            for item in vlans:
                if not isinstance(item, dict):
                    continue
                raw = str(item.get("name") or item.get("vlan_name") or "").strip()
                if not raw:
                    continue
                if raw.lower() in allowed:
                    present.add(raw.lower())
                else:
                    unexpected.append(f"VLAN {item.get('id')} '{raw}'")

    nodes = topology_dict.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _is_core_infrastructure_node(node):
                continue
            t = str(node.get("type", "")).lower()
            if not (
                "host" in t
                or "pc" in t
                or "server" in t
                or "laptop" in t
                or "switch" in t
                or "hub" in t
            ):
                continue
            dept = _node_vlan_department(node)
            if dept is None:
                continue
            if dept in allowed:
                present.add(dept)
            else:
                unexpected.append(f"node '{node.get('id')}' assigned to '{dept}'")

    return unexpected, present


def _scope_reason(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> Optional[str]:
    """Names the VLANs/nodes outside design_plan.departments, or None when in scope."""
    if _plan_mode(design_plan) == "flat_inventory":
        return None
    allowed = _allowed_department_names(design_plan)
    if not allowed:
        return None
    unexpected, _present = _department_scope_items(topology_dict, allowed)
    if not unexpected:
        return None
    return (
        "Departments not in the design plan: "
        + "; ".join(unexpected[:6])
        + ". Only these are allowed: "
        + ", ".join(sorted(allowed))
        + "."
    )


def _missing_department_reason(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> Optional[str]:
    """Names plan departments that got no VLAN and no node, or None when all present."""
    if _plan_mode(design_plan) == "flat_inventory":
        return None
    allowed = _allowed_department_names(design_plan)
    if not allowed:
        return None
    _unexpected, present = _department_scope_items(topology_dict, allowed)
    missing = allowed - present
    if not missing:
        return None
    return (
        "Missing departments (no VLAN and no node created): "
        + ", ".join(sorted(missing))
        + "."
    )


def _missing_host_link_reason(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    Every host must appear as source or target of at least one link.
    Departmental designs expect that link to an access switch; flat inventory
    allows switch or router (the prompt connects hosts to a router when no
    switch exists). The check itself is only: host id present in the links list.
    """
    nodes = topology_dict.get("nodes")
    if not isinstance(nodes, list):
        return None

    host_ids: List[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        t = str(node.get("type") or "").lower()
        if not ("host" in t or "pc" in t or "server" in t or "laptop" in t):
            continue
        hid = node.get("id")
        if hid:
            host_ids.append(str(hid))
    if not host_ids:
        return None

    linked: set = set()
    links = topology_dict.get("links")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            for key in ("source", "target", "sourceNodeId", "targetNodeId"):
                val = link.get(key)
                if val:
                    linked.add(str(val))

    missing = [hid for hid in host_ids if hid not in linked]
    if not missing:
        return None

    if _plan_mode(design_plan) == "flat_inventory":
        clause = "has no link to a switch or router"
    else:
        clause = "has no link to an access switch"
    return " ".join(f"Host {hid} {clause}." for hid in missing).rstrip(".")


def _topology_department_scope_invalid(
    topology_dict: Dict[str, Any], design_plan: Optional[Dict[str, Any]]
) -> bool:
    """
    True when topology references departments/VLANs outside design_plan.departments.
    """
    return _scope_reason(topology_dict, design_plan) is not None


def _norm_vlan_item(item: Any) -> Optional[Tuple[int, str]]:
    if not isinstance(item, dict):
        return None
    vid = item.get("id")
    if vid is None:
        vid = item.get("vlan_id")
    if vid is None:
        return None
    try:
        v = int(vid)
    except (TypeError, ValueError):
        return None
    if v < 2 or v > 4094:
        return None
    name = item.get("name") or item.get("vlan_name") or f"VLAN_{v}"
    return (v, str(name).strip()[:64])

def _fallback_flat_inventory_dict(design_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic topology from stated router/switch/host counts."""
    er, es, eh = _flat_inventory_targets(design_plan)
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    router_ids: List[str] = []
    for i in range(er):
        rid = f"R{i + 1}"
        router_ids.append(rid)
        nodes.append(
            {
                "id": rid,
                "type": "router",
                "label": f"Router {i + 1}",
                "interfaces": [
                    {
                        "name": "GigabitEthernet0/0",
                        "ip": f"192.168.1.{i + 1}",
                        "mask": "255.255.255.0",
                    }
                ],
                "config": {},
                "x": 100 + i * 300,
                "y": 0,
            }
        )

    switch_ids: List[str] = []
    for i in range(es):
        sid = f"SW{i + 1}"
        switch_ids.append(sid)
        nodes.append(
            {
                "id": sid,
                "type": "switch",
                "label": f"Switch {i + 1}",
                "interfaces": [],
                "config": {},
                "x": 100 + i * 300,
                "y": 200,
            }
        )

    host_ids: List[str] = []
    for i in range(eh):
        hid = f"PC{i + 1}"
        host_ids.append(hid)
        nodes.append(
            {
                "id": hid,
                "type": "host",
                "label": f"PC{i + 1}",
                "interfaces": [
                    {
                        "name": "Ethernet0",
                        "ip": f"192.168.10.{10 + i}",
                        "mask": "255.255.255.0",
                    }
                ],
                "config": {},
                "x": 100 + i * 250,
                "y": 500,
            }
        )

    # Simple hierarchy: routers ↔ first switch (or first host), switches ↔ hosts.
    uplink = switch_ids[0] if switch_ids else (host_ids[0] if host_ids else None)
    if uplink:
        for rid in router_ids:
            links.append(
                {
                    "id": f"link-{rid}-{uplink}",
                    "source": rid,
                    "target": uplink,
                    "bandwidth": 1000,
                }
            )
    for i, sid in enumerate(switch_ids):
        if i == 0:
            continue
        links.append(
            {
                "id": f"link-{switch_ids[0]}-{sid}",
                "source": switch_ids[0],
                "target": sid,
                "bandwidth": 1000,
            }
        )
    access = switch_ids[0] if switch_ids else (router_ids[0] if router_ids else None)
    if access:
        for hid in host_ids:
            links.append(
                {
                    "id": f"link-{access}-{hid}",
                    "source": access,
                    "target": hid,
                    "bandwidth": 1000,
                }
            )

    return {
        "nodes": nodes,
        "links": links,
        "protocols": [{"name": "ospf", "parameters": {"area": 0}}],
        "metadata": {"vlans": []},
    }


def _fallback_topology_dict(design_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic topology when LLM output cannot be parsed or validated.
    Flat inventory uses stated device counts; departmental uses the SME campus shape.
    """
    if _plan_mode(design_plan) == "flat_inventory":
        return _fallback_flat_inventory_dict(design_plan)

    depts: List[Dict[str, Any]] = []
    raw = design_plan.get("departments") if isinstance(design_plan, dict) else None
    if isinstance(raw, list):
        for i, d in enumerate(raw):
            if not isinstance(d, dict):
                continue
            nm = sanitize_department_name(
                str(d.get("name") or d.get("department") or ""), i
            )
            vid = d.get("vlan_id") if d.get("vlan_id") is not None else (10 * (i + 1))
            try:
                vi = int(vid)
            except (TypeError, ValueError):
                vi = 100 + i * 10
            if vi < 2:
                vi = 10 + i * 10
            depts.append(
                {
                    "name": nm,
                    "vlan_id": min(max(vi, 2), 4094),
                    "host_nodes": _host_nodes_for_department(d),
                }
            )
    if not depts:
        depts = [
            {"name": "HR", "vlan_id": 10, "host_nodes": 1},
            {"name": "IT", "vlan_id": 20, "host_nodes": 1},
            {"name": "Finance", "vlan_id": 30, "host_nodes": 1},
        ]

    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    nodes.append(
        {
            "id": "R1",
            "type": "router",
            "label": "Router",
            "interfaces": [{"name": "GigabitEthernet0/0", "ip": "192.168.1.1", "mask": "255.255.255.0"}],
            "config": {},
            "x": 400,
            "y": 0,
        }
    )
    nodes.append(
        {
            "id": "SW_CORE",
            "type": "switch",
            "label": "Core Switch",
            "interfaces": [],
            "config": {},
            "x": 400,
            "y": 200,
        }
    )
    links.append({"id": "link-r-core", "source": "R1", "target": "SW_CORE", "bandwidth": 1000})

    x = 100
    host_global = 0
    for i, d in enumerate(depts):
        vid = int(d["vlan_id"])
        name = str(d["name"])
        sid = f"SW_ACC_{i + 1}"
        nodes.append(
            {
                "id": sid,
                "type": "switch",
                "label": f"Access {name}",
                "interfaces": [],
                "config": {"vlan_id": vid, "vlan_name": name},
                "x": x,
                "y": 400,
            }
        )
        links.append({"id": f"link-core-{sid}", "source": "SW_CORE", "target": sid, "bandwidth": 1000})
        n_hosts = int(d.get("host_nodes") or 1)
        for hi in range(n_hosts):
            host_global += 1
            hid = f"H{host_global}"
            nodes.append(
                {
                    "id": hid,
                    "type": "host",
                    "label": f"{name} Host {hi + 1}" if n_hosts > 1 else f"{name} Host",
                    "interfaces": [
                        {
                            "name": "Ethernet0",
                            "ip": f"192.168.{vid}.{10 + hi}",
                            "mask": "255.255.255.0",
                        }
                    ],
                    "config": {"vlan_id": vid, "vlan_name": name},
                    "x": x + hi * 40,
                    "y": 550,
                }
            )
            links.append(
                {"id": f"link-{sid}-{hid}", "source": sid, "target": hid, "bandwidth": 1000}
            )
        x += 300

    vlans = [{"id": int(d["vlan_id"]), "name": str(d["name"])} for d in depts]
    return {
        "nodes": nodes,
        "links": links,
        "protocols": [{"name": "ospf", "parameters": {"area": 0}}],
        "metadata": {"vlans": vlans},
    }


def merge_vlan_metadata(design_plan: Dict[str, Any], topology_dict: Dict[str, Any]) -> None:
    """
    Ensure topology.metadata.vlans exists from design_plan when the LLM omitted it.
    """
    md = topology_dict.setdefault("metadata", {})
    raw = md.get("vlans")
    if isinstance(raw, list) and len(raw) > 0:
        return
    if not isinstance(design_plan, dict):
        return
    out: List[Dict[str, Any]] = []
    seen = set()

    def add(vid: int, name: str) -> None:
        if vid in seen:
            return
        seen.add(vid)
        out.append({"id": vid, "name": name})

    dpv = design_plan.get("vlans")
    if isinstance(dpv, list):
        for item in dpv:
            n = _norm_vlan_item(item)
            if n:
                add(n[0], n[1])
    depts = design_plan.get("departments")
    if isinstance(depts, list):
        for i, d in enumerate(depts):
            if not isinstance(d, dict):
                continue
            name = d.get("name") or d.get("department") or f"DEPT{i + 1}"
            vid = d.get("vlan_id")
            if vid is None:
                vid = 100 + i * 10
            try:
                vi = int(vid)
            except (TypeError, ValueError):
                continue
            if 2 <= vi <= 4094:
                add(vi, str(name))
    if out:
        md["vlans"] = out

def _build_topology_prompt(
    design_plan: Dict[str, Any], prior_errors: Optional[List[str]] = None
) -> str:
    """Generation prompt, with the previous attempt's rejection reasons when retrying."""
    if _plan_mode(design_plan) == "flat_inventory":
        er, es, eh = _flat_inventory_targets(design_plan)
        prompt = f"""You are a network topology generation agent.

Design plan (FLAT INVENTORY mode):
{json.dumps(design_plan, indent=2)}

Generate a network topology that matches the stated device inventory EXACTLY:
- Create exactly {er} router node(s) (type "router").
- Create exactly {es} switch node(s) (type "switch").
- Create exactly {eh} host node(s) (type "host").
- Do NOT invent departments, VLANs, a core-switch hierarchy, or extra devices.
- Connect devices sensibly (routers to switches, switches to hosts; if there is no switch, connect hosts to a router).
- Hierarchical spatial layout: routers near y=0, switches near y=200, hosts near y=500+.
- Spread devices horizontally with at least 200px gap. Assign private IPv4 addresses to routers and hosts.
- metadata.vlans may be an empty list.

Output a JSON object matching this schema:
{{
  "nodes": [
    {{
      "id": "R1",
      "type": "router",
      "label": "Router 1",
      "interfaces": [
          {{ "name": "eth0", "ip": "192.168.1.1", "mask": "255.255.255.0" }}
      ],
      "config": {{}},
      "x": 100,
      "y": 0
    }}
  ],
  "links": [
    {{
      "id": "link1",
      "source": "R1",
      "target": "SW1",
      "bandwidth": 1000
    }}
  ],
  "protocols": [
    {{
      "name": "ospf",
      "parameters": {{"area": 0}}
    }}
  ],
  "metadata": {{
    "vlans": []
  }}
}}

Output ONLY valid JSON, no markdown.
"""
    else:
        _depts = design_plan.get("departments")
        if not isinstance(_depts, list) or len(_depts) == 0:
            _depts = [{"users": 20, "host_nodes": 1}]
        _max_dept_users = max(
            (d.get("users", 20) if isinstance(d, dict) else 20) for d in _depts
        )
        host_lines = []
        for d in _depts:
            if not isinstance(d, dict):
                continue
            hn = _host_nodes_for_department(d)
            host_lines.append(
                f"  - {d.get('name', 'Dept')}: create exactly {hn} host node(s)"
            )
        host_inventory = "\n".join(host_lines) or "  - one host per department"
        expected_hosts = _expected_departmental_hosts(design_plan)
        n_depts = _effective_department_count(design_plan)

        prompt = f"""You are a network topology generation agent.

Design plan (DEPARTMENTAL / SME mode):
{json.dumps(design_plan, indent=2)}

Generate a network topology with:
- Required device inventory. For N={n_depts} departments the design MUST contain, as separate nodes:
    - Exactly ONE router. If the design plan describes a SINGLE site / single campus, use exactly ONE router (one logical L3 device). Do not add separate "Edge Router" and "Core Router" pairs for a single-site design.
    - Exactly ONE dedicated core switch, labelled "Core Switch". This is an ADDITIONAL node on top of the per-department access switches below — it is never one of them, and it must never be omitted.
    - Exactly ONE access switch per department listed in design_plan.departments.
    - Host nodes per department (honour design_plan.departments[].host_nodes when present; otherwise one representative host per department):
{host_inventory}
  Total host nodes must be {expected_hosts}. Do NOT create one host per "users" count when host_nodes is absent — "users" sizes subnets only.
- Connect the topology in that hierarchy: each host connects to its own department's access switch, every access switch connects up to the single core switch, and only the core switch connects up to the router. Do NOT connect access switches directly to the router.
- VLANs MUST match the design plan: use the same VLAN IDs and department names as in design_plan.vlans or design_plan.departments (if present). If the plan lists N departments, create N access VLANs with those ids/names and assign each department's hosts and access switch accordingly.
- ONLY create nodes for departments listed in design_plan.departments. Do NOT add any other departments, VLANs, access switches, or hosts beyond that list.
- On each host node, set "config": {{"vlan_id": <number>, "vlan_name": "<same as catalog>"}} matching that host's department VLAN.
- Put the full VLAN catalog in metadata.vlans as [{{"id": <int 2-4094>, "name": "<string>"}}, ...] covering every department VLAN in the design.
- Use distinct private IPv4 subnets per VLAN.
  Calculate the subnet size from the number of users per department:
  - Up to 30 users: use /26 (62 hosts)
  - 31 to 62 users: use /25 (126 hosts)
  - 63 to 126 users: use /24 (254 hosts)
  Each department in this design has {_max_dept_users} users.
  Use 192.168.<vlan_id>.0 as the base network for each department with the matching mask on hosts; routers use subinterfaces toward switches (do not rely on a fixed 10/20/30 scheme unless the user asked for it).
- Proper connections between devices
- Hierarchical spatial layout:
    - Routers at the top (y=0 to y=100)
    - The core switch below the router (y=200)
    - Access Switches further below (y=400)
    - Hosts/Servers at the bottom (y=600+)
    - Spread devices horizontally (x-axis) with at least 250px gap between them to avoid overlap.
    - Do NOT place nodes at the exact same coordinates.
    - IMPORTANT: You MUST assign valid private IP addresses (e.g. 192.168.x.x) to all Routers and Hosts.

Output a JSON object matching this schema:
{{
  "nodes": [
    {{
      "id": "R1",
      "type": "router",
      "label": "Edge Router",
      "interfaces": [
          {{ "name": "eth0", "ip": "192.168.1.1", "mask": "255.255.255.0" }}
      ],
      "config": {{}},
      "x": 100,
      "y": 100
    }},
    ...
  ],
  "links": [
    {{
      "id": "link1",
      "source": "R1",
      "target": "SW1",
      "bandwidth": 1000
    }},
    ...
  ],
  "protocols": [
    {{
      "name": "ospf",
      "parameters": {{"area": 0}}
    }}
  ],
  "metadata": {{
    "vlans": [
      {{"id": 100, "name": "ExampleDept"}}
    ]
  }}
}}

Output ONLY valid JSON, no markdown.
"""

    if prior_errors:
        numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(prior_errors))
        prompt += f"""
A previous attempt was REJECTED by automated validation for these specific reasons:
{numbered}

Return a corrected topology that resolves every point listed above.
"""
    return prompt


def _parse_and_validate_topology(
    raw_text: str, design_plan: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Returns (topology_dict, []) when the output is usable, or (None, reasons)
    describing exactly why it was rejected.
    """
    clean_text = (raw_text or "").replace("```json", "").replace("```", "").strip()
    try:
        topology_dict = json.loads(clean_text)
    except json.JSONDecodeError as e:
        return None, [f"Response was not valid JSON: {e}"]

    if not isinstance(topology_dict, dict):
        return None, [
            f"Response JSON was a {type(topology_dict).__name__}, expected an object "
            f"with nodes and links."
        ]

    merge_vlan_metadata(design_plan or {}, topology_dict)

    reasons = [
        r
        for r in (
            _sparse_reason(topology_dict, design_plan),
            _scope_reason(topology_dict, design_plan),
            _missing_department_reason(topology_dict, design_plan),
            _missing_host_link_reason(topology_dict, design_plan),
        )
        if r
    ]
    if reasons:
        return None, reasons
    return topology_dict, []


def _access_switch_id_for_host(
    host: Dict[str, Any],
    access_by_id: Dict[str, Dict[str, Any]],
    links: List[Any],
) -> Optional[str]:
    """Which access switch this host hangs off, via link first, then VLAN config."""
    hid = host.get("id")
    for link in links:
        if not isinstance(link, dict):
            continue
        a = link.get("source") or link.get("sourceNodeId")
        b = link.get("target") or link.get("targetNodeId")
        if a == hid and b in access_by_id:
            return b
        if b == hid and a in access_by_id:
            return a

    cfg = host.get("config") if isinstance(host.get("config"), dict) else {}
    vlan_name = str(cfg.get("vlan_name") or "").strip().lower()
    vlan_id = cfg.get("vlan_id")
    for sid, sw in access_by_id.items():
        sc = sw.get("config") if isinstance(sw.get("config"), dict) else {}
        sw_name = str(sc.get("vlan_name") or "").strip().lower()
        if vlan_name and sw_name and vlan_name == sw_name:
            return sid
        if vlan_id is None or sc.get("vlan_id") is None:
            continue
        try:
            if int(vlan_id) == int(sc.get("vlan_id")):
                return sid
        except (TypeError, ValueError):
            continue
    return None


def _group_hosts_by_access_switch(
    hosts: List[Dict[str, Any]],
    access_switches: List[Dict[str, Any]],
    links: List[Any],
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Returns (switch_id -> hosts, unmatched hosts)."""
    access_by_id = {s.get("id"): s for s in access_switches if s.get("id")}
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    unmatched: List[Dict[str, Any]] = []
    for host in hosts:
        sid = _access_switch_id_for_host(host, access_by_id, links)
        if sid is None:
            unmatched.append(host)
        else:
            grouped.setdefault(sid, []).append(host)
    return grouped, unmatched


def _position_hosts_under_access_switches(
    hosts: List[Dict[str, Any]],
    access_switches: List[Dict[str, Any]],
    links: List[Any],
    y_level: int,
    position_row,
) -> None:
    """
    Place each department's hosts on the host row, centered under that
    department's access switch. Unmatched hosts keep the flat-row fallback.
    """
    access_by_id = {s.get("id"): s for s in access_switches if s.get("id")}
    grouped, unmatched = _group_hosts_by_access_switch(hosts, access_switches, links)

    host_gap = _host_center_gap()
    for sid, group in grouped.items():
        center_x = int(access_by_id[sid].get("x") or 0)
        n = len(group)
        start_x = center_x - ((n - 1) * host_gap) / 2
        for i, host in enumerate(group):
            host["x"] = int(start_x + i * host_gap)
            host["y"] = y_level
            if "position" in host:
                del host["position"]

    if unmatched:
        position_row(unmatched, y_level)


def _finalize_topology(
    topology_dict: Dict[str, Any], design_plan: Dict[str, Any]
) -> Topology:
    """Applies the deterministic layout, cleans labels, and validates the schema."""
    nodes = topology_dict.get("nodes", [])

    # Group by type (case-insensitive)
    routers = []
    switches = []
    hosts = []
    others = []

    for n in nodes:
        t = n.get("type", "").lower()
        if "router" in t or "gateway" in t or "firewall" in t:
            routers.append(n)
        elif "switch" in t or "hub" in t:
            switches.append(n)
        elif "host" in t or "pc" in t or "server" in t or "laptop" in t:
            hosts.append(n)
        else:
            others.append(n)

    # Layout parameters
    start_x = 100
    spacing_x = DEFAULT_COLUMN_SPACING_PX

    # Function to position a row
    def position_row(items, y_level, col_spacing=None):
        gap = spacing_x if col_spacing is None else col_spacing
        total_width = (len(items) - 1) * gap
        current_x = start_x + (1000 - total_width) / 2 # Center align roughly
        if current_x < 100: current_x = 100

        for i, node in enumerate(items):
            node["x"] = int(current_x + (i * gap))
            node["y"] = y_level
            # Remove nested position if LLM put it there
            if "position" in node:
                del node["position"]

    # Apply positions. Departmental mode is four tiers (router → core → access → hosts);
    # flat inventory has no core/access split, so every switch stays on one row.
    position_row(routers, 0)
    if _plan_mode(design_plan) == "departmental":
        core_switches = [s for s in switches if _is_core_infrastructure_node(s)]
        access_switches = [s for s in switches if not _is_core_infrastructure_node(s)]
        links = topology_dict.get("links") if isinstance(topology_dict.get("links"), list) else []
        grouped, _unmatched = _group_hosts_by_access_switch(
            hosts, access_switches, links
        )
        max_cluster = max((len(g) for g in grouped.values()), default=1)
        column_spacing = _departmental_column_spacing(max_cluster)
        position_row(core_switches, 200)
        position_row(access_switches, 400, column_spacing)
        position_row(others, 400)
        _position_hosts_under_access_switches(
            hosts, access_switches, links, 500, position_row
        )
    else:
        position_row(switches, 200)
        position_row(others, 400)
        position_row(hosts, 500)

    sanitize_topology_node_labels(topology_dict)
    _annotate_representative_host_user_counts(topology_dict, design_plan)

    return Topology(**topology_dict)  # Pydantic validation


def _match_host_to_representative_users(
    node: Dict[str, Any],
    by_vlan_name: Dict[str, Tuple[str, int]],
    by_vlan_id: Dict[int, Tuple[str, int]],
) -> Optional[Tuple[str, int]]:
    """
    Resolve a host to (department_name, users) when that department is a
    representative (collapsed) user-count department. Prefer VLAN config;
    fall back to a label that starts with the department name.
    """
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}

    vlan_name = cfg.get("vlan_name")
    if vlan_name is not None:
        key = str(vlan_name).strip().lower()
        if key in by_vlan_name:
            return by_vlan_name[key]

    vlan_id = cfg.get("vlan_id")
    if vlan_id is not None:
        try:
            vid = int(vlan_id)
        except (TypeError, ValueError):
            vid = None
        if vid is not None and vid in by_vlan_id:
            return by_vlan_id[vid]

    label = str(node.get("label") or "").strip()
    if label:
        low = label.lower()
        for dept_key, value in by_vlan_name.items():
            if low == dept_key or low.startswith(dept_key + " "):
                return value
    return None


def _annotate_representative_host_user_counts(
    topology_dict: Dict[str, Any], design_plan: Dict[str, Any]
) -> None:
    """
    When a department is drawn as one representative host (no host_nodes) and
    its stated user count is above LITERAL_HOST_NODE_THRESHOLD, append
    "(N PCs)" to that host's label so the canvas shows what the node stands for.

    Flat-inventory plans and departments with explicit small host_nodes are left alone.
    """
    if _plan_mode(design_plan) != "departmental":
        return

    depts = design_plan.get("departments") if isinstance(design_plan, dict) else None
    if not isinstance(depts, list) or not depts:
        return

    by_vlan_name: Dict[str, Tuple[str, int]] = {}
    by_vlan_id: Dict[int, Tuple[str, int]] = {}
    for d in depts:
        if not isinstance(d, dict):
            continue
        # Literal host draws already show individually — no count suffix.
        if d.get("host_nodes") is not None:
            continue
        try:
            users = int(d.get("users", 0))
        except (TypeError, ValueError):
            continue
        if users <= LITERAL_HOST_NODE_THRESHOLD:
            continue
        name = str(d.get("name") or d.get("department") or "").strip()
        if not name:
            continue
        by_vlan_name[name.lower()] = (name, users)
        try:
            vid = int(d["vlan_id"])
        except (TypeError, ValueError, KeyError):
            continue
        by_vlan_id[vid] = (name, users)

    if not by_vlan_name and not by_vlan_id:
        return

    nodes = topology_dict.get("nodes")
    if not isinstance(nodes, list):
        return

    for node in nodes:
        if not isinstance(node, dict):
            continue
        t = str(node.get("type") or "").lower()
        if not ("host" in t or "pc" in t or "server" in t or "laptop" in t):
            continue
        matched = _match_host_to_representative_users(node, by_vlan_name, by_vlan_id)
        if matched is None:
            continue
        dept_name, users = matched
        node["label"] = f"{dept_name} Host ({users} PCs)"


def _prior_topology_errors(state: NetworkDesignState) -> List[str]:
    """Rejection reasons recorded by earlier topology attempts in this run."""
    out: List[str] = []
    for entry in state.get("agent_trace") or []:
        if not isinstance(entry, dict) or entry.get("agent") != "topology":
            continue
        outcome = entry.get("outcome")
        if outcome and entry.get("status") != "success":
            out.append(str(outcome))
    return out


def _trace(model: str, attempt: int, status: str, outcome: str) -> Dict[str, Any]:
    return {
        "agent": "topology",
        "model": model,
        "attempt": attempt,
        "status": status,
        "outcome": outcome,
    }


def topology_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Topology Agent: Converts design plan into network topology.

    Attempt 0 runs on the primary tier. Attempts 1-3 escalate, each prompted with
    the specific reasons earlier attempts were rejected. The deterministic layout
    is only used once the retry budget is exhausted.
    """
    design_plan = state.get("design_plan") or {}
    attempt = int(state.get("topology_retry_count", 0) or 0)
    tier = "primary" if attempt == 0 else "escalated"
    prior_errors = _prior_topology_errors(state)

    prompt = _build_topology_prompt(design_plan, prior_errors)

    try:
        response_text = call_llm(prompt, tier=tier)
    except Exception as e:
        reasons = [str(e)]
    else:
        topology_dict, reasons = _parse_and_validate_topology(response_text, design_plan)
        if topology_dict is not None:
            try:
                topology = _finalize_topology(topology_dict, design_plan)
            except Exception as e:
                reasons = [f"Topology failed schema validation: {e}"]
            else:
                source = "groq" if attempt == 0 else "openai_escalated"
                return {
                    "topology": topology,
                    "topology_source": source,
                    "topology_quality_ok": True,
                    "topology_retry_count": attempt,
                    "agent_trace": [_trace(tier, attempt, "success", f"accepted from {source}")],
                    "conversation_history": [
                        {
                            "role": "assistant",
                            "content": f"Topology generated successfully (attempt {attempt + 1}, {source}).",
                        }
                    ],
                }

    reason_text = " | ".join(reasons) if reasons else "Unknown topology failure."

    if attempt < MAX_TOPOLOGY_RETRIES:
        # Hand control back to the graph so the next attempt can escalate with
        # this reason in its prompt. No fallback while retries remain.
        return {
            "topology_quality_ok": False,
            "topology_retry_count": attempt + 1,
            "agent_trace": [_trace(tier, attempt, "rejected", reason_text)],
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": f"Topology attempt {attempt + 1} rejected: {reason_text}",
                }
            ],
        }

    # Retry budget exhausted — fall back to the deterministic SME layout.
    try:
        topology_dict = _fallback_topology_dict(design_plan)
        merge_vlan_metadata(design_plan, topology_dict)
        topology = _finalize_topology(topology_dict, design_plan)
    except Exception as e:
        return {
            "topology_quality_ok": False,
            "topology_retry_count": attempt + 1,
            "errors": [f"Topology generation failed: {reason_text}"],
            "agent_trace": [_trace(tier, attempt, "failed", f"{reason_text} | fallback also failed: {e}")],
            "conversation_history": [
                {"role": "assistant", "content": f"Error: {reason_text}"}
            ],
        }

    return {
        "topology": topology,
        "topology_source": "deterministic_fallback",
        "topology_quality_ok": False,
        "topology_retry_count": attempt + 1,
        "agent_trace": [_trace(tier, attempt, "fallback", reason_text)],
        "conversation_history": [
            {
                "role": "assistant",
                "content": "Topology generated using built-in SME layout after "
                f"{attempt + 1} rejected attempts.",
            }
        ],
    }
