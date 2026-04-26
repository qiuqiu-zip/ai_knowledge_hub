from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import SourceType


class PromptCreate(BaseModel):
    title: str
    content: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    source_type: SourceType = SourceType.manual
    source_refs: list[dict] = Field(default_factory=list)
    is_favorite: bool = False


class PromptUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    source_type: SourceType | None = None
    source_refs: list[dict] | None = None
    is_favorite: bool | None = None


class PromptRead(PromptCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PromptBatchDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
