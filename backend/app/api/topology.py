"""Configure a canvas topology."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.config_agent import config_node
from app.generators.cisco import generate_cisco_config
from app.models.network import Topology

router = APIRouter()


class ConfigureRequest(BaseModel):
    topology: Dict[str, Any]
    design_plan: Optional[Dict[str, Any]] = None

 #
def _coerce_topology(raw: Dict[str, Any]) -> Topology:
   
    nodes = []
    for n in raw.get("nodes") or []:
        if not isinstance(n, dict) or not n.get("id") or not n.get("type"):
            continue
        nodes.append(
            {
                "id": n["id"],
                "type": n["type"],
                "label": n.get("label") or n.get("name"),
                "interfaces": n.get("interfaces") or [],
                "config": n.get("config") or {},
                "x": int(n.get("x") or 0),
                "y": int(n.get("y") or 0),
            }
        )
    links = []
    for i, link in enumerate(raw.get("links") or []):
        if not isinstance(link, dict):
            continue
        source = link.get("source") or link.get("sourceNodeId")
        target = link.get("target") or link.get("targetNodeId")
        if not source or not target:
            continue
        links.append(
            {
                "id": link.get("id") or f"L-{i}",
                "source": source,
                "target": target,
            }
        )
    return Topology(
        nodes=nodes,
        links=links,
        metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
    )


def _cisco_configs_for(topology: Topology, configurations: Dict[str, Any]) -> Dict[str, str]:
    
    out: Dict[str, str] = {}
    for node in topology.nodes:
        if node.type == "router":
            out[node.id] = generate_cisco_config(node, configurations.get(node.id, {}))
            continue
        nt = (node.type or "").lower()
        if nt == "switch" or "switch" in nt or "catalyst" in nt or "hub" in nt:
            cfg = configurations.get(node.id, {})
            if cfg.get("vlan_plan"):
                out[node.id] = generate_cisco_config(node, cfg)
    return out


@router.post("/configure")
def configure_topology(body: ConfigureRequest):
    try:
        topology = _coerce_topology(body.topology or {})
        if not topology.nodes:
            raise HTTPException(status_code=400, detail="Topology has no nodes")
        state = {
            "topology": topology,
            "design_plan": body.design_plan if isinstance(body.design_plan, dict) else {},
        }
        result = config_node(state)
        topo = result.get("topology") or topology
        configurations = result.get("configurations") or {}
        if not isinstance(topo.metadata, dict):
            topo.metadata = {}
        topo.metadata["configurations"] = configurations
        topo.metadata["cisco_configs"] = _cisco_configs_for(topo, configurations)
      
        return {"topology": topo.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
