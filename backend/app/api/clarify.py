from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.design import generate_design, DesignRequest

router = APIRouter()

@router.post("/clarify")
async def clarify_requirements(request: DesignRequest):
    return await generate_design(request)
