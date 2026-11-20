"""Optional Packet Tracer execute API (disabled by default)."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse

from app.integrations.packettracer.client import (
    check_token,
    invalidate_status_cache,
    is_enabled,
    projects_dir,
    status_probe,
)
from app.integrations.packettracer.models import (
    PacketTracerAttachRequest,
    PacketTracerExecuteRequest,
)
from app.integrations.packettracer.registry import (
    attach_design,
    download_name_for,
    list_runs,
)
from app.integrations.packettracer.runner import execute_packettracer

router = APIRouter()


def _require_enabled_and_token(x_pt_token: Optional[str]) -> None:
    if not is_enabled():
        raise HTTPException(status_code=404, detail="Packet Tracer integration disabled")
    if not check_token(x_pt_token):
        raise HTTPException(status_code=401, detail="Invalid or missing PACKETTRACER_TOKEN")


def _safe_execution_id(execution_id: str) -> str:
    safe = "".join(ch for ch in execution_id if ch.isalnum() or ch in ("-", "_"))
    if not safe or safe != execution_id:
        raise HTTPException(status_code=400, detail="Invalid execution_id")
    return safe


@router.get("/status")
async def packettracer_status(
    x_pt_token: Optional[str] = Header(default=None, alias="X-PT-Token"),
):
    if not is_enabled():
        return {
            "ready": False,
            "enabled": False,
            "canvas_empty": False,
            "detail": "PACKETTRACER_ENABLED is false",
        }
    if not check_token(x_pt_token):
        raise HTTPException(status_code=401, detail="Invalid or missing PACKETTRACER_TOKEN")
    # Off the event loop so list/download stay responsive while MCP is probed.
    return await asyncio.to_thread(status_probe)


@router.post("/execute")
async def packettracer_execute(
    body: PacketTracerExecuteRequest,
    x_pt_token: Optional[str] = Header(default=None, alias="X-PT-Token"),
):
    _require_enabled_and_token(x_pt_token)
    design_id = body.design_id
    design_name = body.design_name
    if isinstance(body.options, dict):
        if not design_id:
            design_id = body.options.get("design_id")
        if not design_name:
            design_name = body.options.get("design_name")
    result = await asyncio.to_thread(
        execute_packettracer,
        topology=body.topology,
        cisco_configs=body.cisco_configs,
        configurations=body.configurations,
        execution_id=body.execution_id,
        design_id=design_id,
        design_name=design_name,
    )
    invalidate_status_cache()
    return result


@router.get("/projects")
def packettracer_list_projects(
    design_id: Optional[str] = Query(default=None),
    x_pt_token: Optional[str] = Header(default=None, alias="X-PT-Token"),
):
    """List saved PT runs (filenames + ids only; no filesystem paths)."""
    _require_enabled_and_token(x_pt_token)
    return {"projects": list_runs(design_id=design_id)}


@router.post("/projects/{execution_id}/attach")
def packettracer_attach_project(
    execution_id: str,
    body: PacketTracerAttachRequest,
    x_pt_token: Optional[str] = Header(default=None, alias="X-PT-Token"),
):
    """Attach an orphan run to a design after the design is saved."""
    _require_enabled_and_token(x_pt_token)
    safe = _safe_execution_id(execution_id)
    if not (body.design_id or "").strip():
        raise HTTPException(status_code=400, detail="design_id required")
    row = attach_design(safe, body.design_id.strip())
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


@router.get("/projects/{execution_id}")
def packettracer_download(
    execution_id: str,
    x_pt_token: Optional[str] = Header(default=None, alias="X-PT-Token"),
):
    _require_enabled_and_token(x_pt_token)
    safe = _safe_execution_id(execution_id)
    base = projects_dir() / safe
    pkt = base / f"{safe}.pkt"
    if not pkt.exists() or not pkt.is_file():
        candidates = list(base.glob("*.pkt"))
        if not candidates:
            raise HTTPException(status_code=404, detail="Project not found")
        pkt = candidates[0]
    try:
        pkt.resolve().relative_to(projects_dir().resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project path")
    return FileResponse(
        path=str(pkt),
        filename=download_name_for(safe),
        media_type="application/octet-stream",
    )
