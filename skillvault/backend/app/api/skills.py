from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.db import models
from app.db.session import get_db
from app.schemas.skill import (
    GenerateSkillRequest,
    SkillCandidateRead,
    SkillCreate,
    SkillRead,
    SkillUpdate,
)

router = APIRouter(tags=["skills"])


@router.get("/api/skill-candidates")
def list_skill_candidates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.SkillCandidate)
    total = db.scalar(select(func.count()).select_from(models.SkillCandidate)) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            stmt.order_by(models.SkillCandidate.created_at.desc()).offset(offset).limit(page_size)
        ).all()
    )
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.post("/api/skill-candidates/generate")
def generate_candidate(payload: GenerateSkillRequest, db: Session = Depends(get_db)):
    if not db.get(models.SourceDocument, payload.source_document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    job = enqueue_job(
        db,
        job_type=models.JobType.skill_generate,
        payload={"document_id": payload.source_document_id},
        priority=120,
        dedupe_key=f"{models.JobType.skill_generate.value}:doc:{payload.source_document_id}",
    )
    return {"job_id": job.id}


@router.post("/api/skill-candidates/{candidate_id}/accept", response_model=SkillRead)
def accept_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(models.SkillCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Skill candidate not found")

    doc = db.get(models.SourceDocument, candidate.source_document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Source document missing")

    skill = models.Skill(
        title=candidate.title,
        description=f"Accepted from candidate #{candidate.id}",
        scenario=candidate.scenario,
        input_schema=candidate.input_schema,
        prompt_template=candidate.prompt_template,
        output_format=candidate.output_format,
        examples=candidate.examples,
        tags=candidate.tags,
        source_type=doc.source_type,
        source_refs=[
            {
                "source_url": candidate.source_url,
                "license": candidate.license,
                "document_id": doc.id,
            }
        ],
        version="1.0.0",
    )
    candidate.status = models.CandidateStatus.accepted
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/api/skills")
def list_skills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.Skill)
    total = db.scalar(select(func.count()).select_from(models.Skill)) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            stmt.order_by(models.Skill.created_at.desc()).offset(offset).limit(page_size)
        ).all()
    )
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.post("/api/skills", response_model=SkillRead)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    obj = models.Skill(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/api/skills/{skill_id}", response_model=SkillRead)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Skill, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Skill not found")
    return obj


@router.put("/api/skills/{skill_id}", response_model=SkillRead)
def update_skill(skill_id: int, payload: SkillUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Skill, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Skill not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/api/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Skill, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(obj)
    db.commit()
    return {"ok": True}
