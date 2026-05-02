from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.workers.handlers import JOB_HANDLERS

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, worker_id: str | None = None) -> None:
        self.worker_id = worker_id or settings.worker_id

    def recover_stale_jobs(self, db: Session) -> None:
        threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.job_timeout_seconds)
        stale = list(
            db.query(models.SyncJob)
            .filter(models.SyncJob.status == models.JobStatus.running)
            .filter(models.SyncJob.locked_at.is_not(None))
            .filter(models.SyncJob.locked_at < threshold)
            .all()
        )
        for job in stale:
            if job.retry_count < job.max_retry:
                job.status = models.JobStatus.pending
                job.locked_by = None
                job.locked_at = None
            else:
                job.status = models.JobStatus.failed
                job.error_message = "Job timeout and max retry exceeded"
        db.commit()

    def claim_next_job(self, db: Session) -> models.SyncJob | None:
        row = db.execute(
            text(
                """
                SELECT id
                FROM sync_job
                WHERE status = 'pending'
                  AND (available_at IS NULL OR available_at <= NOW())
                ORDER BY priority DESC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            )
        ).first()
        if not row:
            db.rollback()
            return None

        job = db.get(models.SyncJob, row[0])
        if not job:
            db.rollback()
            return None

        now = datetime.now(timezone.utc)
        job.status = models.JobStatus.running
        job.locked_by = self.worker_id
        job.locked_at = now
        job.started_at = now
        db.commit()
        db.refresh(job)
        logger.info(
            "claimed job id=%s type=%s worker=%s payload=%s",
            job.id,
            job.job_type.value if hasattr(job.job_type, "value") else job.job_type,
            self.worker_id,
            job.payload,
        )
        return job

    def run_job(self, db: Session, job: models.SyncJob) -> None:
        handler = JOB_HANDLERS.get(job.job_type)
        if not handler:
            job.status = models.JobStatus.failed
            job.error_message = f"Unsupported job type: {job.job_type}"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        try:
            logger.info(
                "running job id=%s type=%s source_id=%s document_id=%s",
                job.id,
                job.job_type.value if hasattr(job.job_type, "value") else job.job_type,
                job.payload.get("source_id") if isinstance(job.payload, dict) else None,
                job.payload.get("document_id") if isinstance(job.payload, dict) else None,
            )
            handler(db, job.payload)
            job.status = models.JobStatus.success
            job.finished_at = datetime.now(timezone.utc)
            job.error_message = None
            db.commit()
            logger.info("job success id=%s type=%s", job.id, job.job_type.value if hasattr(job.job_type, "value") else job.job_type)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            job = db.get(models.SyncJob, job.id)
            if not job:
                return
            job.retry_count += 1
            job.error_message = str(exc)
            job.locked_by = None
            job.locked_at = None
            job.finished_at = datetime.now(timezone.utc)
            if job.retry_count < job.max_retry:
                job.status = models.JobStatus.pending
            else:
                job.status = models.JobStatus.failed
            db.commit()
            logger.exception(
                "job failed id=%s type=%s retry=%s/%s error=%s",
                job.id,
                job.job_type.value if hasattr(job.job_type, "value") else job.job_type,
                job.retry_count,
                job.max_retry,
                job.error_message,
            )
