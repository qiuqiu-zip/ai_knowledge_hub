from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.job import JobRead

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)):
    return list(db.scalars(select(models.SyncJob).order_by(models.SyncJob.created_at.desc())).all())


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
    job.error_message = None
    job.locked_by = None
    job.locked_at = None
    job.started_at = None
    job.finished_at = None
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
