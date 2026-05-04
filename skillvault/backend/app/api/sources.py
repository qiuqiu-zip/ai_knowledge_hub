from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.schemas.source import (
    SourceCreate,
    SourceRead,
    SourceSyncNowResponse,
    SourceSyncSettingsUpdate,
    SourceUpdate,
)
from app.services.github_service import GithubService, GithubServiceError

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _source_to_dict(row: models.Source) -> dict:
    return {
        "id": row.id,
        "source_type": row.source_type,
        "name": row.name,
        "url": row.url,
        "owner": row.owner,
        "license": row.license,
        "metadata": row.metadata_json or {},
        "auto_sync_enabled": row.auto_sync_enabled,
        "sync_interval_minutes": row.sync_interval_minutes,
        "last_sync_at": row.last_sync_at,
        "next_sync_at": row.next_sync_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _build_github_dedupe_key(db: Session, source: models.Source) -> str:
    repo_full_name = db.scalar(select(models.GithubRepo.full_name).where(models.GithubRepo.source_id == source.id).limit(1))
    if repo_full_name:
        return f"github_sync:{repo_full_name.lower()}"

    if source.url:
        try:
            normalized = GithubService.normalize_repo_full_name(source.url)
            return f"github_sync:{normalized}"
        except GithubServiceError:
            return f"github_sync:{source.url}"

    return f"github_sync:source:{source.id}"


def _find_existing_pending_or_running_job(db: Session, dedupe_key: str) -> models.SyncJob | None:
    return db.scalar(
        select(models.SyncJob)
        .where(models.SyncJob.dedupe_key == dedupe_key)
        .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running]))
        .order_by(models.SyncJob.created_at.desc())
        .limit(1)
    )


@router.get("")
def list_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(models.Source)) or 0
    offset = (page - 1) * page_size
    rows = list(
        db.scalars(
            select(models.Source)
            .order_by(models.Source.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [_source_to_dict(row) for row in rows],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=SourceRead)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    obj = models.Source(
        source_type=payload.source_type,
        name=payload.name,
        url=payload.url,
        owner=payload.owner,
        license=payload.license,
        metadata_json=payload.metadata,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _source_to_dict(obj)


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Source, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    return _source_to_dict(obj)


@router.put("/{source_id}", response_model=SourceRead)
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Source, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = payload.model_dump(exclude_unset=True)

    for k, v in update_data.items():
        if k == "metadata":
            obj.metadata_json = v
            continue
        setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return _source_to_dict(obj)


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Source, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.put("/{source_id}/sync-settings", response_model=SourceRead)
def update_sync_settings(source_id: int, payload: SourceSyncSettingsUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Source, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")

    min_interval = max(settings.min_github_sync_interval_minutes, settings.github_sync_min_interval_minutes)
    if payload.sync_interval_minutes < min_interval:
        raise HTTPException(
            status_code=400,
            detail=f"sync_interval_minutes must be >= {min_interval}",
        )
    interval = payload.sync_interval_minutes
    obj.sync_interval_minutes = interval

    if payload.auto_sync_enabled and obj.source_type != models.SourceType.github_api:
        raise HTTPException(status_code=400, detail="Auto sync is only supported for github_api source")

    obj.auto_sync_enabled = payload.auto_sync_enabled
    now = datetime.now(timezone.utc)

    if payload.auto_sync_enabled:
        if obj.next_sync_at is None:
            obj.next_sync_at = now + timedelta(minutes=interval)
    else:
        obj.next_sync_at = None

    db.commit()
    db.refresh(obj)

    if payload.auto_sync_enabled and payload.run_now:
        if not obj.url:
            raise HTTPException(status_code=400, detail="Source URL is required to sync now")
        dedupe_key = _build_github_dedupe_key(db, obj)
        existing = _find_existing_pending_or_running_job(db, dedupe_key)
        job = enqueue_job(
            db,
            job_type=models.JobType.github_sync,
            payload={"source_id": obj.id, "repo_url": obj.url},
            priority=200,
            dedupe_key=dedupe_key,
        )
        if not existing:
            obj.last_sync_at = now
            obj.next_sync_at = now + timedelta(minutes=interval)
            db.commit()
            db.refresh(obj)

    return _source_to_dict(obj)


@router.post("/{source_id}/sync-now", response_model=SourceSyncNowResponse)
def sync_now(source_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Source, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    if obj.source_type != models.SourceType.github_api:
        raise HTTPException(status_code=400, detail="Sync now is only supported for github_api source")
    if not obj.url:
        raise HTTPException(status_code=400, detail="Source URL is required")

    dedupe_key = _build_github_dedupe_key(db, obj)
    existing = _find_existing_pending_or_running_job(db, dedupe_key)
    job = enqueue_job(
        db,
        job_type=models.JobType.github_sync,
        payload={"source_id": obj.id, "repo_url": obj.url},
        priority=200,
        dedupe_key=dedupe_key,
    )
    if not existing:
        now = datetime.now(timezone.utc)
        obj.last_sync_at = now
        min_interval = max(settings.min_github_sync_interval_minutes, settings.github_sync_min_interval_minutes)
        obj.next_sync_at = now + timedelta(minutes=max(obj.sync_interval_minutes, min_interval))
        db.commit()
    return SourceSyncNowResponse(job_id=job.id, job_type=job.job_type.value, status=job.status.value)
