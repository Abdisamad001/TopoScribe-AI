"""Orchestrate a Packet Tracer execute request."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.integrations.packettracer.client import (
    claim_execution_id,
    new_execution_id,
    release_execution_id,
    run_worker,
)
from app.integrations.packettracer.mapper import get_cabling_rows
from app.integrations.packettracer.registry import (
    friendly_pkt_name,
    public_result,
    record_run,
)


def execute_packettracer(
    *,
    topology: Dict[str, Any],
    cisco_configs: Dict[str, str],
    configurations: Optional[Dict[str, Any]] = None,
    execution_id: Optional[str] = None,
    design_id: Optional[str] = None,
    design_name: Optional[str] = None,
) -> Dict[str, Any]:
    eid = (execution_id or "").strip() or new_execution_id()
    display_name = friendly_pkt_name(design_name, eid)
    err = claim_execution_id(eid)
    if err:
        return public_result(
            {
                "execution_id": eid,
                "ok": False,
                "stage": "duplicate",
                "message": err,
                "devices": [],
                "links": [],
                "cli_lines": [],
                "pings": [],
                "name_map": {},
                "raw_notes": [],
            },
            design_name=design_name,
        )

    try:
        if not get_cabling_rows(topology):
            release_execution_id(eid, success=False)
            return public_result(
                {
                    "execution_id": eid,
                    "ok": False,
                    "stage": "precheck",
                    "message": "Missing topology.metadata.cabling — run configure first",
                    "devices": [],
                    "links": [],
                    "cli_lines": [],
                    "pings": [],
                    "name_map": {},
                    "raw_notes": [],
                },
                design_name=design_name,
            )
        if not cisco_configs:
            release_execution_id(eid, success=False)
            return public_result(
                {
                    "execution_id": eid,
                    "ok": False,
                    "stage": "precheck",
                    "message": "cisco_configs is empty",
                    "devices": [],
                    "links": [],
                    "cli_lines": [],
                    "pings": [],
                    "name_map": {},
                    "raw_notes": [],
                },
                design_name=design_name,
            )

        result = run_worker(
            {
                "execution_id": eid,
                "topology": topology,
                "cisco_configs": cisco_configs,
                "configurations": configurations or {},
            }
        )
        release_execution_id(eid, success=bool(result.get("ok")))
        try:
            record_run(
                execution_id=eid,
                design_id=design_id,
                design_name=design_name,
                ok=bool(result.get("ok")),
                stage=str(result.get("stage") or ""),
                message=str(result.get("message") or ""),
                filename=f"{eid}.pkt",
                download_filename=display_name,
            )
        except Exception as reg_err:
            result.setdefault("raw_notes", []).append(f"registry:{reg_err}")
        return public_result(result, design_name=design_name)
    except Exception as e:
        release_execution_id(eid, success=False)
        try:
            record_run(
                execution_id=eid,
                design_id=design_id,
                design_name=design_name,
                ok=False,
                stage="exception",
                message=str(e),
                filename=f"{eid}.pkt",
                download_filename=display_name,
            )
        except Exception:
            pass
        return public_result(
            {
                "execution_id": eid,
                "ok": False,
                "stage": "exception",
                "message": str(e),
                "devices": [],
                "links": [],
                "cli_lines": [],
                "pings": [],
                "name_map": {},
                "raw_notes": [],
            },
            design_name=design_name,
        )
