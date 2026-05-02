from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.api.jobs import enqueue_job
from app.core.config import settings
from app.core.logging import setup_logging
from app.db import models
from app.db.session import SessionLocal
from app.services.github_service import GithubService, GithubServiceError

logger = logging.getLogger(__name__)


def _build_dedupe_key(source: models.Source, repo_full_name: str | None) -> str:
    if repo_full_name:
        return f"github_sync:{repo_full_name.lower()}"
    if source.url:
        try:
            normalized = GithubService.normalize_repo_full_name(source.url)
            return f"github_sync:{normalized}"
        except GithubServiceError:
            return f"github_sync:{source.url}"
    return f"github_sync:source:{source.id}"


def run_scheduler_once() -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        jobs_today = db.scalar(
            select(func.count())
            .select_from(models.SyncJob)
            .where(models.SyncJob.job_type == models.JobType.github_sync)
            .where(models.SyncJob.created_at >= today_start)
        ) or 0
        files_today = db.scalar(
            select(func.count())
            .select_from(models.SourceDocument)
            .where(models.SourceDocument.source_type == models.SourceType.github_api)
            .where(models.SourceDocument.created_at >= today_start)
        ) or 0
        if jobs_today >= settings.github_sync_daily_max_jobs or files_today >= settings.github_sync_daily_max_files:
            logger.warning(
                "skip scheduling github_sync due to daily budget jobs_today=%s/%s files_today=%s/%s",
                jobs_today,
                settings.github_sync_daily_max_jobs,
                files_today,
                settings.github_sync_daily_max_files,
            )
            _enqueue_daily_digest_if_due(db, now)
            return

        due_sources = list(
            db.scalars(
                select(models.Source)
                .where(models.Source.source_type == models.SourceType.github_api)
                .where(models.Source.auto_sync_enabled.is_(True))
                .where(models.Source.next_sync_at.is_not(None))
                .where(models.Source.next_sync_at <= now)
                .order_by(models.Source.next_sync_at.asc())
                .limit(settings.github_sync_max_sources_per_run)
            ).all()
        )
        logger.info("found %s due sources (max_sources_per_run=%s)", len(due_sources), settings.github_sync_max_sources_per_run)

        for source in due_sources:
            try:
                if not source.url:
                    logger.warning("skip source_id=%s because url is empty", source.id)
                    continue

                repo_full_name = db.scalar(
                    select(models.GithubRepo.full_name).where(models.GithubRepo.source_id == source.id).limit(1)
                )
                dedupe_key = _build_dedupe_key(source, repo_full_name)

                existing = db.scalar(
                    select(models.SyncJob)
                    .where(models.SyncJob.dedupe_key == dedupe_key)
                    .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running]))
                    .limit(1)
                )
                if existing:
                    source.next_sync_at = now + timedelta(minutes=5)
                    db.commit()
                    logger.info(
                        "skip because existing job found source_id=%s dedupe_key=%s existing_job_id=%s",
                        source.id,
                        dedupe_key,
                        existing.id,
                    )
                    logger.info("update next_sync_at source_id=%s next_sync_at=%s", source.id, source.next_sync_at)
                    continue

                payload = {"source_id": source.id, "repo_url": source.url}
                if repo_full_name:
                    payload["repo_full_name"] = repo_full_name

                job = enqueue_job(
                    db,
                    job_type=models.JobType.github_sync,
                    payload=payload,
                    priority=200,
                    max_retry=3,
                    dedupe_key=dedupe_key,
                )
                min_interval = max(settings.min_github_sync_interval_minutes, settings.github_sync_min_interval_minutes)
                interval = max(source.sync_interval_minutes, min_interval)
                source.last_sync_at = now
                source.next_sync_at = now + timedelta(minutes=interval)
                db.commit()
                logger.info(
                    "enqueue github_sync for source_id=%s repo=%s job_id=%s",
                    source.id,
                    repo_full_name or source.url,
                    job.id,
                )
                logger.info("update next_sync_at source_id=%s next_sync_at=%s", source.id, source.next_sync_at)
            except Exception:
                db.rollback()
                logger.exception("scheduler error for source_id=%s", source.id)
        _enqueue_daily_digest_if_due(db, now)


def _enqueue_daily_digest_if_due(db, now: datetime) -> None:
    digest_date = now.date().isoformat()
    dedupe_key = f"daily_digest:{digest_date}"
    logger.info(
        "daily_digest schedule check now=%s hour=%s digest_daily_hour=%s digest_date=%s dedupe_key=%s",
        now.isoformat(),
        now.hour,
        settings.digest_daily_hour,
        digest_date,
        dedupe_key,
    )

    if now.hour < settings.digest_daily_hour:
        logger.info(
            "skip daily_digest because generation hour not reached current_hour=%s required_hour=%s",
            now.hour,
            settings.digest_daily_hour,
        )
        return

    existing = db.scalar(
        select(models.SyncJob)
        .where(models.SyncJob.dedupe_key == dedupe_key)
        .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running, models.JobStatus.success]))
        .limit(1)
    )
    if existing:
        logger.info(
            "skip daily_digest because existing job found dedupe_key=%s job_id=%s status=%s",
            dedupe_key,
            existing.id,
            existing.status,
        )
        return

    existing_digest = db.scalar(
        select(models.DailyDigest).where(models.DailyDigest.digest_date == digest_date).limit(1)
    )
    if existing_digest:
        logger.info(
            "skip daily_digest because digest record already exists digest_date=%s digest_id=%s",
            digest_date,
            existing_digest.id,
        )
        return

    job = enqueue_job(
        db,
        job_type=models.JobType.daily_digest,
        payload={"date": digest_date, "window_hours": 24},
        priority=80,
        max_retry=2,
        dedupe_key=dedupe_key,
    )
    logger.info("enqueue daily_digest date=%s dedupe_key=%s job_id=%s", digest_date, dedupe_key, job.id)


def main() -> None:
    setup_logging()
    logger.info("scheduler started poll_interval=%ss", settings.scheduler_poll_interval_seconds)
    while True:
        try:
            run_scheduler_once()
        except Exception:
            logger.exception("scheduler loop error")
        time.sleep(settings.scheduler_poll_interval_seconds)


if __name__ == "__main__":
    main()
