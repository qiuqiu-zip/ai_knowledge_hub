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
    auth_secret_key: str | None = None
    auth_access_token_expire_minutes: int = 1440
    auth_algorithm: str = "HS256"
    admin_username: str = "admin"
    admin_password: str = "lsq123456"
    auth_enable_docs: bool = True
    auth_enable_redoc: bool = True

    worker_id: str = "worker-1"
    worker_poll_interval_seconds: int = 3
    job_timeout_seconds: int = 600
    scheduler_poll_interval_seconds: int = 60
    scheduler_max_jobs_per_tick: int = 5
    default_github_sync_interval_minutes: int = 1440
    min_github_sync_interval_minutes: int = 10
    github_sync_min_interval_minutes: int = 1440
    github_sync_max_sources_per_run: int = 5
    github_sync_max_files_per_source: int = 50
    github_sync_max_file_size_bytes: int = 1048576
    github_sync_daily_max_jobs: int = 20
    github_sync_daily_max_files: int = 500
    github_sync_prefer_chinese: bool = True
    github_sync_auto_summary_limit: int = 5
    github_discovery_enabled: bool = True
    github_discovery_interval_minutes: int = 1440
    github_discovery_min_stars: int = 100
    github_discovery_max_repos_per_run: int = 10
    github_discovery_queries: str = "llm,rag,agent,developer-tools,backend,database,redis,java,python"
    github_discovery_prefer_chinese: bool = True

    auto_summarize_enabled: bool = True
    auto_summarize_readme_only: bool = True
    auto_summarize_after_sync: bool = True
    auto_summarize_max_docs_per_source: int = 5
    auto_summarize_readme: bool = True
    auto_summarize_skill_docs: bool = True
    auto_summarize_docs: bool = False
    auto_skill_generate_enabled: bool = False

    digest_daily_hour: int = 9
    app_timezone: str = "Asia/Shanghai"
    digest_timezone: str | None = None

    @property
    def github_discovery_queries_list(self) -> list[str]:
        return [q.strip() for q in (self.github_discovery_queries or "").split(",") if q.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
