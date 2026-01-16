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
    
    return {
        "cisco_configs": cisco_configs,
        "validation_result": {"status": "passed"},
        "conversation_history": [{"role": "assistant", "content": "Validation passed. Configs ready."}]
    }
