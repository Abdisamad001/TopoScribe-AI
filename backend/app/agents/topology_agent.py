from app.graph.state import NetworkDesignState
from app.models.network import Topology
from app.utils.llm import call_llm
from app.utils.dept_labels import sanitize_department_name, sanitize_topology_node_labels
from typing import Dict, Any, List, Optional, Tuple
import json

# Escalated retries allowed after the initial primary-tier attempt.
MAX_TOPOLOGY_RETRIES = 3

def _effective_department_count(design_plan: Optional[Dict[str, Any]]) -> int:
    """How many department segments the SME layout should have (min 1)."""
    if not isinstance(design_plan, dict):
        return 3
    raw = design_plan.get("departments")
    if isinstance(raw, list) and raw:
        n = sum(1 for d in raw if isinstance(d, dict))
        return max(n, 1)
    return 3


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
    The LLM often returns a short path (router–core–one access–one host) even when the plan
    has several departments. Returns what is missing, or None when the shape fits the plan.
    """
    n_depts = _effective_department_count(design_plan)
    expected_nodes = 2 + 2 * n_depts
    nodes = topology_dict.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return (
            f"No nodes were returned; {n_depts} department(s) need at least "
            f"{expected_nodes} nodes."
        )
    if len(nodes) < expected_nodes:
        return (
            f"Only {len(nodes)} nodes for {n_depts} department(s); expected at least "
            f"{expected_nodes} (1 router + 1 core switch + 1 access switch and 1 host "
            f"per department)."
        )
    _r, sw, ho = _count_roles_in_nodes(nodes)
    if ho < n_depts:
        return (
            f"Only {ho} host(s) for {n_depts} department(s); every department needs its "
            f"own host."
        )
    if sw < n_depts + 1:
        return (
            f"Only {sw} switch(es) for {n_depts} department(s); expected {n_depts + 1} "
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

def _fallback_topology_dict(design_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic SME topology when LLM output cannot be parsed or validated.
    Single router, core switch, one access switch + host per department.
    """
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
            depts.append({"name": nm, "vlan_id": min(max(vi, 2), 4094)})
    if not depts:
        depts = [
            {"name": "HR", "vlan_id": 10},
            {"name": "IT", "vlan_id": 20},
            {"name": "Finance", "vlan_id": 30},
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
    for i, d in enumerate(depts):
        vid = int(d["vlan_id"])
        name = str(d["name"])
        sid = f"SW_ACC_{i + 1}"
        hid = f"H{i + 1}"
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
        nodes.append(
            {
                "id": hid,
                "type": "host",
                "label": f"{name} Host",
                "interfaces": [
                    {"name": "Ethernet0", "ip": f"192.168.{vid}.10", "mask": "255.255.255.0"}
                ],
                "config": {"vlan_id": vid, "vlan_name": name},
                "x": x,
                "y": 550,
            }
        )
        links.append({"id": f"link-core-{sid}", "source": "SW_CORE", "target": sid, "bandwidth": 1000})
        links.append({"id": f"link-{sid}-{hid}", "source": sid, "target": hid, "bandwidth": 1000})
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
    _depts = design_plan.get("departments")
    if not isinstance(_depts, list) or len(_depts) == 0:
        _depts = [{"users": 20}]
    _max_dept_users = max(
        (d.get("users", 20) if isinstance(d, dict) else 20) for d in _depts
    )

    prompt = f"""You are a network topology generation agent.

Design plan:
{json.dumps(design_plan, indent=2)}

Generate a network topology with:
- Routers, switches, hosts as needed
- If the design plan describes a SINGLE site / single campus, use exactly ONE router (one logical L3 device). Do not add separate "Edge Router" and "Core Router" pairs for a single-site design.
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
    - Core Switches below (y=200)
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
        )
        if r
    ]
    if reasons:
        return None, reasons
    return topology_dict, []


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
    spacing_x = 300

    # Function to position a row
    def position_row(items, y_level):
        total_width = (len(items) - 1) * spacing_x
        current_x = start_x + (1000 - total_width) / 2 # Center align roughly
        if current_x < 100: current_x = 100

        for i, node in enumerate(items):
            node["x"] = int(current_x + (i * spacing_x))
            node["y"] = y_level
            # Remove nested position if LLM put it there
            if "position" in node:
                del node["position"]

    # Apply positions
    position_row(routers, 0)
    position_row(switches, 200)
    position_row(others, 400) # Firewalls etc
    position_row(hosts, 500)

    sanitize_topology_node_labels(topology_dict)

    return Topology(**topology_dict)  # Pydantic validation


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
        sanitize_topology_node_labels(topology_dict)
        topology = Topology(**topology_dict)
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
