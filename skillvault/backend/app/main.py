from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import auth, digests, documents, github, jobs, knowledge, prompts, search, skills, sources
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import get_current_user
from app.db import models
from app.db.session import SessionLocal, get_db

setup_logging()
logger = logging.getLogger(__name__)

docs_url = "/docs" if settings.auth_enable_docs else None
redoc_url = "/redoc" if settings.auth_enable_redoc else None
openapi_url = "/openapi.json" if settings.auth_enable_docs or settings.auth_enable_redoc else None

app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url, openapi_url=openapi_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
protected = [Depends(get_current_user)]
app.include_router(sources.router, dependencies=protected)
app.include_router(github.router, dependencies=protected)
app.include_router(documents.router, dependencies=protected)
app.include_router(knowledge.router, dependencies=protected)
app.include_router(skills.router, dependencies=protected)
app.include_router(prompts.router, dependencies=protected)
app.include_router(search.router, dependencies=protected)
app.include_router(jobs.router, dependencies=protected)
app.include_router(digests.router, dependencies=protected)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(
    _current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "sources": db.scalar(select(func.count()).select_from(models.Source)) or 0,
        "documents": db.scalar(select(func.count()).select_from(models.SourceDocument)) or 0,
        "chunks": db.scalar(select(func.count()).select_from(models.DocumentChunk)) or 0,
        "skills": db.scalar(select(func.count()).select_from(models.Skill)) or 0,
        "prompts": db.scalar(select(func.count()).select_from(models.Prompt)) or 0,
        "jobs": [
            {
                "id": j.id,
                "job_type": j.job_type,
                "status": j.status,
                "error_message": j.error_message,
                "created_at": j.created_at,
            }
            for j in db.scalars(select(models.SyncJob).order_by(models.SyncJob.created_at.desc()).limit(10)).all()
        ],
    }


@app.on_event("startup")
def on_startup() -> None:
    if settings.app_env.lower() in {"prod", "production"} and not settings.auth_secret_key:
        raise RuntimeError("AUTH_SECRET_KEY is required in production environment")
    if not settings.auth_secret_key:
        logger.warning("AUTH_SECRET_KEY is not configured. Login token issuance/verification will fail.")
    with SessionLocal() as db:
        auth.init_admin_user(db)
