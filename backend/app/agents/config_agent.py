from app.graph.state import NetworkDesignState
from typing import Dict, Any, List, Optional, Tuple
import re
import ipaddress

def _is_switch(node_type: str) -> bool:
    t = (node_type or "").lower()
    if not t:
        return False
    if t == "switch" or "switch" in t:
        return True
    if "hub" in t or "catalyst" in t or "2960" in t or "3750" in t:
        return True
    return False

def _is_router(node_type: str) -> bool:
    t = (node_type or "").lower()
    return bool(t) and ("router" in t or "gateway" in t or "firewall" in t)

def _neighbor_ids(topology, node_id: str) -> List[str]:
    out: List[str] = []
    for link in topology.links:
        if link.source == node_id:
            out.append(link.target)
        elif link.target == node_id:
            out.append(link.source)
    return out

def _normalize_vlan_entry(raw: Any) -> Optional[Tuple[int, str]]:
    if not isinstance(raw, dict):
        return None
    vid = raw.get("id")
    if vid is None:
        vid = raw.get("vlan_id")
    if vid is None:
        return None
    try:
        vid_i = int(vid)
    except (TypeError, ValueError):
        return None
    if vid_i < 2 or vid_i > 4094:
        return None
    name = raw.get("name") or raw.get("vlan_name") or f"VLAN_{vid_i}"
    return (vid_i, str(name).strip()[:64] or f"VLAN_{vid_i}")

def _primary_ip(node) -> Optional[str]:
    for iface in getattr(node, "interfaces", None) or []:
        ip = getattr(iface, "ip_address", None) or getattr(iface, "ip", None)
        if not ip:
            continue
        s = str(ip).strip()
        if s and s not in ("0.0.0.0", "no ip address"):
            return s
    return None

def vlan_catalog_from_state(topology, design_plan: Optional[dict]) -> List[Dict[str, Any]]:
    """
    Ordered VLAN catalog: from topology.metadata.vlans, then design_plan, then node hints.
    """
    seen: set = set()
    out: List[Dict[str, Any]] = []

    def add(vid: int, name: str) -> None:
        if vid in seen:
            return
        seen.add(vid)
        out.append({"id": vid, "name": name})

    md = (topology.metadata or {}) if topology else {}
    raw_vlans = md.get("vlans")
    if isinstance(raw_vlans, list):
        for item in raw_vlans:
            n = _normalize_vlan_entry(item)
            if n:
                add(n[0], n[1])

    if isinstance(design_plan, dict):
        if not out:
            dpv = design_plan.get("vlans")
            if isinstance(dpv, list):
                for item in dpv:
                    n = _normalize_vlan_entry(item)
                    if n:
                        add(n[0], n[1])
        if not out:
            depts = design_plan.get("departments")
            if isinstance(depts, list) and depts:
                for i, d in enumerate(depts):
                    if not isinstance(d, dict):
                        continue
                    name = d.get("name") or d.get("department") or f"DEPT{i + 1}"
                    vid = d.get("vlan_id")
                    if vid is None:
                        vid = 100 + i * 10
                    try:
                        vid_i = int(vid)
                    except (TypeError, ValueError):
                        continue
                    if 2 <= vid_i <= 4094:
                        add(vid_i, str(name))

    if not out:
        for n in topology.nodes:
            cfg = getattr(n, "config", None) or {}
            if isinstance(cfg, dict) and cfg.get("vlan_id") is not None:
                try:
                    vid_i = int(cfg["vlan_id"])
                except (TypeError, ValueError):
                    continue
                if 2 <= vid_i <= 4094:
                    nm = cfg.get("vlan_name") or f"VLAN_{vid_i}"
                    add(vid_i, str(nm))

    if not out:
        # Infer VLAN ids from host IPv4 third octet (e.g. 192.168.100.10 -> VLAN 100)
        for n in topology.nodes:
            nt = (n.type or "").lower()
            if _is_router(nt) or _is_switch(nt):
                continue
            ip = _primary_ip(n)
            if not ip:
                continue
            parts = ip.split(".")
            if len(parts) < 3:
                continue
            try:
                c = int(parts[2])
            except ValueError:
                continue
            if 2 <= c <= 4094:
                add(c, f"VLAN_{c}")

    return out

def _catalog_id_set(catalog: List[Dict[str, Any]]) -> set:
    return {int(v["id"]) for v in catalog}

def _match_vlan_name_in_text(text: str, catalog: List[Dict[str, Any]]) -> Optional[int]:
    t = (text or "").lower()
    if not t:
        return None
    best: Optional[Tuple[int, int]] = None  # (score, vid)
    for v in catalog:
        name = str(v.get("name", "")).lower().strip()
        if not name:
            continue
        if name in t or name.replace(" ", "_") in t:
            score = len(name)
            if best is None or score > best[0]:
                best = (score, int(v["id"]))
        tokens = re.split(r"[\s_/\-]+", name)
        for tok in tokens:
            if len(tok) >= 2 and tok in t:
                score = len(tok)
                if best is None or score > best[0]:
                    best = (score, int(v["id"]))
    return best[1] if best else None

def _host_config_vlan(node) -> Optional[int]:
    cfg = getattr(node, "config", None) or {}
    if not isinstance(cfg, dict) or cfg.get("vlan_id") is None:
        return None
    try:
        v = int(cfg["vlan_id"])
        return v if 2 <= v <= 4094 else None
    except (TypeError, ValueError):
        return None

def _access_end_devices(topology, switch_id: str) -> List[Any]:
    out: List[Any] = []
    for nid in _neighbor_ids(topology, switch_id):
        n = next((x for x in topology.nodes if x.id == nid), None)
        if not n:
            continue
        nt = n.type or ""
        if _is_router(nt):
            continue
        if _is_switch(nt):
            continue
        out.append(n)
    return out

def _resolve_vlan_for_host(
    host,
    switch_node,
    catalog: List[Dict[str, Any]],
    rr_counter: List[int],
) -> int:
    ids = _catalog_id_set(catalog)
    if not ids:
        ip = _primary_ip(host)
        if ip:
            parts = ip.split(".")
            if len(parts) >= 3:
                try:
                    c = int(parts[2])
                    if 2 <= c <= 4094:
                        return c
                except ValueError:
                    pass
        return 1

    v = _host_config_vlan(host)
    if v is not None and v in ids:
        return v

    v = _match_vlan_name_in_text(
        f"{getattr(host, 'label', '')} {getattr(host, 'id', '')}", catalog
    )
    if v is not None:
        return v

    if switch_node:
        v = _match_vlan_name_in_text(
            f"{getattr(switch_node, 'label', '')} {getattr(switch_node, 'id', '')}",
            catalog,
        )
        if v is not None:
            return v

    # Round-robin across catalog order
    order = [int(x["id"]) for x in catalog]
    idx = rr_counter[0] % len(order)
    rr_counter[0] += 1
    return order[idx]

def _vlan_rows_for_ids(used_ids: List[int], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {int(v["id"]): v["name"] for v in catalog}
    rows = []
    for vid in sorted(set(used_ids)):
        name = by_id.get(vid, f"VLAN_{vid}")
        rows.append({"id": vid, "name": name})
    return rows

def _allowed_vlans_csv(catalog: List[Dict[str, Any]]) -> str:
    return ",".join(str(int(v["id"])) for v in catalog)


def _users_by_vlan_from_plan(design_plan: Optional[dict]) -> Dict[int, int]:
    """Map vlan_id -> users from design_plan.departments (max if duplicate ids)."""
    out: Dict[int, int] = {}
    if not isinstance(design_plan, dict):
        return out
    depts = design_plan.get("departments")
    if not isinstance(depts, list):
        return out
    for d in depts:
        if not isinstance(d, dict):
            continue
        vid = d.get("vlan_id")
        if vid is None:
            continue
        try:
            vid_i = int(vid)
        except (TypeError, ValueError):
            continue
        raw = d.get("users")
        if raw is None:
            continue
        try:
            u = int(raw)
        except (TypeError, ValueError):
            continue
        prev = out.get(vid_i, 0)
        out[vid_i] = max(prev, u)
    return out


def _prefix_len_for_department_users(users: Optional[int]) -> int:
    """
    Subnet size from planned user count per department:
    ≤14 → /28, ≤30 → /26, ≤62 → /25, ≤126 → /25, else → /24.
    Missing/invalid user count defaults to /24.
    """
    if users is None or users < 0:
        return 24
    u = int(users)
    if u <= 14:
        return 28
    if u <= 30:
        return 26
    if u <= 126:
        return 25
    return 24


def _allocate_vlan_networks(
    vlan_ids: List[int],
    users_by_vlan: Dict[int, int],
) -> Dict[int, ipaddress.IPv4Network]:
    """
    Per VLAN catalog index i: network 192.168.(10 + i*10).0/<prefix>.
    Third octet steps by 10 (10, 20, 30, ...) so VLANs are separated; wraps at 25 VLANs.
    """
    out: Dict[int, ipaddress.IPv4Network] = {}
    for i, vid in enumerate(vlan_ids):
        u = users_by_vlan.get(vid)
        pl = _prefix_len_for_department_users(u if u is not None and u >= 0 else None)
        third = 10 + (i % 25) * 10
        start = ipaddress.IPv4Address(f"192.168.{third}.0")
        net = ipaddress.IPv4Network((start, pl), strict=False)
        out[vid] = net
    return out


def _build_switch_vlan_plan(
    topology, switch_id: str, catalog: List[Dict[str, Any]]
) -> Dict[str, Any]:
    sw = next((x for x in topology.nodes if x.id == switch_id), None)
    neighbors = _neighbor_ids(topology, switch_id)
    neighbors.sort()

    ports: List[Dict[str, Any]] = []
    used_vlan_ids: List[int] = []
    rr = [0]
    port_idx = 1

    for nid in neighbors:
        peer = next((x for x in topology.nodes if x.id == nid), None)
        if not peer:
            continue
        nt = peer.type or ""
        ifname = f"FastEthernet0/{port_idx}"
        port_idx += 1

        if _is_router(nt) or _is_switch(nt):
            ports.append(
                {
                    "interface": ifname,
                    "mode": "trunk",
                    "allowed_vlans_csv": _allowed_vlans_csv(catalog) if catalog else "1",
                }
            )
            continue

        vid = _resolve_vlan_for_host(peer, sw, catalog, rr)
        used_vlan_ids.append(vid)
        ports.append(
            {
                "interface": ifname,
                "mode": "access",
                "vlan_id": vid,
            }
        )

    # Trunks may carry the full catalog; VLAN DB on the switch must list every id allowed on trunks
    vlan_union = set(used_vlan_ids)
    if catalog and any(p.get("mode") == "trunk" for p in ports):
        for v in catalog:
            vlan_union.add(int(v["id"]))
    vlan_rows = (
        _vlan_rows_for_ids(sorted(vlan_union), catalog)
        if vlan_union
        else (list(catalog) if catalog else [])
    )

    return {"vlans": vlan_rows, "ports": ports}

def _router_trunk_parent(router_node) -> str:
    ifaces = getattr(router_node, "interfaces", None) or []
    if ifaces:
        return getattr(ifaces[0], "name", None) or "GigabitEthernet0/0"
    return "GigabitEthernet0/0"


def _sync_topology_vlan_catalog(topology, catalog: List[Dict[str, Any]]) -> None:
    """Write catalog ids/names onto topology.metadata.vlans (same shape as before)."""
    rows = [{"id": int(v["id"]), "name": str(v["name"])} for v in (catalog or [])]
    if isinstance(topology.metadata, dict):
        topology.metadata["vlans"] = rows
    else:
        topology.metadata = {"vlans": rows}


def _vlan_maps_from_catalog(
    catalog: Optional[List[Dict[str, Any]]],
) -> Tuple[Dict[int, str], List[int]]:
    vlan_name_by_id: Dict[int, str] = {}
    vlan_ids_in_order: List[int] = []
    for i, v in enumerate(catalog or []):
        try:
            vid = int(v["id"])
        except (TypeError, ValueError, KeyError):
            continue
        vlan_ids_in_order.append(vid)
        vlan_name_by_id[vid] = str(v.get("name") or f"VLAN_{vid}")
    return vlan_name_by_id, vlan_ids_in_order


def _write_vlan_gateways_metadata(
    topology,
    vlan_ids_in_order: List[int],
    vlan_networks: Dict[int, Any],
) -> None:
    if not isinstance(topology.metadata, dict):
        return
    topology.metadata["vlan_gateways"] = [
        {
            "vlan_id": int(vid),
            "gateway": str(vlan_networks[vid][1]),
            "mask": str(vlan_networks[vid].netmask),
        }
        for vid in vlan_ids_in_order
        if vid in vlan_networks
    ]


def _collect_host_nodes(topology) -> List[Any]:
    host_nodes: List[Any] = []
    for n in topology.nodes:
        nt = (n.type or "").lower()
        if _is_router(nt) or _is_switch(nt):
            continue
        host_nodes.append(n)
    return host_nodes


def _connected_switch_for_host(topology, host) -> Any:
    for nid in _neighbor_ids(topology, host.id):
        sn = next((x for x in topology.nodes if x.id == nid), None)
        if sn and _is_switch(sn.type or ""):
            return sn
    return None


def _assign_host_vlan_membership(
    topology,
    host_nodes: List[Any],
    catalog: List[Dict[str, Any]],
    vlan_name_by_id: Dict[int, str],
    rr: List[int],
) -> Dict[int, List[Any]]:
    """Assign VLAN membership + vlan config on each host; return hosts_by_vlan."""
    hosts_by_vlan: Dict[int, List[Any]] = {}
    for h in host_nodes:
        connected_switch = _connected_switch_for_host(topology, h)
        vid = _resolve_vlan_for_host(h, connected_switch, catalog or [], rr)
        # Write back host config for downstream generators (frontend report + VLAN name lookups)
        h.config = {
            "vlan_id": int(vid),
            "vlan_name": vlan_name_by_id.get(int(vid), f"VLAN_{int(vid)}"),
        }
        hosts_by_vlan.setdefault(int(vid), []).append(h)
    return hosts_by_vlan


def _apply_host_interface_address(host, ip: str, mask: str) -> None:
    """Write host IP/mask using the same field names as the original config_node."""
    if getattr(host, "interfaces", None):
        if len(host.interfaces) > 0:
            host.interfaces[0].ip_address = ip
            host.interfaces[0].subnet_mask = mask
    else:
        host.interfaces = [{"name": "eth0", "ip": ip, "mask": mask}]


def _assign_host_ips_from_networks(
    hosts_by_vlan: Dict[int, List[Any]],
    vlan_ids_in_order: List[int],
    vlan_networks: Dict[int, Any],
) -> None:
    """Host IPs: gateway is net[1]; assign hosts from remaining usable addresses in order."""
    for vid in vlan_ids_in_order:
        net = vlan_networks.get(vid)
        if not net:
            continue
        mask = str(net.netmask)
        usable = list(net.hosts())
        if len(usable) < 2:
            continue
        host_addrs = usable[1:]
        vlan_hosts = hosts_by_vlan.get(vid) or []
        vlan_hosts.sort(key=lambda x: x.id)
        for i, h in enumerate(vlan_hosts):
            if i < len(host_addrs):
                ip = str(host_addrs[i])
            else:
                ip = str(host_addrs[i % len(host_addrs)])
            _apply_host_interface_address(h, ip, mask)


def _build_router_configuration(
    node,
    catalog: List[Dict[str, Any]],
    vlan_ids_in_order: List[int],
    vlan_networks: Dict[int, Any],
    subnet_base: str,
    subnet_counter: int,
) -> Tuple[Dict[str, Any], int]:
    """
    Build one router's configuration dict and advance subnet_counter exactly as before.
    Returns (config, next_subnet_counter).
    """
    node_interfaces = []
    for idx, interface in enumerate(node.interfaces):
        ip = f"{subnet_base}.{subnet_counter}.{idx + 1}"
        mask = "255.255.255.0"
        interface.ip_address = ip
        interface.subnet_mask = mask
        node_interfaces.append(
            {"name": interface.name, "ip": ip, "mask": mask}
        )
    parent = _router_trunk_parent(node)
    subinterfaces = []
    trunk_interfaces = []
    if catalog:
        trunk_interfaces.append(
            {
                "name": parent,
                "allowed_vlans_csv": _allowed_vlans_csv(catalog),
            }
        )
        # Same iteration order as _allocate_vlan_networks (vlan_ids_in_order); use
        # vlan_networks[vid] so each subinterface matches that VLAN's gateway + mask.
        for vid in vlan_ids_in_order:
            net = vlan_networks.get(vid)
            if not net:
                continue
            subinterfaces.append(
                {
                    "parent": parent,
                    "vlan_id": int(vid),
                    "ip": str(net[1]),
                    "mask": str(net.netmask),
                }
            )
        config = {
            "hostname": node.label or node.id,
            "trunk_interfaces": trunk_interfaces,
            "subinterfaces": subinterfaces,
            "interfaces": [],
        }
    else:
        config = {
            "hostname": node.label or node.id,
            "interfaces": node_interfaces,
            "trunk_interfaces": [],
            "subinterfaces": [],
        }
    return config, subnet_counter + 1


def _build_switch_configuration(topology, node, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "hostname": node.label or node.id,
        "vlan_plan": _build_switch_vlan_plan(topology, node.id, catalog),
    }


def config_node(state: NetworkDesignState) -> Dict[str, Any]:
    topology = state.get("topology")
    if topology is None:
        return {
            "errors": ["Configuration skipped: topology is missing from state."],
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "Configuration skipped because topology generation did not produce a topology.",
                }
            ],
        }

    design_plan = state.get("design_plan") or {}

    catalog = vlan_catalog_from_state(topology, design_plan if isinstance(design_plan, dict) else {})

    # Ensure frontend has the VLAN catalog (names/ids) even if topology_agent omitted metadata merge.
    _sync_topology_vlan_catalog(topology, catalog)

    # Assign each host to a VLAN id and a valid subnet sized from design_plan users per department.
    vlan_name_by_id, vlan_ids_in_order = _vlan_maps_from_catalog(catalog)

    plan_dict = design_plan if isinstance(design_plan, dict) else {}
    users_by_vlan = _users_by_vlan_from_plan(plan_dict)
    vlan_networks = _allocate_vlan_networks(vlan_ids_in_order, users_by_vlan)
    _write_vlan_gateways_metadata(topology, vlan_ids_in_order, vlan_networks)

    # Hosts that don't match anything will be assigned in deterministic RR order.
    rr = [0]
    host_nodes = _collect_host_nodes(topology)
    hosts_by_vlan = _assign_host_vlan_membership(
        topology, host_nodes, catalog or [], vlan_name_by_id, rr
    )
    _assign_host_ips_from_networks(hosts_by_vlan, vlan_ids_in_order, vlan_networks)

    configurations: Dict[str, Any] = {}
    subnet_base = "192.168"
    subnet_counter = 1

    for node in topology.nodes:
        if node.type == "router":
            configurations[node.id], subnet_counter = _build_router_configuration(
                node,
                catalog,
                vlan_ids_in_order,
                vlan_networks,
                subnet_base,
                subnet_counter,
            )

    for node in topology.nodes:
        if not _is_switch(node.type or ""):
            continue
        configurations[node.id] = _build_switch_configuration(topology, node, catalog)

    return {
        "configurations": configurations,
        "topology": topology,
        "conversation_history": [{"role": "assistant", "content": "Configuration complete."}],
    }
