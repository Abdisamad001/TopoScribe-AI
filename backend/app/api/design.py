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

RUN_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "scenario_runs.csv"
RUN_LOG_HEADERS = [
    "Run #",
    "Requirements Clear?",
    "Questions Asked?",
    "Design Generated?",
    "Retries",
    "Runtime (Seconds)",
    "Result",
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
) -> None:
    _ensure_run_log_file()
    row = [
        _next_run_number(),
        "Yes" if requirements_clear else "No",
        questions_asked,
        "Yes" if design_generated else "No",
        retries,
        runtime_seconds,
        result,
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
            "configurations": None,
            "validation_result": None,
            "cisco_configs": None,
            "report": None,
            "errors": [],
            "retry_count": 0,
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
        
        # Planning complete, return results
        retries = int(result.get("retry_count", 0) or 0)
        design_generated = bool(result.get("topology"))
        _append_run_row(
            requirements_clear=True,
            questions_asked=0,
            design_generated=design_generated,
            retries=retries,
            runtime_seconds=runtime_seconds,
            result="Success" if design_generated else "Incomplete",
        )
        return {
            "status": "complete",
            "topology": result.get("topology").dict() if result.get("topology") else None,
            "configurations": result.get("configurations"),
            "cisco_configs": result.get("cisco_configs"),
            "validation_result": result.get("validation_result"),
            "retry_count": retries,
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
