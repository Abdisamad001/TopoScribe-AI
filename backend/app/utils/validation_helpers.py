
from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Optional, Tuple

Addr = Tuple[str, str, ipaddress.IPv4Address]  # (device_id, role, ip)
Net = Tuple[str, ipaddress.IPv4Network]  # (label, network)

_RFC1918 = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)


def _parse_ip(raw: Any) -> Optional[ipaddress.IPv4Address]:
    if raw is None or raw == "" or raw == "no ip address":
        return None
    try:
        return ipaddress.IPv4Address(str(raw).strip())
    except (ValueError, TypeError):
        return None


def _parse_network_from_host(ip_raw: Any, mask_raw: Any) -> Optional[ipaddress.IPv4Network]:
    ip = _parse_ip(ip_raw)
    if ip is None or not mask_raw:
        return None
    try:
        return ipaddress.IPv4Network(f"{ip}/{str(mask_raw).strip()}", strict=False)
    except (ValueError, TypeError):
        return None


def _is_rfc1918(net: ipaddress.IPv4Network) -> bool:
    return any(net.subnet_of(block) or net == block for block in _RFC1918)


def _host_addrs_from_topology(topology) -> List[Addr]:
    rows: List[Addr] = []
    meta = getattr(topology, "metadata", None) or {}
    ha = meta.get("host_addresses") if isinstance(meta, dict) else None
    if isinstance(ha, list) and ha:
        for h in ha:
            if not isinstance(h, dict):
                continue
            ip = _parse_ip(h.get("ip"))
            if ip is None:
                continue
            rows.append((str(h.get("id") or h.get("label") or "?"), "host", ip))
        return rows
    for n in getattr(topology, "nodes", []) or []:
        nt = (getattr(n, "type", None) or "").lower()
        if "router" in nt or "switch" in nt or "catalyst" in nt or "hub" in nt:
            continue
        for iface in getattr(n, "interfaces", None) or []:
            ip_raw = getattr(iface, "ip_address", None) or getattr(iface, "ip", None)
            if isinstance(iface, dict):
                ip_raw = iface.get("ip_address") or iface.get("ip")
            ip = _parse_ip(ip_raw)
            if ip is not None:
                rows.append((str(getattr(n, "id", "?")), "host", ip))
                break
    return rows


def _collect_invalid_ip_errors(topology, configurations: Dict[str, Any]) -> List[str]:
    """Non-empty IP strings that fail IPv4Address parsing."""
    errors: List[str] = []

    def consider(device_id: str, raw: Any) -> None:
        if raw is None or raw == "" or raw == "no ip address":
            return
        if _parse_ip(raw) is None:
            errors.append(f"IP conflict / invalid IP: {raw} on {device_id}")

    for node_id, config in (configurations or {}).items():
        if not isinstance(config, dict):
            continue
        for iface in config.get("interfaces") or []:
            if isinstance(iface, dict):
                consider(node_id, iface.get("ip"))
        for s in config.get("subinterfaces") or []:
            if isinstance(s, dict):
                consider(node_id, s.get("ip"))
        consider(node_id, config.get("management_ip"))

    meta = getattr(topology, "metadata", None) or {}
    if isinstance(meta, dict):
        for h in meta.get("host_addresses") or []:
            if isinstance(h, dict):
                consider(str(h.get("id") or h.get("label") or "?"), h.get("ip"))
    return errors


def collect_addresses_and_networks(
    topology, configurations: Dict[str, Any]
) -> Tuple[List[Addr], List[Net]]:
    addrs: List[Addr] = []
    nets: List[Net] = []
    for node_id, config in (configurations or {}).items():
        if not isinstance(config, dict):
            continue
        for iface in config.get("interfaces") or []:
            if not isinstance(iface, dict):
                continue
            ip = _parse_ip(iface.get("ip"))
            if ip is not None:
                addrs.append((node_id, "interface", ip))
            net = _parse_network_from_host(iface.get("ip"), iface.get("mask"))
            if net is not None:
                nets.append((f"{node_id} interface", net))
        for s in config.get("subinterfaces") or []:
            if not isinstance(s, dict):
                continue
            ip = _parse_ip(s.get("ip"))
            if ip is not None:
                addrs.append((node_id, f"subinterface vlan {s.get('vlan_id')}", ip))
            net = _parse_network_from_host(s.get("ip"), s.get("mask"))
            if net is not None:
                nets.append((f"{node_id} vlan {s.get('vlan_id')}", net))
        mip = _parse_ip(config.get("management_ip"))
        if mip is not None:
            addrs.append((node_id, "management", mip))
            if config.get("management_mask"):
                mnet = _parse_network_from_host(
                    config.get("management_ip"), config.get("management_mask")
                )
                if mnet is not None:
                    nets.append((f"{node_id} management", mnet))

    addrs.extend(_host_addrs_from_topology(topology))

    meta = getattr(topology, "metadata", None) or {}
    if isinstance(meta, dict):
        for g in meta.get("vlan_gateways") or []:
            if not isinstance(g, dict):
                continue
            net = _parse_network_from_host(g.get("gateway"), g.get("mask"))
            if net is not None:
                nets.append((f"vlan_gateway {g.get('vlan_id')}", net))
    return addrs, nets


def check_ip_and_subnet_conflicts(topology, configurations: Dict[str, Any]) -> List[str]:
    """Duplicates, invalid IPs, RFC1918, management vs data-plane, overlapping subnets."""
    errors = _collect_invalid_ip_errors(topology, configurations or {})
    addrs, nets = collect_addresses_and_networks(topology, configurations or {})

    for label, net in nets:
        if not _is_rfc1918(net):
            errors.append(
                f"IP conflict: subnet {label} ({net}) is outside RFC 1918 private space"
            )

    seen: Dict[ipaddress.IPv4Address, Addr] = {}
    for device_id, role, ip in addrs:
        if ip in seen:
            o_id, o_role, _ = seen[ip]
            errors.append(
                f"IP conflict: {ip} on {device_id} ({role}) "
                f"already used by {o_id} ({o_role})"
            )
        else:
            seen[ip] = (device_id, role, ip)

    data_plane = [(label, net) for label, net in nets if "management" not in label]
    mgmt_nets = [(label, net) for label, net in nets if "management" in label]

    for node_id, config in (configurations or {}).items():
        if not isinstance(config, dict):
            continue
        mip = _parse_ip(config.get("management_ip"))
        if mip is None:
            continue
        for label, net in nets:
            if mip == net.network_address or mip == net.broadcast_address:
                errors.append(
                    f"IP conflict: management IP {mip} on {node_id} "
                    f"is network/broadcast of {label} ({net})"
                )
        for label, net in data_plane:
            if mip in net:
                errors.append(
                    f"IP conflict: management IP {mip} on {node_id} "
                    f"falls inside data-plane subnet {label} ({net})"
                )

    # Management networks must be strictly disjoint from every data-plane subnet
    
    for ml, mn in mgmt_nets:
        for dl, dn in data_plane:
            if mn == dn or mn.overlaps(dn):
                errors.append(
                    f"Subnet overlap: management network {ml} ({mn}) "
                    f"conflicts with data-plane {dl} ({dn})"
                )

    for i in range(len(nets)):
        la, na = nets[i]
        for j in range(i + 1, len(nets)):
            lb, nb = nets[j]
            if na == nb:
                # Identical nets: only error if a management side is involved
                if ("management" in la) or ("management" in lb):
                    errors.append(
                        f"Subnet overlap: {la} ({na}) equals {lb} ({nb})"
                    )
                continue
            if na.overlaps(nb):
                errors.append(
                    f"Subnet overlap: {la} ({na}) overlaps {lb} ({nb})"
                )
    return errors
