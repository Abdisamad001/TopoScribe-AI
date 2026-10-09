"""Saved export reports. Deleting a report does not delete the design."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Report, get_db

router = APIRouter()


class ReportCreate(BaseModel):
    name: str
    markdown: str
    design_id: Optional[str] = None


def _to_dict(report: Report) -> Dict[str, Any]:
    return {
        "id": str(report.id),
        "name": report.name,
        "markdown": report.markdown,
        "design_id": report.design_id,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).all()
        return [_to_dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_report(body: ReportCreate, db: Session = Depends(get_db)):
    name = body.name.strip() or "Report"
    if not body.markdown.strip():
        raise HTTPException(status_code=400, detail="Report content is empty")
    try:
        report = Report(name=name, markdown=body.markdown, design_id=body.design_id)
        db.add(report)
        db.commit()
        db.refresh(report)
        return _to_dict(report)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}")
def delete_report(report_id: str, db: Session = Depends(get_db)):
    try:
        report = db.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        db.delete(report)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
