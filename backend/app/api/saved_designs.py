from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.db import Design, get_db

router = APIRouter()


class DesignCreate(BaseModel):
    name: str
    topology: Dict[str, Any]


class DesignUpdate(BaseModel):
    name: Optional[str] = None
    topology: Optional[Dict[str, Any]] = None


def _to_dict(design: Design) -> Dict[str, Any]:
    return {
        "id": str(design.id),
        "name": design.name,
        "topology": design.topology,
        "is_favourite": design.is_favourite,
        "is_template": bool(getattr(design, "is_template", False)),
        "created_at": design.created_at.isoformat() if design.created_at else None,
        "last_opened_at": design.last_opened_at.isoformat() if design.last_opened_at else None,
    }


def _get_or_404(db: Session, design_id: str) -> Design:
    design = db.get(Design, design_id)
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return design


@router.get("")
def list_designs(db: Session = Depends(get_db)):
    try:
        designs = db.query(Design).order_by(Design.created_at.desc()).all()
        return [_to_dict(d) for d in designs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_design(request: DesignCreate, db: Session = Depends(get_db)):
    try:
        design = Design(name=request.name, topology=request.topology)
        db.add(design)
        db.commit()
        db.refresh(design)
        return _to_dict(design)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{design_id}/open")
def open_design(design_id: str, db: Session = Depends(get_db)):
    try:
        design = _get_or_404(db, design_id)
        design.last_opened_at = func.now()
        db.commit()
        db.refresh(design)
        return _to_dict(design)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{design_id}/favourite")
def toggle_favourite(design_id: str, db: Session = Depends(get_db)):
    try:
        design = _get_or_404(db, design_id)
        design.is_favourite = not design.is_favourite
        db.commit()
        db.refresh(design)
        return _to_dict(design)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{design_id}/template")
def toggle_template(design_id: str, db: Session = Depends(get_db)):
    try:
        design = _get_or_404(db, design_id)
        design.is_template = not design.is_template
        db.commit()
        db.refresh(design)
        return _to_dict(design)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{design_id}")
def update_design(design_id: str, request: DesignUpdate, db: Session = Depends(get_db)):
    try:
        design = _get_or_404(db, design_id)
        if request.name is not None:
            design.name = request.name
        if request.topology is not None:
            design.topology = request.topology
        db.commit()
        db.refresh(design)
        return _to_dict(design)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{design_id}", status_code=204)
def delete_design(design_id: str, db: Session = Depends(get_db)):
    try:
        design = _get_or_404(db, design_id)
        db.delete(design)
        db.commit()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
