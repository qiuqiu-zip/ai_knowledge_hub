from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.knowledge import KnowledgeRead

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeRead])
def list_knowledge(db: Session = Depends(get_db)):
    return list(db.scalars(select(models.KnowledgeItem).order_by(models.KnowledgeItem.created_at.desc())).all())


@router.get("/{knowledge_id}", response_model=KnowledgeRead)
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    item = db.get(models.KnowledgeItem, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return item
