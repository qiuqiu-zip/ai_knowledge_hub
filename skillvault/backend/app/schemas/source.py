from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import SourceType


class SourceBase(BaseModel):
    source_type: SourceType
    name: str
    url: str | None = None
    owner: str | None = None
    license: str | None = None
    metadata: dict = Field(default_factory=dict)


class SourceCreate(SourceBase):
    model_config = ConfigDict(populate_by_name=True)


class SourceUpdate(BaseModel):
    source_type: SourceType | None = None
    name: str | None = None
    url: str | None = None
    owner: str | None = None
    license: str | None = None
    metadata: dict | None = None

    model_config = ConfigDict(populate_by_name=True)


class SourceRead(SourceBase):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    auto_sync_enabled: bool
    sync_interval_minutes: int
    last_sync_at: datetime | None = None
    next_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SourceSyncSettingsUpdate(BaseModel):
    auto_sync_enabled: bool
    sync_interval_minutes: int
    run_now: bool = False


class SourceSyncNowResponse(BaseModel):
    job_id: int
    job_type: str
    status: str
