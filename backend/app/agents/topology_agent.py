from app.graph.state import NetworkDesignState
from app.models.network import Topology
from app.utils.llm import get_llm_response
from typing import Dict, Any
import json

def topology_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Topology Agent: Converts design plan into network topology.
    """
    
    design_plan = state.get("design_plan", {})
    
    prompt = f"""You are a network topology generation agent.

Design plan:
{json.dumps(design_plan, indent=2)}

Generate a network topology with:
- Routers, switches, hosts as needed
- If the design plan describes a SINGLE site / single campus, use exactly ONE router (one logical L3 device). Do not add separate "Edge Router" and "Core Router" pairs for a single-site design.
- For multi-department VLAN campus designs (e.g. HR, IT, Finance), place hosts on subnets 192.168.10.0/24, 192.168.20.0/24, and 192.168.30.0/24 respectively (third octet 10, 20, 30) and connect each department's hosts to that department's access switch.
- Proper connections between devices
- Hierarchical spatial layout:
    - Routers at the top (y=0 to y=100)
    - Core Switches below (y=200)
    - Access Switches further below (y=400)
    - Hosts/Servers at the bottom (y=600+)
    - Spread devices horizontally (x-axis) with at least 250px gap between them to avoid overlap.
    - Do NOT place nodes at the exact same coordinates.
    - IMPORTANT: You MUST assign valid private IP addresses (e.g. 192.168.x.x) to all Routers and Hosts.

Output a JSON object matching this schema:
{{
  "nodes": [
    {{
      "id": "R1",
      "type": "router",
      "label": "Edge Router",
      "interfaces": [
          {{ "name": "eth0", "ip": "192.168.1.1", "mask": "255.255.255.0" }}
      ],
      "config": {{}},
      "x": 100,
      "y": 100
    }},
    ...
  ],
  "links": [
    {{
      "id": "link1",
      "source": "R1",
      "target": "SW1",
      "bandwidth": 1000
    }},
    ...
  ],
  "protocols": [
    {{
      "name": "ospf",
      "parameters": {{"area": 0}}
    }}
  ],
  "metadata": {{}}
}}

Output ONLY valid JSON, no markdown.
"""
    
    response_text = get_llm_response(prompt, model="llama-3.3-70b-versatile")
    
    # Parse and validate
    try:
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        topology_dict = json.loads(clean_text)
        
        # Apply deterministic layout
        nodes = topology_dict.get("nodes", [])
        
        # Group by type (case-insensitive)
        routers = []
        switches = []
        hosts = []
        others = []

        for n in nodes:
            t = n.get("type", "").lower()
            if "router" in t or "gateway" in t or "firewall" in t:
                routers.append(n)
            elif "switch" in t or "hub" in t:
                switches.append(n)
            elif "host" in t or "pc" in t or "server" in t or "laptop" in t:
                hosts.append(n)
            else:
                others.append(n)
        
        # Layout parameters
        start_x = 100
        spacing_x = 300
        level_height = 200
        
        # Function to position a row
        def position_row(items, y_level):
            total_width = (len(items) - 1) * spacing_x
            current_x = start_x + (1000 - total_width) / 2 # Center align roughly
            if current_x < 100: current_x = 100
            
            for i, node in enumerate(items):
                node["x"] = int(current_x + (i * spacing_x))
                node["y"] = y_level
                # Remove nested position if LLM put it there
                if "position" in node:
                    del node["position"]

        # Apply positions
        position_row(routers, 0)
        position_row(switches, 200)
        position_row(others, 400) # Firewalls etc
        position_row(hosts, 500)
        
        topology = Topology(**topology_dict)  # Pydantic validation
        
        return {
            "topology": topology,
            "conversation_history": [{"role": "assistant", "content": "Topology generated successfully."}]
        }
    except Exception as e:
        return {
            "errors": [f"Topology generation failed: {str(e)}"],
            "conversation_history": [{"role": "assistant", "content": f"Error: {str(e)}"}]
        }
