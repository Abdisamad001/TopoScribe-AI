from app.graph.state import NetworkDesignState
from app.models.network import Topology
from app.utils.llm import get_llm_response
from typing import Dict, Any, List, Optional, Tuple
import json

def _norm_vlan_item(item: Any) -> Optional[Tuple[int, str]]:
    if not isinstance(item, dict):
        return None
    vid = item.get("id")
    if vid is None:
        vid = item.get("vlan_id")
    if vid is None:
        return None
    try:
        v = int(vid)
    except (TypeError, ValueError):
        return None
    if v < 2 or v > 4094:
        return None
    name = item.get("name") or item.get("vlan_name") or f"VLAN_{v}"
    return (v, str(name).strip()[:64])

def merge_vlan_metadata(design_plan: Dict[str, Any], topology_dict: Dict[str, Any]) -> None:
    """
    Ensure topology.metadata.vlans exists from design_plan when the LLM omitted it.
    """
    md = topology_dict.setdefault("metadata", {})
    raw = md.get("vlans")
    if isinstance(raw, list) and len(raw) > 0:
        return
    if not isinstance(design_plan, dict):
        return
    out: List[Dict[str, Any]] = []
    seen = set()

    def add(vid: int, name: str) -> None:
        if vid in seen:
            return
        seen.add(vid)
        out.append({"id": vid, "name": name})

    dpv = design_plan.get("vlans")
    if isinstance(dpv, list):
        for item in dpv:
            n = _norm_vlan_item(item)
            if n:
                add(n[0], n[1])
    depts = design_plan.get("departments")
    if isinstance(depts, list):
        for i, d in enumerate(depts):
            if not isinstance(d, dict):
                continue
            name = d.get("name") or d.get("department") or f"DEPT{i + 1}"
            vid = d.get("vlan_id")
            if vid is None:
                vid = 100 + i * 10
            try:
                vi = int(vid)
            except (TypeError, ValueError):
                continue
            if 2 <= vi <= 4094:
                add(vi, str(name))
    if out:
        md["vlans"] = out

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
- VLANs MUST match the design plan: use the same VLAN IDs and department names as in design_plan.vlans or design_plan.departments (if present). If the plan lists N departments, create N access VLANs with those ids/names and assign each department's hosts and access switch accordingly.
- On each host node, set "config": {{"vlan_id": <number>, "vlan_name": "<same as catalog>"}} matching that host's department VLAN.
- Put the full VLAN catalog in metadata.vlans as [{{"id": <int 2-4094>, "name": "<string>"}}, ...] covering every department VLAN in the design.
- Use distinct private IPv4 subnets per VLAN (e.g. 192.168.<vlan_id>.0/24 or another consistent scheme) on hosts; routers use subinterfaces toward switches (do not rely on a fixed 10/20/30 scheme unless the user asked for it).
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
  "metadata": {{
    "vlans": [
      {{"id": 100, "name": "ExampleDept"}}
    ]
  }}
}}

Output ONLY valid JSON, no markdown.
"""
    
    response_text = get_llm_response(prompt, model="llama-3.3-70b-versatile")
    
    # Parse and validate
    try:
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        topology_dict = json.loads(clean_text)

        merge_vlan_metadata(design_plan or {}, topology_dict)
        
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
