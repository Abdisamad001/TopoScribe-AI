from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.graph.workflow import app as workflow_app
from app.graph.state import NetworkDesignState
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time
import csv
from pathlib import Path

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Part 2 run log. scenario_runs.csv (Part 1) is frozen as the pre-escalation
# baseline and no longer receives rows; run numbering restarts at 1 here because
# this is a separate dataset, not a continuation. See scenario_runs_NOTES.md.
RUN_LOG_PATH = DATA_DIR / "scenario_runs_part2.csv"
RUN_LOG_HEADERS = [
    "Run #",
    "Requirements Clear?",
    "Questions Asked?",
    "Design Generated?",
    "Retries",
    "Runtime (Seconds)",
    "Result",
    "Topology Source",
    "Topology Retries",
    "Escalated",
]

# Keys copied out of the graph's agent_trace, so the response shape stays stable
# if a node starts recording extra internal fields.
_TRACE_KEYS = ("agent", "model", "attempt", "outcome", "status")


def _compact_trace(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Per-attempt generation provenance, for research evaluation."""
    return [
        {k: entry.get(k) for k in _TRACE_KEYS}
        for entry in (result.get("agent_trace") or [])
        if isinstance(entry, dict)
    ]


def _ensure_run_log_file() -> None:
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RUN_LOG_PATH.exists():
        return
    with RUN_LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(RUN_LOG_HEADERS)


def _next_run_number() -> int:
    _ensure_run_log_file()
    with RUN_LOG_PATH.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    # Header only => run 1
    return max(1, len(rows))


def _append_run_row(
    requirements_clear: bool,
    questions_asked: int,
    design_generated: bool,
    retries: int,
    runtime_seconds: float,
    result: str,
    topology_source: Optional[str] = None,
    topology_retries: int = 0,
) -> None:
    _ensure_run_log_file()
    # Runs that never reached topology generation have no source, and must not
    # be counted as escalated just because the source is not "groq".
    escalated = "Yes" if topology_source and topology_source != "groq" else "No"
    row = [
        _next_run_number(),
        "Yes" if requirements_clear else "No",
        questions_asked,
        "Yes" if design_generated else "No",
        retries,
        runtime_seconds,
        result,
        topology_source or "",
        topology_retries,
        escalated,
    ]
    with RUN_LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

class DesignRequest(BaseModel):
    description: str
    conversation_history: List[dict] = []

@router.post("/generate")
async def generate_design(request: DesignRequest):
    """
    Initiates the LangGraph workflow.
    """
    try:
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()

        initial_state: NetworkDesignState = {
            "user_input": request.description,
            "conversation_history": request.conversation_history,
            "requirements_clear": False,
            "clarifying_questions": None,
            "design_plan": None,
            "topology": None,
            "topology_retry_count": 0,
            "topology_source": None,
            "topology_quality_ok": True,
            "configurations": None,
            "validation_result": None,
            "cisco_configs": None,
            "report": None,
            "errors": [],
            "retry_count": 0,
            "agent_trace": [],
        }
        
        # Invoke LangGraph workflow
        result = await workflow_app.ainvoke(initial_state)
        runtime_ms = round((time.perf_counter() - t0) * 1000, 2)
        runtime_seconds = round(runtime_ms / 1000, 3)
        
        # Check if planning needs more info
        if not result.get("requirements_clear"):
            questions = result.get("clarifying_questions", []) or []
            retries = int(result.get("retry_count", 0) or 0)
            _append_run_row(
                requirements_clear=False,
                questions_asked=len(questions),
                design_generated=False,
                retries=retries,
                runtime_seconds=runtime_seconds,
                result="Needs Clarification",
            )
            return {
                "status": "needs_clarification",
                "questions": questions,
                "conversation_history": result.get("conversation_history", []),
                "runtime": {
                    "started_at_utc": started_at,
                    "elapsed_ms": runtime_ms,
                    "elapsed_seconds": runtime_seconds,
                },
            }
        
        # Planning complete — require a topology payload for the frontend
        if not result.get("topology"):
            errs = result.get("errors") or []
            detail = errs[0] if errs else "Topology could not be produced."
            topology_retries = int(result.get("topology_retry_count", 0) or 0)
            _append_run_row(
                requirements_clear=True,
                questions_asked=0,
                design_generated=False,
                retries=int(result.get("retry_count", 0) or 0),
                runtime_seconds=runtime_seconds,
                result=f"Incomplete: {detail}",
                topology_source=result.get("topology_source"),
                topology_retries=topology_retries,
            )
            return {
                "status": "generation_failed",
                "message": detail,
                "errors": errs,
                "conversation_history": result.get("conversation_history", []),
                "retry_count": int(result.get("retry_count", 0) or 0),
                "topology_source": result.get("topology_source"),
                "topology_retry_count": topology_retries,
                "agent_trace": _compact_trace(result),
                "runtime": {
                    "started_at_utc": started_at,
                    "elapsed_ms": runtime_ms,
                    "elapsed_seconds": runtime_seconds,
                },
            }

        # Planning complete, return results
        retries = int(result.get("retry_count", 0) or 0)
        design_generated = bool(result.get("topology"))
        topology_retries = int(result.get("topology_retry_count", 0) or 0)
        _append_run_row(
            requirements_clear=True,
            questions_asked=0,
            design_generated=design_generated,
            retries=retries,
            runtime_seconds=runtime_seconds,
            result="Success" if design_generated else "Incomplete",
            topology_source=result.get("topology_source"),
            topology_retries=topology_retries,
        )
        return {
            "status": "complete",
            "topology": result.get("topology").dict() if result.get("topology") else None,
            "configurations": result.get("configurations"),
            "cisco_configs": result.get("cisco_configs"),
            "validation_result": result.get("validation_result"),
            "retry_count": retries,
            "topology_source": result.get("topology_source"),
            "topology_retry_count": topology_retries,
            "agent_trace": _compact_trace(result),
            "runtime": {
                "started_at_utc": started_at,
                "elapsed_ms": runtime_ms,
                "elapsed_seconds": runtime_seconds,
            },
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            runtime_seconds = round((time.perf_counter() - t0), 3) if "t0" in locals() else 0.0
            _append_run_row(
                requirements_clear=False,
                questions_asked=0,
                design_generated=False,
                retries=0,
                runtime_seconds=runtime_seconds,
                result=f"Error: {str(e)}",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
