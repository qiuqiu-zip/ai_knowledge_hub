from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.prompt import PromptBatchDeleteRequest, PromptCreate, PromptRead, PromptUpdate

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def _normalize_prompt_input(
    *,
    title: str | None,
    content: str | None,
    tags: list[str] | None = None,
) -> tuple[str | None, str | None, list[str] | None]:
    normalized_title = title.strip() if title is not None else None
    normalized_content = content.strip() if content is not None else None
    normalized_tags = [tag.strip() for tag in (tags or []) if tag and tag.strip()]
    return normalized_title, normalized_content, normalized_tags


@router.get("", response_model=list[PromptRead])
def list_prompts(
    keyword: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.Prompt)
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(models.Prompt.title.ilike(kw), models.Prompt.content.ilike(kw)))
    if favorite is not None:
        stmt = stmt.where(models.Prompt.is_favorite == favorite)
    stmt = stmt.order_by(models.Prompt.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.post("", response_model=PromptRead)
def create_prompt(payload: PromptCreate, db: Session = Depends(get_db)):
    title, content, tags = _normalize_prompt_input(
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
    )
    if not title:
        raise HTTPException(status_code=400, detail="title cannot be empty")
    if not content:
        raise HTTPException(status_code=400, detail="content cannot be empty")

    data = payload.model_dump()
    data["title"] = title
    data["content"] = content
    data["tags"] = tags or []

    obj = models.Prompt(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{prompt_id}", response_model=PromptRead)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Prompt, prompt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return obj


@router.put("/{prompt_id}", response_model=PromptRead)
def update_prompt(prompt_id: int, payload: PromptUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Prompt, prompt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "title" in update_data or "content" in update_data or "tags" in update_data:
        title, content, tags = _normalize_prompt_input(
            title=update_data.get("title"),
            content=update_data.get("content"),
            tags=update_data.get("tags"),
        )
        if "title" in update_data:
            if not title:
                raise HTTPException(status_code=400, detail="title cannot be empty")
            update_data["title"] = title
        if "content" in update_data:
            if not content:
                raise HTTPException(status_code=400, detail="content cannot be empty")
            update_data["content"] = content
        if "tags" in update_data:
            update_data["tags"] = tags or []

    for k, v in update_data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Prompt, prompt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(obj)
    db.commit()
    return {"success": True}


@router.post("/batch-delete")
def batch_delete_prompts(payload: PromptBatchDeleteRequest, db: Session = Depends(get_db)):
    ids = list({int(pid) for pid in payload.ids if pid})
    if not ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")
    result = db.execute(delete(models.Prompt).where(models.Prompt.id.in_(ids)))
    db.commit()
    return {"success": True, "deleted": int(result.rowcount or 0)}


@router.post("/{prompt_id}/toggle-favorite")
def toggle_favorite(prompt_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Prompt, prompt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Prompt not found")
    obj.is_favorite = not obj.is_favorite
    db.commit()
    db.refresh(obj)
    return {"id": obj.id, "is_favorite": obj.is_favorite}
