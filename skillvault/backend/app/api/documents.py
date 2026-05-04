import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.db import models
from app.db.session import get_db
from app.schemas.document import DocumentCreateManual, DocumentRead

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _document_to_dict(row: models.SourceDocument) -> dict:
    return {
        "id": row.id,
        "source_id": row.source_id,
        "title": row.title,
        "content": row.content,
        "source_type": row.source_type,
        "source_url": row.source_url,
        "license": row.license,
        "repo": row.repo,
        "file_path": row.file_path,
        "commit_sha": row.commit_sha,
        "content_hash": row.content_hash,
        "metadata": row.metadata_json or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _enqueue_document_job(
    db: Session,
    *,
    doc_id: int,
    job_type: models.JobType,
    priority: int,
) -> dict:
    doc = db.get(models.SourceDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    dedupe_key = f"{job_type.value}:doc:{doc_id}"
    job = enqueue_job(
        db,
        job_type=job_type,
        payload={"document_id": doc_id},
        priority=priority,
        dedupe_key=dedupe_key,
    )
    if job_type == models.JobType.summarize:
        meta = dict(doc.metadata_json or {})
        meta["summary_status"] = "pending"
        doc.metadata_json = meta
        db.commit()
    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "status": job.status,
    }


@router.get("")
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    repo: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    recommended: bool | None = Query(default=None),
    has_summary: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(models.SourceDocument)
    if repo and repo.strip():
        stmt = stmt.where(models.SourceDocument.repo.ilike(f"%{repo.strip()}%"))
    if doc_type:
        stmt = stmt.where(models.SourceDocument.metadata_json["doc_type"].astext == doc_type)
    if language:
        stmt = stmt.where(models.SourceDocument.metadata_json["language"].astext == language)
    if recommended is not None:
        stmt = stmt.where(models.SourceDocument.metadata_json["is_recommended"].astext == ("true" if recommended else "false"))
    if has_summary is not None:
        summary_expr = models.SourceDocument.metadata_json["summary"].astext
        if has_summary:
            stmt = stmt.where(and_(summary_expr.is_not(None), summary_expr != ""))
        else:
            stmt = stmt.where((summary_expr.is_(None)) | (summary_expr == ""))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    rows = list(
        db.scalars(
            stmt.order_by(models.SourceDocument.created_at.desc()).offset(offset).limit(page_size)
        ).all()
    )
    return {
        "items": [_document_to_dict(row) for row in rows],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(models.SourceDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_to_dict(doc)


@router.post("/manual", response_model=DocumentRead)
def create_manual_document(payload: DocumentCreateManual, db: Session = Depends(get_db)):
    source = models.Source(
        source_type=models.SourceType.manual,
        name=payload.source_name,
        url=payload.source_url,
        owner=payload.owner,
        license=payload.license,
        metadata_json=payload.metadata,
    )
    db.add(source)
    db.flush()

    content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    doc = models.SourceDocument(
        source_id=source.id,
        title=payload.title,
        content=payload.content,
        source_type=models.SourceType.manual,
        source_url=payload.source_url,
        license=payload.license,
        content_hash=content_hash,
        metadata_json=payload.metadata,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _document_to_dict(doc)


@router.post("/{doc_id}/chunk")
def enqueue_chunk(doc_id: int, db: Session = Depends(get_db)):
    return _enqueue_document_job(db, doc_id=doc_id, job_type=models.JobType.document_chunk, priority=150)


@router.post("/{doc_id}/embed")
def enqueue_embed(doc_id: int, db: Session = Depends(get_db)):
    return _enqueue_document_job(db, doc_id=doc_id, job_type=models.JobType.document_embed, priority=140)


@router.post("/{doc_id}/summarize")
def enqueue_summarize(doc_id: int, db: Session = Depends(get_db)):
    return _enqueue_document_job(db, doc_id=doc_id, job_type=models.JobType.summarize, priority=130)


@router.post("/{doc_id}/skill-draft")
def enqueue_skill_draft(doc_id: int, db: Session = Depends(get_db)):
    return _enqueue_document_job(db, doc_id=doc_id, job_type=models.JobType.skill_generate, priority=120)
