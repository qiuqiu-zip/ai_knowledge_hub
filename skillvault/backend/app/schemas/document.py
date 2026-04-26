from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import SourceType


class DocumentCreateManual(BaseModel):
    title: str
    content: str
    source_name: str
    source_url: str | None = None
    owner: str | None = None
    license: str | None = None
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class DocumentRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    source_id: int
    title: str
    content: str
    source_type: SourceType
    source_url: str | None
    license: str | None
    repo: str | None
    file_path: str | None
    commit_sha: str | None
    content_hash: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class ChunkRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    metadata: dict
    created_at: datetime
    updated_at: datetime
