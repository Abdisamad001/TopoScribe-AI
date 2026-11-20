"""Request/response shapes for Packet Tracer execute."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PacketTracerExecuteRequest(BaseModel):
    topology: Dict[str, Any]
    cisco_configs: Dict[str, str] = Field(default_factory=dict)
    configurations: Dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[str] = None
    design_id: Optional[str] = None
    design_name: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class PacketTracerAttachRequest(BaseModel):
    design_id: str


class CliLineResult(BaseModel):
    device_id: str
    line: str
    status: str  # ok | rejected | error | skipped
    impact: str = ""  # benign | harmful | unknown | ""
    detail: str = ""


class DeviceCreateResult(BaseModel):
    node_id: str
    label: str = ""
    pt_name: str
    pt_model: str
    ok: bool
    detail: str = ""


class LinkCreateResult(BaseModel):
    link_id: str = ""
    a_id: str
    a_port: str
    b_id: str
    b_port: str
    cable_type: str
    ok: bool
    detail: str = ""


class PingResult(BaseModel):
    source: str
    destination: str
    attempts: int
    final_status: str  # pass | fail
    messages: List[str] = Field(default_factory=list)


class PacketTracerExecuteResult(BaseModel):
    execution_id: str
    ok: bool
    stage: str = ""
    message: str = ""
    devices: List[DeviceCreateResult] = Field(default_factory=list)
    links: List[LinkCreateResult] = Field(default_factory=list)
    cli_lines: List[CliLineResult] = Field(default_factory=list)
    pings: List[PingResult] = Field(default_factory=list)
    project_file: Optional[str] = None
    project_download_id: Optional[str] = None
    name_map: Dict[str, str] = Field(default_factory=dict)
    raw_notes: List[str] = Field(default_factory=list)
