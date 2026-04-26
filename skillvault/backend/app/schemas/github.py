from datetime import datetime
from pydantic import BaseModel, ConfigDict, HttpUrl


class GithubImportRequest(BaseModel):
    repo_url: HttpUrl


class GithubImportResponse(BaseModel):
    job_id: int


class GithubRepoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    full_name: str
    description: str | None
    stars: int
    forks: int
    language: str | None
    topics: list[str]
    license: str | None
    default_branch: str | None
    pushed_at: str | None
    html_url: str
    readme_source_url: str | None
    commit_sha: str | None
    content_hash: str | None
    collected_at: str | None
    created_at: datetime
    updated_at: datetime
