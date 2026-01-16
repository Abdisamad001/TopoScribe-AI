from app.graph.state import NetworkDesignState
from typing import Dict, Any

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
    
    return {
        "configurations": configurations,
        "topology": topology, # Return updated topology with IPs
        "conversation_history": [{"role": "assistant", "content": "Configuration complete."}]
    }
