from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.design import generate_design, DesignRequest

router = APIRouter()

@router.post("/clarify")
async def clarify_requirements(request: DesignRequest):
    """
    Continues the LangGraph workflow after user provides answers.
    Reuse generate_design logic as the state will just continue from new input.
    """
    return await generate_design(request)
