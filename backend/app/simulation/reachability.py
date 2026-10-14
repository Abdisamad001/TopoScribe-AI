import networkx as nx
from typing import Dict, Any

def simulate_ping(graph: nx.Graph, source: str, target: str) -> Dict[str, Any]:
    try:
        path = nx.shortest_path(graph, source=source, target=target)
        return {
            "success": True,
            "path": path,
            "hops": len(path) - 1
        }
    except nx.NetworkXNoPath:
        return {
            "success": False,
            "message": f"No path from {source} to {target}"
        }
    except nx.NodeNotFound as e:
        return {
            "success": False,
            "message": f"Node not found: {str(e)}"
        }
