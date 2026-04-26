from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import CandidateStatus, SourceType


class SkillCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_document_id: int
    title: str
    scenario: str | None
    input_schema: dict
    prompt_template: str
    output_format: str | None
    examples: list[dict]
    tags: list[str]
    source_url: str | None
    license: str | None
    status: CandidateStatus
    created_at: datetime
    updated_at: datetime


class SkillCreate(BaseModel):
    title: str
    description: str | None = None
    scenario: str | None = None
    input_schema: dict = Field(default_factory=dict)
    prompt_template: str
    output_format: str | None = None
    examples: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_type: SourceType
    source_refs: list[dict] = Field(default_factory=list)
    version: str = "1.0.0"


class SkillUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    scenario: str | None = None
    input_schema: dict | None = None
    prompt_template: str | None = None
    output_format: str | None = None
    examples: list[dict] | None = None
    tags: list[str] | None = None
    source_type: SourceType | None = None
    source_refs: list[dict] | None = None
    version: str | None = None


class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class GenerateSkillRequest(BaseModel):
    source_document_id: int


class AcceptCandidateRequest(BaseModel):
    description: str | None = None
