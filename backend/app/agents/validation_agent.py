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
    
    # Check 2: No IP conflicts (interfaces + router subinterfaces)
    used_ips = set()
    for node_id, config in configurations.items():
        for iface in config.get("interfaces", []):
            ip = iface.get("ip")
            if ip:
                if ip in used_ips:
                    errors.append(f"IP conflict: {ip} used multiple times")
                used_ips.add(ip)
        for s in config.get("subinterfaces") or []:
            ip = s.get("ip")
            if ip:
                if ip in used_ips:
                    errors.append(f"IP conflict: {ip} used multiple times (subinterface)")
                used_ips.add(ip)

    # Check 3: VLAN plan (switches): dynamic VLAN ids and port modes
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

        for p in vp.get("ports") or []:
            mode = p.get("mode")
            if mode == "access":
                av = p.get("vlan_id")
                if av is None:
                    errors.append(f"VLAN plan {node_id}: access port missing vlan_id")
                    continue
                if av not in defined:
                    errors.append(
                        f"VLAN plan {node_id}: access vlan {av} not declared in vlans list"
                    )
            elif mode == "trunk":
                csv = (p.get("allowed_vlans_csv") or "").strip()
                if not csv:
                    errors.append(f"VLAN plan {node_id}: trunk port missing allowed VLANs")
                    continue
                for part in csv.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        tv = int(part)
                    except ValueError:
                        errors.append(
                            f"VLAN plan {node_id}: invalid trunk vlan token {part!r}"
                        )
                        continue
                    if tv != 1 and tv not in defined:
                        errors.append(
                            f"VLAN plan {node_id}: trunk references vlan {tv} not in local VLAN database"
                        )
            else:
                errors.append(f"VLAN plan {node_id}: unknown port mode {mode!r}")
    
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
            if nt == "switch" or "switch" in nt or "catalyst" in nt or "hub" in nt:
                cfg = configurations.get(node.id, {})
                if cfg.get("vlan_plan"):
                    cisco_configs[node.id] = generate_cisco_config(node, cfg)
    
    return {
        "cisco_configs": cisco_configs,
        "validation_result": {"status": "passed"},
        "conversation_history": [{"role": "assistant", "content": "Validation passed. Configs ready."}]
    }
