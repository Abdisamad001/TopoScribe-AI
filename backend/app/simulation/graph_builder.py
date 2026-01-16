import networkx as nx
from app.models.network import Topology

def build_network_graph(topology: Topology) -> nx.Graph:
    """
    Converts Topology model to NetworkX graph.
    """
    G = nx.Graph()
    
    # Add nodes
    for node in topology.nodes:
        G.add_node(node.id, **node.dict())
    
    # Add edges
    for link in topology.links:
        G.add_edge(
            link.source,
            link.target,
            weight=1.0 / (link.bandwidth or 1000)  # Lower bandwidth = higher weight
        )
    
    return G
