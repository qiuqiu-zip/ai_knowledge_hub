from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.knowledge import KnowledgeRead

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("")
def list_knowledge(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            models.KnowledgeItem,
            models.SourceDocument.repo,
            models.SourceDocument.file_path,
            models.SourceDocument.source_url,
            models.SourceDocument.title.label("document_title"),
        )
        .join(
            models.SourceDocument,
            models.KnowledgeItem.source_document_id == models.SourceDocument.id,
            isouter=True,
        )
    )
    total = db.scalar(select(func.count()).select_from(models.KnowledgeItem)) or 0
    offset = (page - 1) * page_size
    rows = db.execute(
        stmt.order_by(models.KnowledgeItem.created_at.desc()).offset(offset).limit(page_size)
    ).all()
    items = []
    for row in rows:
        item = row[0]
        items.append(
            {
                "id": item.id,
                "source_document_id": item.source_document_id,
                "title": item.title,
                "summary": item.summary,
                "key_points": item.key_points,
                "tags": item.tags,
                "category": item.category,
                "quality_score": item.quality_score,
                "visibility": item.visibility,
                "repo": row[1],
                "file_path": row[2],
                "source_url": row[3],
                "document_title": row[4],
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        )
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.get("/{knowledge_id}", response_model=KnowledgeRead)
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(
            models.KnowledgeItem,
            models.SourceDocument.repo,
            models.SourceDocument.file_path,
            models.SourceDocument.source_url,
            models.SourceDocument.title.label("document_title"),
        )
        .join(
            models.SourceDocument,
            models.KnowledgeItem.source_document_id == models.SourceDocument.id,
            isouter=True,
        )
        .where(models.KnowledgeItem.id == knowledge_id)
        .limit(1)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    item = row[0]
    return {
        "id": item.id,
        "source_document_id": item.source_document_id,
        "title": item.title,
        "summary": item.summary,
        "key_points": item.key_points,
        "tags": item.tags,
        "category": item.category,
        "quality_score": item.quality_score,
        "visibility": item.visibility,
        "repo": row[1],
        "file_path": row[2],
        "source_url": row[3],
        "document_title": row[4],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
