from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.db import models
from app.db.session import get_db
from app.schemas.github import GithubImportRequest, GithubImportResponse, GithubRepoRead
from app.services.github_service import GithubService, GithubServiceError

router = APIRouter(prefix="/api/github", tags=["github"])


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
    return list(db.scalars(select(models.GithubRepo).order_by(models.GithubRepo.created_at.desc())).all())


@router.get("/repos/{repo_id}", response_model=GithubRepoRead)
def get_github_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(models.GithubRepo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo
