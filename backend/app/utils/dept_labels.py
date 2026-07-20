"""
Sanitize department names and topology labels so prompt fragments never become node titles.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Requirement-style fragments that are not department names
_JUNK_PATTERNS = [
    re.compile(r"sites?\s+in\b", re.I),
    re.compile(r"users?\s+each\b", re.I),
    re.compile(r"\beach\s+with\b", re.I),
    re.compile(r"\d+\s+sites?\b", re.I),
    re.compile(r"with\s+\d+\s+users?\b", re.I),
    re.compile(r"network\s+design\b", re.I),
    re.compile(r"\bfor\s+me\b", re.I),
    re.compile(r"\bwith\s+vlan\b", re.I),
    re.compile(r"\bin\s+each\b", re.I),
]


def is_plausible_department_name(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    n = name.strip().strip(' "\'[](){}')
    # Single-letter tokens are almost always parse noise (e.g. stray "e"), not real department names.
    if len(n) < 2 or len(n) > 48:
        return False
    if len(n.split()) > 3:
        return False
    if "(" in n or ")" in n or "." in n:
        return False
    if re.search(r"\d", n) and re.search(r"[A-Za-z]", n):
        return False
    low = n.lower()
    if low in ("vlan", "each", "sites", "site", "users", "user", "network", "eg", "e.g"):
        return False
    if low.startswith("e.g") or low.startswith("eg,"):
        return False
    for pat in _JUNK_PATTERNS:
        if pat.search(n):
            return False
    return True


def sanitize_department_name(name: str, fallback_index: int = 0) -> str:
    """Single department string for design_plan / VLAN rows."""
    if is_plausible_department_name(name):
        return name.strip()[:48]
    return f"Dept{fallback_index + 1}"


def filter_department_string_list(names: List[str]) -> List[str]:
    """Keep only plausible tokens; preserves order."""
    out: List[str] = []
    fb = 0
    for raw in names:
        if not isinstance(raw, str):
            continue
        if not is_plausible_department_name(raw):
            continue
        out.append(sanitize_department_name(raw, fb))
        fb += 1
    return out


def _clean_node_label(
    raw_label: Optional[str],
    node_type: str,
    ordinal: int,
    config: Optional[Dict[str, Any]],
) -> str:
    nt = (node_type or "").lower()
    cfg = config if isinstance(config, dict) else {}
    vlan_name = cfg.get("vlan_name")
    vid = cfg.get("vlan_id")

    label = (raw_label or "").strip()
    if label and is_plausible_department_name(label) and len(label) <= 44:
        return label[:44]

    # Prefer VLAN name from host/switch config when label is junk
    if vlan_name and is_plausible_department_name(str(vlan_name)):
        base = str(vlan_name).strip()[:28]
        if "host" in nt or "pc" in nt or "server" in nt or "laptop" in nt:
            return f"{base} Host"
        if "switch" in nt or "hub" in nt:
            return f"Access {base}"

    if "router" in nt or "gateway" in nt:
        return "Router"
    if "switch" in nt or "hub" in nt or "catalyst" in nt:
        return f"Switch {ordinal + 1}"
    if "host" in nt or "pc" in nt or "server" in nt:
        return f"Host {ordinal + 1}"
    return f"Device {ordinal + 1}"


def sanitize_topology_node_labels(topology_dict: Dict[str, Any]) -> None:
    """In-place: fix labels that contain requirement text instead of short names."""
    nodes = topology_dict.get("nodes")
    if not isinstance(nodes, list):
        return

    switch_i = 0
    host_i = 0
    router_i = 0

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nt = str(node.get("type") or "")
        cfg = node.get("config") if isinstance(node.get("config"), dict) else {}

        if _is_router(nt):
            node["label"] = _clean_node_label(node.get("label"), nt, router_i, cfg)
            router_i += 1
        elif _is_switch(nt):
            node["label"] = _clean_node_label(node.get("label"), nt, switch_i, cfg)
            switch_i += 1
        elif _is_host(nt):
            node["label"] = _clean_node_label(node.get("label"), nt, host_i, cfg)
            host_i += 1
        else:
            lbl = node.get("label")
            if not lbl or not is_plausible_department_name(str(lbl)):
                node["label"] = f"Node {router_i + switch_i + host_i}"


def _is_router(nt: str) -> bool:
    x = nt.lower()
    return "router" in x or "gateway" in x


def _is_switch(nt: str) -> bool:
    x = nt.lower()
    return "switch" in x or "hub" in x or "catalyst" in x


def _is_host(nt: str) -> bool:
    x = nt.lower()
    return "host" in x or "pc" in x or "server" in x or "laptop" in x
