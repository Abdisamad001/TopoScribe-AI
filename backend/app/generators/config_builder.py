from typing import Dict, Any, List, Optional, Tuple
import re
import ipaddress
from app.models.network import Interface

_ROUTER_GI = [f"GigabitEthernet0/{i}" for i in range(2)]
_SWITCH_FA = [f"FastEthernet0/{i}" for i in range(1, 25)]
_SWITCH_GI = [f"GigabitEthernet0/{i}" for i in range(1, 3)]
_PC_FA = "FastEthernet0"


def sanitize_hostname(raw: str, used: Optional[set] = None) -> str:
    s = re.sub(r"[^A-Za-z0-9-]", "-", (raw or "").strip())
    s = re.sub(r"-+", "-", s).strip("-") or "Device"
    s = s[:63]
    if used is not None:
        base = s
        n = 2
        while s.lower() in used:
            suffix = f"-{n}"
            s = base[: 63 - len(suffix)] + suffix
            n += 1
        used.add(s.lower())
    return s

def _node_by_id(topology, node_id: str):
    return next((x for x in topology.nodes if x.id == node_id), None)

def _end_kind(node_type: str) -> str:
    t = (node_type or "").lower()
    if _is_router(t):
        return "router"
    if _is_switch(t):
        return "switch"
    if t in ("host", "pc", "laptop"):
        return "host"
    return "unknown"

def _port_free(counters, node_id: str, pool: List[str], kind: str):
    idx = counters.get(node_id, {}).get(kind, 0)
    if idx >= len(pool):
        return None
    return pool[idx]

def _port_commit(counters, node_id: str, kind: str) -> None:
    bucket = counters.setdefault(node_id, {})
    bucket[kind] = bucket.get(kind, 0) + 1

def _iface_ip_mask(o):
    if o is None:
        return None, None
    if isinstance(o, dict):
        return o.get("ip") or o.get("ip_address"), o.get("mask") or o.get("subnet_mask")
    return (
        getattr(o, "ip_address", None) or getattr(o, "ip", None),
        getattr(o, "subnet_mask", None) or getattr(o, "mask", None),
    )

def _physical(name) -> str:
    return str(name).split(".", 1)[0] if name else ""

def _assign_design_ports(topology) -> List[str]:
    errors: List[str] = []
    counters: Dict[str, Dict[str, int]] = {}
    cabling: List[Dict[str, Any]] = []
    ports_by_node: Dict[str, List[str]] = {n.id: [] for n in topology.nodes}

    def take_pair(a, b, a_pool, a_kind, b_pool, b_kind, cable, pool_a, pool_b, link):
        pa = _port_free(counters, a.id, a_pool, a_kind)
        pb = _port_free(counters, b.id, b_pool, b_kind)
        if pa is None or pb is None:
            if pa is None:
                errors.append(
                    f"Port exhaustion on {a.label or a.id}: no free port for link {link.id} "
                    f"to {b.label or b.id} ({pool_a})."
                )
            if pb is None:
                errors.append(
                    f"Port exhaustion on {b.label or b.id}: no free port for link {link.id} "
                    f"to {a.label or a.id} ({pool_b})."
                )
            return
        _port_commit(counters, a.id, a_kind)
        _port_commit(counters, b.id, b_kind)
        ports_by_node[a.id].append(pa)
        ports_by_node[b.id].append(pb)
        cabling.append({
            "link_id": link.id,
            "a_id": a.id,
            "a_port": pa,
            "b_id": b.id,
            "b_port": pb,
            "cable": cable,
        })

    for link in topology.links:
        a = _node_by_id(topology, link.source)
        b = _node_by_id(topology, link.target)
        if not a or not b:
            missing = link.source if not a else link.target
            errors.append(f"Link {link.id}: endpoint {missing} not found.")
            continue
        ka, kb = _end_kind(a.type or ""), _end_kind(b.type or "")
        if ka == "unknown" or kb == "unknown":
            errors.append(
                f"Link {link.id}: cannot assign ports between {a.label or a.id} ({a.type}) "
                f"and {b.label or b.id} ({b.type})."
            )
            continue
        pair = tuple(sorted((ka, kb)))
        if pair == ("router", "router"):
            take_pair(a, b, _ROUTER_GI, "r_gi", _ROUTER_GI, "r_gi", "copper cross-over", "1941 Gi0/0-0/1", "1941 Gi0/0-0/1", link)
        elif pair == ("router", "switch"):
            if ka == "router":
                take_pair(a, b, _ROUTER_GI, "r_gi", _SWITCH_GI, "s_gi", "copper straight-through", "1941 Gi0/0-0/1", "2960 Gi0/1-2", link)
            else:
                take_pair(a, b, _SWITCH_GI, "s_gi", _ROUTER_GI, "r_gi", "copper straight-through", "2960 Gi0/1-2", "1941 Gi0/0-0/1", link)
        elif pair == ("switch", "switch"):
            take_pair(a, b, _SWITCH_FA, "s_fa", _SWITCH_FA, "s_fa", "copper straight-through", "2960 Fa0/1-24", "2960 Fa0/1-24", link)
        elif pair == ("host", "switch"):
            if ka == "switch":
                take_pair(a, b, _SWITCH_FA, "s_fa", [_PC_FA], "pc", "copper straight-through", "2960 Fa0/1-24", "PC FastEthernet0", link)
            else:
                take_pair(a, b, [_PC_FA], "pc", _SWITCH_FA, "s_fa", "copper straight-through", "PC FastEthernet0", "2960 Fa0/1-24", link)
        elif pair == ("host", "router"):
            if ka == "router":
                take_pair(a, b, _ROUTER_GI, "r_gi", [_PC_FA], "pc", "copper straight-through", "1941 Gi0/0-0/1", "PC FastEthernet0", link)
            else:
                take_pair(a, b, [_PC_FA], "pc", _ROUTER_GI, "r_gi", "copper straight-through", "PC FastEthernet0", "1941 Gi0/0-0/1", link)
        else:
            errors.append(
                f"Link {link.id}: cannot assign ports between {a.label or a.id} ({a.type}) "
                f"and {b.label or b.id} ({b.type})."
            )

    for node in topology.nodes:
        names = ports_by_node.get(node.id) or []
        if not names:
            continue
        old = list(getattr(node, "interfaces", None) or [])
        kind = _end_kind(node.type or "")
        rebuilt: List[Interface] = []
        if kind == "host":
            ip, mask = _iface_ip_mask(old[0] if old else None)
            rebuilt.append(Interface(name=names[0], ip=ip, mask=mask))
        elif kind == "switch":
            for name in names:
                rebuilt.append(Interface(name=name))
        elif kind == "router":
            for name in names:
                ip = mask = None
                phys = _physical(name)
                for o in old:
                    oname = o.get("name") if isinstance(o, dict) else getattr(o, "name", None)
                    if _physical(oname) == phys:
                        ip, mask = _iface_ip_mask(o)
                        break
                rebuilt.append(Interface(name=name, ip=ip, mask=mask))
        else:
            continue
        node.interfaces = rebuilt

    if not isinstance(topology.metadata, dict):
        topology.metadata = {}
    topology.metadata["cabling"] = cabling
    topology.metadata["port_errors"] = list(errors)
    return errors

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

    if not out:
        out = [{"id": 1, "name": "Default"}]

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
        # Fallback Default VLAN 1: align with classic Gi0/0 gateway 192.168.1.1/24.
        if int(vid) == 1:
            out[vid] = ipaddress.IPv4Network("192.168.1.0/24")
            continue
        third = 10 + (i % 25) * 10
        start = ipaddress.IPv4Address(f"192.168.{third}.0")
        net = ipaddress.IPv4Network((start, pl), strict=False)
        out[vid] = net
    return out


def _build_switch_vlan_plan(
    topology, switch_id: str, catalog: List[Dict[str, Any]]
) -> Dict[str, Any]:
    sw = next((x for x in topology.nodes if x.id == switch_id), None)
    ports: List[Dict[str, Any]] = []
    used_vlan_ids: List[int] = []
    rr = [0]
    cabling = []
    if isinstance(topology.metadata, dict):
        cabling = list(topology.metadata.get("cabling") or [])
    for link in topology.links:
        if link.source != switch_id and link.target != switch_id:
            continue
        peer_id = link.target if link.source == switch_id else link.source
        peer = _node_by_id(topology, peer_id)
        if not peer:
            continue
        nt = peer.type or ""
        ifname = None
        for row in cabling:
            if row.get("link_id") != link.id:
                continue
            if row.get("a_id") == switch_id:
                ifname = row.get("a_port")
            elif row.get("b_id") == switch_id:
                ifname = row.get("b_port")
            break
        if not ifname:
            if isinstance(topology.metadata, dict):
                pe = topology.metadata.setdefault("port_errors", [])
                pe.append(
                    f"Switch {switch_id}: link {link.id} has no cabling port assignment."
                )
            continue

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

def _router_trunk_parent(router_node, topology=None) -> str:
    if topology is not None and isinstance(getattr(topology, "metadata", None), dict):
        for row in topology.metadata.get("cabling") or []:
            for side, port, peer_id in (
                (row.get("a_id"), row.get("a_port"), row.get("b_id")),
                (row.get("b_id"), row.get("b_port"), row.get("a_id")),
            ):
                if side != router_node.id or not port:
                    continue
                peer = _node_by_id(topology, peer_id)
                if peer and _is_switch(peer.type or ""):
                    return str(port).split(".", 1)[0]
    ifaces = getattr(router_node, "interfaces", None) or []
    if ifaces:
        name = getattr(ifaces[0], "name", None) or "GigabitEthernet0/0"
    else:
        name = "GigabitEthernet0/0"
    return str(name).split(".", 1)[0] or "GigabitEthernet0/0"


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
    users_by_vlan: Optional[Dict[int, int]] = None,
) -> None:
    if not isinstance(topology.metadata, dict):
        return
    users_by_vlan = users_by_vlan or {}
    rows: List[Dict[str, Any]] = []
    for vid in vlan_ids_in_order:
        if vid not in vlan_networks:
            continue
        net = vlan_networks[vid]
        row: Dict[str, Any] = {
            "vlan_id": int(vid),
            "gateway": str(net[1]),
            "mask": str(net.netmask),
            "network": str(net.network_address),
            "prefix_len": int(net.prefixlen),
        }
        if vid in users_by_vlan:
            row["users"] = int(users_by_vlan[vid])
        rows.append(row)
    topology.metadata["vlan_gateways"] = rows


def _write_host_addresses_metadata(topology) -> None:
    if not isinstance(topology.metadata, dict):
        return
    gw_by_vlan = {
        int(r["vlan_id"]): r
        for r in (topology.metadata.get("vlan_gateways") or [])
        if isinstance(r, dict) and r.get("vlan_id") is not None
    }
    rows: List[Dict[str, Any]] = []
    for n in topology.nodes:
        if _is_router(n.type or "") or _is_switch(n.type or ""):
            continue
        iface = (getattr(n, "interfaces", None) or [None])[0]
        ip = mask = None
        name = "FastEthernet0"
        if iface is not None:
            ip, mask = _iface_ip_mask(iface)
            iname = iface.get("name") if isinstance(iface, dict) else getattr(iface, "name", None)
            if iname:
                name = str(iname)
        vid = None
        cfg = getattr(n, "config", None) or {}
        if isinstance(cfg, dict) and cfg.get("vlan_id") is not None:
            try:
                vid = int(cfg["vlan_id"])
            except (TypeError, ValueError):
                vid = None
        gw = (gw_by_vlan.get(vid) or {}).get("gateway") if vid is not None else None
        rows.append({
            "id": n.id,
            "label": n.label or n.id,
            "interface": name,
            "ip": ip,
            "mask": mask,
            "gateway": gw,
            "vlan_id": vid,
        })
    topology.metadata["host_addresses"] = rows


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
    used_hostnames: Optional[set] = None,
    topology=None,
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
    if catalog and topology is not None and isinstance(getattr(topology, "metadata", None), dict):
        sw_uplinks = 0
        for row in topology.metadata.get("cabling") or []:
            for side, peer_id in (
                (row.get("a_id"), row.get("b_id")),
                (row.get("b_id"), row.get("a_id")),
            ):
                if side != node.id:
                    continue
                peer = _node_by_id(topology, peer_id)
                if peer and _is_switch(peer.type or ""):
                    sw_uplinks += 1
        if sw_uplinks > 1:
            pe = topology.metadata.setdefault("port_errors", [])
            pe.append(
                f"Router {node.label or node.id}: VLAN mode supports one switch uplink; "
                f"found {sw_uplinks}."
            )
    parent = _router_trunk_parent(node, topology)
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
            "hostname": sanitize_hostname(node.label or node.id, used_hostnames),
            "trunk_interfaces": trunk_interfaces,
            "subinterfaces": subinterfaces,
            "interfaces": [],
        }
    else:
        config = {
            "hostname": sanitize_hostname(node.label or node.id, used_hostnames),
            "interfaces": node_interfaces,
            "trunk_interfaces": [],
            "subinterfaces": [],
        }
    return config, subnet_counter + 1


def _build_switch_configuration(
    topology, node, catalog: List[Dict[str, Any]], used_hostnames: Optional[set] = None
) -> Dict[str, Any]:
    return {
        "hostname": sanitize_hostname(node.label or node.id, used_hostnames),
        "vlan_plan": _build_switch_vlan_plan(topology, node.id, catalog),
    }
