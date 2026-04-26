from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.db.models import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType
    payload: dict
    priority: int = 100
    max_retry: int = 3


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: JobType
    status: JobStatus
    priority: int
    payload: dict
    retry_count: int
    max_retry: int
    error_message: str | None
    locked_by: str | None
    dedupe_key: str | None
    available_at: datetime | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RetryJobResponse(BaseModel):
    id: int
    status: JobStatus
