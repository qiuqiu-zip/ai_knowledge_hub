from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import (
    Boolean,
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.db.base import Base, IDMixin, TimestampMixin


class SourceType(str, enum.Enum):
    github_api = "github_api"
    manual = "manual"
    web_page = "web_page"
    upload_file = "upload_file"
    rss = "rss"
    imported = "imported"


class JobType(str, enum.Enum):
    github_sync = "github_sync"
    document_chunk = "document_chunk"
    document_embed = "document_embed"
    summarize = "summarize"
    skill_generate = "skill_generate"
    daily_digest = "daily_digest"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class CandidateStatus(str, enum.Enum):
    draft = "draft"
    reviewed = "reviewed"
    accepted = "accepted"
    rejected = "rejected"


class Source(Base, IDMixin, TimestampMixin):
    __tablename__ = "source"

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024))
    owner: Mapped[str | None] = mapped_column(String(255))
    license: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=settings.default_github_sync_interval_minutes,
        server_default=text(str(settings.default_github_sync_interval_minutes)),
        nullable=False,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    documents: Mapped[list[SourceDocument]] = relationship(back_populates="source", cascade="all, delete-orphan")


class GithubRepo(Base, IDMixin, TimestampMixin):
    __tablename__ = "github_repo"

    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(128))
    topics: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255))
    default_branch: Mapped[str | None] = mapped_column(String(128))
    pushed_at: Mapped[str | None] = mapped_column(String(64))
    html_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    readme_content: Mapped[str | None] = mapped_column(Text)
    readme_source_url: Mapped[str | None] = mapped_column(String(1024))
    commit_sha: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    collected_at: Mapped[str | None] = mapped_column(String(64))


class SourceDocument(Base, IDMixin, TimestampMixin):
    __tablename__ = "source_document"

    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    license: Mapped[str | None] = mapped_column(String(255))
    repo: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(512))
    commit_sha: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    source: Mapped[Source] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, IDMixin, TimestampMixin):
    __tablename__ = "document_chunk"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),)

    document_id: Mapped[int] = mapped_column(ForeignKey("source_document.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimension), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class KnowledgeItem(Base, IDMixin, TimestampMixin):
    __tablename__ = "knowledge_item"

    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_document.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    quality_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    visibility: Mapped[str] = mapped_column(String(50), default="private", nullable=False)

    document: Mapped[SourceDocument] = relationship(back_populates="knowledge_items")


class SkillCandidate(Base, IDMixin, TimestampMixin):
    __tablename__ = "skill_candidate"

    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_document.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario: Mapped[str | None] = mapped_column(Text)
    input_schema: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str | None] = mapped_column(Text)
    examples: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    license: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CandidateStatus] = mapped_column(Enum(CandidateStatus), default=CandidateStatus.draft, nullable=False)


class Skill(Base, IDMixin, TimestampMixin):
    __tablename__ = "skill"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scenario: Mapped[str | None] = mapped_column(Text)
    input_schema: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str | None] = mapped_column(Text)
    examples: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_refs: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)


class Prompt(Base, IDMixin, TimestampMixin):
    __tablename__ = "prompt"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_refs: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(default=False, nullable=False)


class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "sync_job"

    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retry: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_key: Mapped[str | None] = mapped_column(String(255), index=True)
    available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        server_default=func.now(),
    )


class DailyDigest(Base, IDMixin, TimestampMixin):
    __tablename__ = "daily_digest"

    digest_date: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    stats_json: Mapped[dict] = mapped_column("stats", JSONB, default=dict, nullable=False)
