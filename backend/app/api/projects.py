"""Projects."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Project, get_db

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    design_ids: Optional[List[str]] = None


def _to_dict(project: Project) -> Dict[str, Any]:
    ids = project.design_ids if isinstance(project.design_ids, list) else []
    return {
        "id": str(project.id),
        "name": project.name,
        "design_ids": [str(i) for i in ids],
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def _get_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    try:
        rows = db.query(Project).order_by(Project.created_at.desc()).all()
        return [_to_dict(p) for p in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    try:
        project = Project(name=name, design_ids=[])
        db.add(project)
        db.commit()
        db.refresh(project)
        return _to_dict(project)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}")
def update_project(project_id: str, body: ProjectUpdate, db: Session = Depends(get_db)):
    try:
        project = _get_or_404(db, project_id)
        if body.name is not None:
            name = body.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="Name is required")
            project.name = name
        if body.design_ids is not None:
            # Keep order, drop duplicates.
            seen = set()
            clean = []
            for design_id in body.design_ids:
                key = str(design_id)
                if key in seen:
                    continue
                seen.add(key)
                clean.append(key)
            project.design_ids = clean
        db.commit()
        db.refresh(project)
        return _to_dict(project)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    try:
        project = _get_or_404(db, project_id)
        db.delete(project)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
