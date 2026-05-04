from datetime import datetime
from pydantic import BaseModel, ConfigDict


class KnowledgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_document_id: int
    title: str
    summary: str
    key_points: list[str]
    tags: list[str]
    category: str | None
    quality_score: int
    visibility: str
    repo: str | None = None
    file_path: str | None = None
    source_url: str | None = None
    document_title: str | None = None
    created_at: datetime
    updated_at: datetime
