from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.graph.workflow import app as workflow_app
from app.graph.state import NetworkDesignState
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time

router = APIRouter()

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
            "errors": []
        }
        
        # Invoke LangGraph workflow
        result = await workflow_app.ainvoke(initial_state)
        runtime_ms = round((time.perf_counter() - t0) * 1000, 2)
        runtime_seconds = round(runtime_ms / 1000, 3)
        
        # Check if planning needs more info
        if not result.get("requirements_clear"):
            return {
                "status": "needs_clarification",
                "questions": result.get("clarifying_questions", []),
                "conversation_history": result.get("conversation_history", []),
                "runtime": {
                    "started_at_utc": started_at,
                    "elapsed_ms": runtime_ms,
                    "elapsed_seconds": runtime_seconds,
                },
            }
        
        # Planning complete, return results
        return {
            "status": "complete",
            "topology": result.get("topology").dict() if result.get("topology") else None,
            "configurations": result.get("configurations"),
            "cisco_configs": result.get("cisco_configs"),
            "validation_result": result.get("validation_result"),
            "runtime": {
                "started_at_utc": started_at,
                "elapsed_ms": runtime_ms,
                "elapsed_seconds": runtime_seconds,
            },
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
