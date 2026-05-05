import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.core.security import get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.github import GithubImportRequest, GithubImportResponse, GithubRepoRead
from app.services.github_discovery_service import run_github_discovery
from app.services.github_service import GithubService, GithubServiceError

router = APIRouter(prefix="/api/github", tags=["github"])
logger = logging.getLogger(__name__)


@router.post("/import", response_model=GithubImportResponse)
def import_github_repo(payload: GithubImportRequest, db: Session = Depends(get_db)):
    try:
        repo_full_name = GithubService.normalize_repo_full_name(str(payload.repo_url))
    except GithubServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = enqueue_job(
        db,
        job_type=models.JobType.github_sync,
        payload={"repo_url": str(payload.repo_url)},
        priority=200,
        max_retry=3,
        dedupe_key=f"github_sync:{repo_full_name}",
    )
    return GithubImportResponse(job_id=job.id)


@router.get("/repos", response_model=list[GithubRepoRead])
def list_github_repos(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(models.GithubRepo).order_by(models.GithubRepo.stars.desc(), models.GithubRepo.created_at.desc())
        ).all()
    )


@router.get("/repos/{repo_id}", response_model=GithubRepoRead)
def get_github_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(models.GithubRepo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo


@router.post("/discover-now")
def discover_now(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可手动触发项目发现")
    try:
        return run_github_discovery(db, force=True)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("discover-now failed")
        raise HTTPException(status_code=500, detail=f"触发 GitHub 项目发现失败：{exc}") from exc
