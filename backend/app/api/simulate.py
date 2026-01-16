from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.network import Topology
from app.simulation.graph_builder import build_network_graph
from app.simulation.reachability import simulate_ping

router = APIRouter()

class SimulationRequest(BaseModel):
    topology: Topology
    source: str
    target: str

@router.post("/run")
async def run_simulation(request: SimulationRequest):
    """
    Simulates connectivity between two nodes.
    """
    try:
        # Build NetworkX graph
        graph = build_network_graph(request.topology)
        
        # Run reachability check
        result = simulate_ping(graph, request.source, request.target)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
