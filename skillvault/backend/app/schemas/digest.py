from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DailyDigestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    digest_date: str
    title: str
    content: str
    stats_json: dict
    created_at: datetime
    updated_at: datetime
