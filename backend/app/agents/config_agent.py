from app.graph.state import NetworkDesignState
from typing import Dict, Any, List, Optional, Tuple
import re

# Department VLANs (must match topology_agent / SME scope)
_DEPARTMENT_VLANS: Tuple[Tuple[int, str], ...] = (
    (10, "HR"),
    (20, "IT"),
    (30, "Finance"),
)
_VID_BY_NAME = {name: vid for vid, name in _DEPARTMENT_VLANS}
_VIDS_ORDER = [vid for vid, _ in _DEPARTMENT_VLANS]

def _is_switch(node_type: str) -> bool:
    """Match topology_agent grouping: switch, hub, catalyst, and common vendor tokens."""
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

def _department_vlan_from_node(node) -> Optional[int]:
    """Map HR / IT / Finance from label or id; returns None if unknown."""
    text = f"{getattr(node, 'label', None) or ''} {getattr(node, 'id', None) or ''}".lower()
    if re.search(r"\b(hr|human[\s_-]?resources)\b", text):
        return _VID_BY_NAME["HR"]
    if re.search(r"\b(it|information[\s_-]?technology|help[\s_-]?desk|infotech)\b", text):
        return _VID_BY_NAME["IT"]
    if re.search(r"\b(finance|accounting|accounts)\b", text):
        return _VID_BY_NAME["Finance"]
    return None

def _primary_ip(node) -> Optional[str]:
    """First usable IPv4 on node interfaces (topology often uses 192.168.{10|20|30}.x)."""
    for iface in getattr(node, "interfaces", None) or []:
        ip = getattr(iface, "ip_address", None) or getattr(iface, "ip", None)
        if not ip:
            continue
        s = str(ip).strip()
        if s and s not in ("0.0.0.0", "no ip address"):
            return s
    return None

def _vlan_from_subnet(ip: str) -> Optional[int]:
    """192.168.10.x -> VLAN 10; 20 -> 20; 30 -> 30 (department /24 scheme)."""
    parts = ip.strip().split(".")
    if len(parts) < 3:
        return None
    try:
        third = int(parts[2])
        if third in (10, 20, 30):
            return third
    except ValueError:
        pass
    return None

def _access_end_devices(topology, switch_id: str) -> List[Any]:
    """
    Neighbors that should get access ports: not router uplink, not another L2/L3 switch.
    Catches host/pc/server and LLM variants (workstation, desktop, end, etc.).
    """
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

def _build_vlan_plan_for_switch(topology, switch_id: str) -> Dict[str, Any]:
    """
    Always define VLANs 10=HR, 20=IT, 30=Finance on the switch.
    Assign each access (end-device) port using:
    1) host IP third octet (192.168.10.x -> VLAN 10),
    2) host/switch label keywords,
    3) access-switch departmental name (e.g. 'Access Switch HR' -> all hosts VLAN 10),
    4) round-robin 10/20/30.
    """
    vlans = [{"id": vid, "name": name} for vid, name in _DEPARTMENT_VLANS]

    sw = next((x for x in topology.nodes if x.id == switch_id), None)
    sw_dept_vlan = _department_vlan_from_node(sw) if sw else None

    end_nodes = _access_end_devices(topology, switch_id)
    # Stable order for Fa0/1, Fa0/2, ...
    end_nodes.sort(key=lambda n: n.id)

    assignments: List[Dict[str, Any]] = []
    rr = 0
    for n in end_nodes:
        vid: Optional[int] = None
        pip = _primary_ip(n)
        if pip:
            vid = _vlan_from_subnet(pip)
        if vid is None:
            vid = _department_vlan_from_node(n)
        if vid is None and sw_dept_vlan is not None:
            vid = sw_dept_vlan
        if vid is None:
            vid = _VIDS_ORDER[rr % len(_VIDS_ORDER)]
            rr += 1
        assignments.append({"neighbor_node_id": n.id, "vlan_id": int(vid)})

    return {
        "vlans": vlans,
        "access_assignments": assignments,
    }

def config_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Configuration Agent: Assigns IPs and protocol parameters.
    """
    
    topology = state["topology"]
    
    # IP assignment logic (can use LLM or deterministic algorithm)
    # For simplicity, use deterministic approach:
    
    configurations = {}
    subnet_base = "192.168"
    subnet_counter = 1
    
    for node in topology.nodes:
        if node.type == "router":
            # Assign IPs to router interfaces
            # Note: This is an internal representation of config, not updating the topology model itself directly here unless we want to.
            # But the 'configurations' dict is separate in state.
            
            node_interfaces = []
            for idx, interface in enumerate(node.interfaces):
                # Updating the interface object in place if needed, but here generating config dict
                ip = f"{subnet_base}.{subnet_counter}.{idx + 1}"
                mask = "255.255.255.0"
                
                # Also update topology model for consistency if we can (Pydantic models are mutable)
                interface.ip_address = ip
                interface.subnet_mask = mask
                
                node_interfaces.append({
                    "name": interface.name,
                    "ip": ip,
                    "mask": mask
                })
            
            configurations[node.id] = {
                "hostname": node.label or node.id,
                "interfaces": node_interfaces
            }
            subnet_counter += 1

    # VLAN segmentation: one plan per switch (access layer)
    for node in topology.nodes:
        if not _is_switch(node.type or ""):
            continue
        configurations[node.id] = {
            "hostname": node.label or node.id,
            "vlan_plan": _build_vlan_plan_for_switch(topology, node.id),
        }
    
    return {
        "configurations": configurations,
        "topology": topology, # Return updated topology with IPs
        "conversation_history": [{"role": "assistant", "content": "Configuration complete."}]
    }
