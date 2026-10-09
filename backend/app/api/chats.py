"""Saved assistant chats. Deleting a chat does not delete the design."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Chat, get_db

router = APIRouter()


class ChatCreate(BaseModel):
    title: str
    messages: List[Dict[str, Any]]
    design_id: Optional[str] = None
    design_name: Optional[str] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    design_id: Optional[str] = None
    design_name: Optional[str] = None


def _to_dict(chat: Chat) -> Dict[str, Any]:
    messages = chat.messages if isinstance(chat.messages, list) else []
    return {
        "id": str(chat.id),
        "title": chat.title,
        "messages": messages,
        "design_id": chat.design_id,
        "design_name": chat.design_name,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
    }


def _get_or_404(db: Session, chat_id: str) -> Chat:
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.get("")
def list_chats(db: Session = Depends(get_db)):
    try:
        rows = db.query(Chat).order_by(Chat.updated_at.desc()).all()
        return [_to_dict(c) for c in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_chat(body: ChatCreate, db: Session = Depends(get_db)):
    title = body.title.strip() or "Chat"
    try:
        chat = Chat(
            title=title,
            messages=body.messages or [],
            design_id=body.design_id,
            design_name=body.design_name,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return _to_dict(chat)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{chat_id}")
def update_chat(chat_id: str, body: ChatUpdate, db: Session = Depends(get_db)):
    try:
        chat = _get_or_404(db, chat_id)
        if body.title is not None:
            chat.title = body.title.strip() or chat.title
        if body.messages is not None:
            chat.messages = body.messages
        if body.design_id is not None:
            chat.design_id = body.design_id
        if body.design_name is not None:
            chat.design_name = body.design_name
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(chat)
        return _to_dict(chat)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    try:
        chat = _get_or_404(db, chat_id)
        db.delete(chat)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
