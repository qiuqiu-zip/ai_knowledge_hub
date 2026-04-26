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
    created_at: datetime
    updated_at: datetime
