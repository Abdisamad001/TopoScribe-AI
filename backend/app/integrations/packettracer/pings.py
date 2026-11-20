"""Generic ping-pair derivation for TopoScribe topologies."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.integrations.packettracer.mapper import host_ip_gateway


def _host_nodes(topology: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for n in topology.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        t = (n.get("type") or "").lower()
        if t == "host" or t == "pc" or "host" in t:
            out.append(n)
    return out


def derive_ping_pairs(topology: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Returns list of (from_device_id, to_ip).
    1) each host -> its gateway
    2) one host per VLAN -> every other VLAN host IP (inter-VLAN)
    """
    hosts = _host_nodes(topology)
    pairs: List[Tuple[str, str]] = []
    seen = set()

    def add(src: str, dst: str) -> None:
        key = (src, dst)
        if key in seen or not src or not dst:
            return
        seen.add(key)
        pairs.append((src, dst))

    by_vlan: Dict[int, Dict[str, Any]] = {}
    for h in hosts:
        info = host_ip_gateway(h, topology)
        if not info:
            continue
        hid = str(h["id"])
        if info.get("gateway"):
            add(hid, info["gateway"])
        cfg = h.get("config") if isinstance(h.get("config"), dict) else {}
        try:
            vid = int(cfg.get("vlan_id"))
        except (TypeError, ValueError):
            continue
        if vid not in by_vlan:
            by_vlan[vid] = {"id": hid, "ip": info["ip"]}

    vlan_hosts = list(by_vlan.values())
    for i, a in enumerate(vlan_hosts):
        for j, b in enumerate(vlan_hosts):
            if i == j:
                continue
            add(str(a["id"]), str(b["ip"]))

    return pairs
