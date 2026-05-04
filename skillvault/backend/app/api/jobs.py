from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.job import JobRead

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    job_type: models.JobType | None = Query(default=None),
    status: models.JobStatus | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(models.SyncJob)
    if job_type is not None:
        stmt = stmt.where(models.SyncJob.job_type == job_type)
    if status is not None:
        stmt = stmt.where(models.SyncJob.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            stmt.order_by(models.SyncJob.created_at.desc()).offset(offset).limit(page_size)
        ).all()
    )
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.SyncJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobRead)
def retry_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.SyncJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = models.JobStatus.pending
    job.retry_count = 0
    job.error_message = None
    job.locked_by = None
    job.locked_at = None
    job.started_at = None
    job.finished_at = None
    job.available_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def enqueue_job(
    db: Session,
    *,
    job_type: models.JobType,
    payload: dict,
    priority: int = 100,
    max_retry: int = 3,
    dedupe_key: str | None = None,
    available_at: datetime | None = None,
) -> models.SyncJob:
    if dedupe_key:
        existing = db.scalar(
            select(models.SyncJob)
            .where(models.SyncJob.dedupe_key == dedupe_key)
            .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running]))
            .order_by(models.SyncJob.created_at.desc())
            .limit(1)
        )
        if existing:
            return existing

    job = models.SyncJob(
        job_type=job_type,
        status=models.JobStatus.pending,
        priority=priority,
        payload=payload,
        max_retry=max_retry,
        retry_count=0,
        dedupe_key=dedupe_key,
        available_at=available_at or datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
