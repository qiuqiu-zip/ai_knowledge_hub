from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.core.config import settings
from app.core.security import get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.digest import DailyDigestRead

router = APIRouter(prefix="/api/digests", tags=["digests"])


class DigestGenerateRequest(BaseModel):
    digest_date: str | None = None


def _get_digest_tz() -> ZoneInfo:
    tz_name = settings.digest_timezone or settings.app_timezone or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Shanghai")


def _digest_to_dict(row: models.DailyDigest) -> dict:
    return {
        "id": row.id,
        "digest_date": row.digest_date,
        "title": row.title,
        "content": row.content,
        "stats_json": row.stats_json or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("")
def list_digests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.DailyDigest)
    total = db.scalar(select(func.count()).select_from(models.DailyDigest)) or 0
    offset = (page - 1) * page_size
    rows = list(
        db.scalars(
            stmt.order_by(models.DailyDigest.digest_date.desc()).offset(offset).limit(page_size)
        ).all()
    )
    return {
        "items": [_digest_to_dict(row) for row in rows],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.get("/today")
def get_today_digest(db: Session = Depends(get_db)):
    tz = _get_digest_tz()
    digest_date = datetime.now(timezone.utc).astimezone(tz).date().isoformat()
    row = db.scalar(select(models.DailyDigest).where(models.DailyDigest.digest_date == digest_date).limit(1))
    if not row:
        return {"exists": False, "digest_date": digest_date, "message": "今日简报尚未生成"}
    return {"exists": True, "digest_date": digest_date, "digest": _digest_to_dict(row)}


@router.get("/{digest_id}", response_model=DailyDigestRead)
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    row = db.get(models.DailyDigest, digest_id)
    if not row:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _digest_to_dict(row)


@router.post("/generate")
def generate_digest(
    req: DigestGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可手动生成或刷新简报")

    tz = _get_digest_tz()
    digest_date = req.digest_date or datetime.now(timezone.utc).astimezone(tz).date().isoformat()
    dedupe_key = f"daily_digest:{digest_date}"

    existing_job = db.scalar(
        select(models.SyncJob)
        .where(models.SyncJob.dedupe_key == dedupe_key)
        .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running]))
        .order_by(models.SyncJob.created_at.desc())
        .limit(1)
    )
    if existing_job:
        return {
            "created": False,
            "job_id": existing_job.id,
            "digest_date": digest_date,
            "dedupe_key": dedupe_key,
            "reason": f"job already exists status={existing_job.status}",
        }

    job = enqueue_job(
        db,
        job_type=models.JobType.daily_digest,
        payload={"date": digest_date, "window_hours": 24, "timezone": str(tz), "force_refresh": True},
        priority=80,
        max_retry=2,
        dedupe_key=dedupe_key,
    )
    existing_digest = db.scalar(
        select(models.DailyDigest).where(models.DailyDigest.digest_date == digest_date).limit(1)
    )
    stats = (existing_digest.stats_json or {}) if existing_digest else {}
    return {
        "created": True,
        "created_or_updated": "updated" if existing_digest else "created",
        "job_id": job.id,
        "digest_date": digest_date,
        "dedupe_key": dedupe_key,
        "recommended_count": len((stats.get("recommended_documents") or [])),
        "new_documents": int(stats.get("documents_created") or 0),
        "updated_documents": int(stats.get("documents_updated") or 0),
        "sync_success": int(stats.get("succeeded_jobs") or 0),
        "sync_failed": int(stats.get("failed_jobs") or 0),
        "message": "已提交今日简报生成/刷新任务",
        "reason": "job created",
    }
