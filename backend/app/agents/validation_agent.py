from app.graph.state import NetworkDesignState
from app.generators.cisco import generate_cisco_config
from typing import Dict, Any

def validation_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Validation Agent: Validates and generates final configs.
    """
    
    topology = state["topology"]
    configurations = state["configurations"]
    
    # Validation checks
    errors = []
    
    # Check 1: All links have valid endpoints
    node_ids = {node.id for node in topology.nodes}
    for link in topology.links:
        if link.source not in node_ids:
            errors.append(f"Link {link.id}: source {link.source} not found")
        if link.target not in node_ids:
            errors.append(f"Link {link.id}: target {link.target} not found")
    
    # Check 2: No IP conflicts (simplified)
    used_ips = set()
    for node_id, config in configurations.items():
        for iface in config.get("interfaces", []):
            ip = iface.get("ip")
            if ip in used_ips:
                errors.append(f"IP conflict: {ip} used multiple times")
            used_ips.add(ip)

    # Check 3: VLAN plan consistency (segmentation pipeline)
    for node_id, config in configurations.items():
        vp = config.get("vlan_plan")
        if not vp:
            continue
        vlans = vp.get("vlans") or []
        vlan_ids = []
        for v in vlans:
            vid = v.get("id")
            if vid is None:
                errors.append(f"VLAN plan {node_id}: missing vlan id in vlans list")
                continue
            if not isinstance(vid, int) or vid < 2 or vid > 4094:
                errors.append(f"VLAN plan {node_id}: invalid vlan id {vid} (must be 2-4094)")
            vlan_ids.append(vid)
        if len(vlan_ids) != len(set(vlan_ids)):
            errors.append(f"VLAN plan {node_id}: duplicate VLAN ids in vlans list")
        defined = set(vlan_ids)
        for a in vp.get("access_assignments") or []:
            av = a.get("vlan_id")
            if av is None:
                errors.append(f"VLAN plan {node_id}: access assignment missing vlan_id")
                continue
            if av not in defined:
                errors.append(
                    f"VLAN plan {node_id}: access vlan {av} not declared in vlans list"
                )
            nh = a.get("neighbor_node_id")
            if nh and nh not in node_ids:
                errors.append(
                    f"VLAN plan {node_id}: assignment references unknown neighbor {nh}"
                )
    
    if errors:
        return {
            "errors": errors,
            "validation_result": {"status": "failed", "errors": errors}
        }
    
    # Generate Cisco configs
    cisco_configs = {}
    for node in topology.nodes:
        if node.type == "router":
            cisco_configs[node.id] = generate_cisco_config(node, configurations.get(node.id, {}))
        else:
            nt = (node.type or "").lower()
            # Keep in sync with config_agent / cisco switch detection (catalyst, hub, etc.)
            if nt == "switch" or "switch" in nt or "catalyst" in nt or "hub" in nt:
                cfg = configurations.get(node.id, {})
                if cfg.get("vlan_plan"):
                    cisco_configs[node.id] = generate_cisco_config(node, cfg)
    
    return {
        "cisco_configs": cisco_configs,
        "validation_result": {"status": "passed"},
        "conversation_history": [{"role": "assistant", "content": "Validation passed. Configs ready."}]
    }
