from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SkillVault"
    app_env: str = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://skillvault:skillvault@postgres:5432/skillvault"
    github_token: str | None = None
    github_min_request_interval_seconds: int = 1
    github_rate_limit_remaining_threshold: int = 10
    github_rate_limit_sleep_buffer_seconds: int = 5
    github_max_retries: int = 3

    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    embedding_api_key: str | None = None
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    admin_token: str | None = None

    worker_id: str = "worker-1"
    worker_poll_interval_seconds: int = 3
    job_timeout_seconds: int = 600
    scheduler_poll_interval_seconds: int = 60
    scheduler_max_jobs_per_tick: int = 5
    default_github_sync_interval_minutes: int = 1440
    min_github_sync_interval_minutes: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
