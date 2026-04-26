from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import documents, github, jobs, knowledge, prompts, search, skills, sources
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import verify_admin_token
from app.db import models
from app.db.session import get_db

setup_logging()

app = FastAPI(title=settings.app_name, dependencies=[Depends(verify_admin_token)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(github.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(skills.router)
app.include_router(prompts.router)
app.include_router(search.router)
app.include_router(jobs.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
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
