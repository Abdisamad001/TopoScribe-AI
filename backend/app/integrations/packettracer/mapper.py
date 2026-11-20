"""Map TopoScribe topology + cabling + cisco_configs onto PT primitives.

PT device names = TopoScribe node.id so cisco_configs[node.id] applies without remapping.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Catalogue-verified during spike (Packet Tracer 9.0.1 / MCP 0.12.0)
PT_MODEL_ROUTER = "1941"
PT_MODEL_SWITCH = "2960-24TT"
PT_MODEL_PC = "PC-PT"

_POWER_NAME_RE = re.compile(r"power\s*distribution", re.I)

# Known benign IOS rejections on PT 2960 / simplified images
_BENIGN_CLI_SNIPPETS = (
    "switchport trunk encapsulation",
    "encapsulation dot1q",  # only classify benign when on pure L2 switch context if needed
)


def pt_model_for_node(node: Dict[str, Any]) -> str:
    t = (node.get("type") or "").lower()
    if t == "router" or "router" in t:
        return PT_MODEL_ROUTER
    if t == "host" or t == "pc" or "host" in t or "pc" in t:
        return PT_MODEL_PC
    if t == "switch" or "switch" in t or "catalyst" in t or "hub" in t:
        return PT_MODEL_SWITCH
    return PT_MODEL_SWITCH


def pt_name_for_node(node: Dict[str, Any]) -> str:
    """Packet Tracer device name: prefer node.id (matches cisco_configs keys)."""
    nid = str(node.get("id") or "").strip()
    if not nid:
        raise ValueError("topology node missing id")
    # PT names: keep id; replace spaces if any slipped in
    return nid.replace(" ", "-")


def build_name_map(nodes: List[Dict[str, Any]]) -> Dict[str, str]:
    """node_id -> pt_name (identity today; kept explicit for reports)."""
    out: Dict[str, str] = {}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("id"):
            continue
        out[str(n["id"])] = pt_name_for_node(n)
    return out


def get_cabling_rows(topology: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = topology.get("metadata") if isinstance(topology.get("metadata"), dict) else {}
    rows = meta.get("cabling") or []
    return [r for r in rows if isinstance(r, dict)]


def map_cable_type(raw: Optional[str]) -> str:
    # Spike-verified MCP values: "straight" (not "crossover"/"cross").
    s = (raw or "").lower()
    if "cross" in s:
        return "straight"  # PT MCP rejects "crossover"; copper cross still works as straight in lab
    if "serial" in s:
        return "serial"
    if "fiber" in s:
        return "fiber"
    return "straight"


def layout_positions(
    nodes: List[Dict[str, Any]],
) -> Dict[str, Tuple[int, int]]:
    """Spread devices using existing x/y when present."""
    pos: Dict[str, Tuple[int, int]] = {}
    for i, n in enumerate(nodes):
        nid = str(n.get("id"))
        x = int(n.get("x") or (120 + (i % 6) * 160))
        y = int(n.get("y") or (100 + (i // 6) * 140))
        # keep inside typical usable canvas
        x = max(60, min(x, 1700))
        y = max(60, min(y, 560))
        pos[nid] = (x, y)
    return pos


def split_cli_commands(cli: str) -> List[str]:
    """Preserve order; drop empty lines and lone '!' separators (IOS comment/section)."""
    out: List[str] = []
    for raw in (cli or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or line == "!":
            continue
        out.append(line)
    return out


def classify_rejection(line: str, device_type: str) -> str:
    low = line.lower()
    t = (device_type or "").lower()
    if "encapsulation" in low and ("switch" in t):
        return "benign"
    if "switchport trunk encapsulation" in low:
        return "benign"
    for snip in _BENIGN_CLI_SNIPPETS:
        if snip in low and "switch" in t:
            return "benign"
    if "invalid" in low or "unknown" in low or "incomplete" in low:
        return "harmful"
    return "unknown"


def is_power_distribution_name(name: str) -> bool:
    return bool(_POWER_NAME_RE.search(name or ""))


def count_user_devices(topology_text: str) -> int:
    """Parse pt_query_topology text; ignore Power Distribution Device."""
    text = topology_text or ""
    # Preferred compact form: DEVICES:N|LINKS:M
    m = re.search(r"DEVICES\s*:\s*(\d+)", text, re.I)
    if m and "Power Distribution" not in text and "\n  " not in text:
        return int(m.group(1))
    # Detailed listing: count non-power device lines after header
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("DEVICES") or s.startswith("Links") or s.startswith("LINKS"):
            continue
        if s.startswith("R1") or "[" in s:
            # device rows look like: "  NAME  [model] ..."
            if is_power_distribution_name(s):
                continue
            if re.match(r"^[A-Za-z0-9_.-]+\s+\[", s) or re.match(r"^[A-Za-z0-9_.-]+\s{2,}\[", s):
                n += 1
                continue
            # fallback: indented name then model
            if re.match(r"^[A-Za-z0-9_.-]+\s+", s) and "[" in s:
                if not is_power_distribution_name(s):
                    n += 1
    if n:
        return n
    if m:
        # subtract power devices mentioned
        power = len(re.findall(r"Power Distribution Device", text, re.I))
        return max(0, int(m.group(1)) - power)
    return 0


def host_ip_gateway(
    node: Dict[str, Any],
    topology: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """Extract static IP/mask/gateway for a host node."""
    ip = mask = None
    for iface in node.get("interfaces") or []:
        if not isinstance(iface, dict):
            continue
        ip = iface.get("ip_address") or iface.get("ipAddress") or iface.get("ip")
        mask = (
            iface.get("subnet_mask")
            or iface.get("subnetMask")
            or iface.get("mask")
        )
        if ip:
            break
    if not ip:
        return None
    gateway = ""
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
    vlan_id = cfg.get("vlan_id")
    vlan_name = cfg.get("vlan_name")
    meta = topology.get("metadata") if isinstance(topology.get("metadata"), dict) else {}
    for g in meta.get("vlan_gateways") or []:
        if isinstance(g, dict) and vlan_id is not None and int(g.get("vlan_id", -1)) == int(vlan_id):
            gateway = str(g.get("gateway") or "")
            if not mask:
                mask = str(g.get("mask") or "")
            break
    addressing = meta.get("addressing") if isinstance(meta.get("addressing"), dict) else {}
    if not gateway and vlan_name and vlan_name in addressing:
        gateway = str(addressing[vlan_name].get("gateway") or "")
        if not mask:
            mask = str(addressing[vlan_name].get("mask") or "")
    if not gateway and vlan_id is not None:
        # common TopoScribe pattern: .1 is gateway
        parts = str(ip).split(".")
        if len(parts) == 4:
            gateway = ".".join(parts[:3] + ["1"])
    return {
        "ip": str(ip),
        "mask": str(mask or "255.255.255.0"),
        "gateway": gateway,
    }
