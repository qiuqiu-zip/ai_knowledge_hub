import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(models.SourceDocument).order_by(models.SourceDocument.created_at.desc())).all())
    return [_document_to_dict(row) for row in rows]


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
