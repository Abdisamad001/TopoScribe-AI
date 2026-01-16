from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Interface(BaseModel):
    name: str
    ip_address: Optional[str] = Field(None, alias="ip")
    subnet_mask: Optional[str] = Field(None, alias="mask")

    class Config:
        populate_by_name = True

class NetworkNode(BaseModel):
    id: str
    type: str
    label: Optional[str] = None
    interfaces: List[Interface] = []
    config: Dict[str, Any] = {}
    x: int = 0
    y: int = 0

class Link(BaseModel):
    id: str
    source: str
    target: str
    bandwidth: Optional[int] = 1000

class Protocol(BaseModel):
    name: str
    parameters: Dict[str, Any] = {}

class Topology(BaseModel):
    nodes: List[NetworkNode]
    links: List[Link]
    protocols: List[Protocol] = []
    metadata: Dict[str, Any] = {}
