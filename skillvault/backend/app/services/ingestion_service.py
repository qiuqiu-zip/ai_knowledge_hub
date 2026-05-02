from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest_github_repo(self, data: dict) -> tuple[models.Source, models.GithubRepo, models.SourceDocument, str]:
        source = self.db.scalar(
            select(models.Source).where(models.Source.url == data["html_url"], models.Source.source_type == models.SourceType.github_api)
        )
        if not source:
            source = models.Source(
                source_type=models.SourceType.github_api,
                name=data["full_name"],
                url=data["html_url"],
                owner=data.get("owner"),
                license=data.get("license"),
                metadata_json=data.get("metadata", {}),
            )
            self.db.add(source)
            self.db.flush()

        repo = self.db.scalar(select(models.GithubRepo).where(models.GithubRepo.full_name == data["full_name"]))
        if not repo:
            repo = models.GithubRepo(source_id=source.id, full_name=data["full_name"], html_url=data["html_url"])
            self.db.add(repo)

        for key in [
            "description",
            "stars",
            "forks",
            "language",
            "topics",
            "license",
            "default_branch",
            "pushed_at",
            "html_url",
            "readme_content",
            "readme_source_url",
            "commit_sha",
            "content_hash",
            "collected_at",
        ]:
            setattr(repo, key, data.get(key))

        unchanged_doc = self.db.scalar(
            select(models.SourceDocument).where(
                models.SourceDocument.source_id == source.id,
                models.SourceDocument.file_path == data.get("file_path"),
                models.SourceDocument.content_hash == data["content_hash"],
            )
        )
        if unchanged_doc:
            return source, repo, unchanged_doc, "unchanged"

        existing_doc = self.db.scalar(
            select(models.SourceDocument).where(
                models.SourceDocument.source_id == source.id,
                models.SourceDocument.file_path == data.get("file_path"),
            )
        )
        if existing_doc:
            existing_doc.title = f"{data['full_name']} README"
            existing_doc.content = data["readme_content"]
            existing_doc.source_type = models.SourceType.github_api
            existing_doc.source_url = data.get("readme_source_url") or data.get("html_url")
            existing_doc.license = data.get("license")
            existing_doc.repo = data.get("repo")
            existing_doc.file_path = data.get("file_path")
            existing_doc.commit_sha = data.get("commit_sha")
            existing_doc.content_hash = data["content_hash"]
            existing_doc.metadata_json = data.get("metadata", {})
            self.db.flush()
            return source, repo, existing_doc, "updated"

        doc = models.SourceDocument(
            source_id=source.id,
            title=f"{data['full_name']} README",
            content=data["readme_content"],
            source_type=models.SourceType.github_api,
            source_url=data.get("readme_source_url") or data.get("html_url"),
            license=data.get("license"),
            repo=data.get("repo"),
            file_path=data.get("file_path"),
            commit_sha=data.get("commit_sha"),
            content_hash=data["content_hash"],
            metadata_json=data.get("metadata", {}),
        )
        self.db.add(doc)
        self.db.flush()
        return source, repo, doc, "created"

    def ingest_source_document(self, source: models.Source, data: dict) -> tuple[models.SourceDocument, str]:
        unchanged_doc = self.db.scalar(
            select(models.SourceDocument).where(
                models.SourceDocument.source_id == source.id,
                models.SourceDocument.file_path == data.get("file_path"),
                models.SourceDocument.content_hash == data["content_hash"],
            )
        )
        if unchanged_doc:
            return unchanged_doc, "unchanged"

        existing_doc = self.db.scalar(
            select(models.SourceDocument).where(
                models.SourceDocument.source_id == source.id,
                models.SourceDocument.file_path == data.get("file_path"),
            )
        )
        if existing_doc:
            existing_doc.title = data["title"]
            existing_doc.content = data["content"]
            existing_doc.source_type = models.SourceType(data.get("source_type", models.SourceType.manual.value))
            existing_doc.source_url = data.get("source_url")
            existing_doc.license = data.get("license")
            existing_doc.repo = data.get("repo")
            existing_doc.file_path = data.get("file_path")
            existing_doc.commit_sha = data.get("commit_sha")
            existing_doc.content_hash = data["content_hash"]
            existing_doc.metadata_json = data.get("metadata", {})
            self.db.flush()
            return existing_doc, "updated"

        doc = models.SourceDocument(
            source_id=source.id,
            title=data["title"],
            content=data["content"],
            source_type=models.SourceType(data.get("source_type", models.SourceType.manual.value)),
            source_url=data.get("source_url"),
            license=data.get("license"),
            repo=data.get("repo"),
            file_path=data.get("file_path"),
            commit_sha=data.get("commit_sha"),
            content_hash=data["content_hash"],
            metadata_json=data.get("metadata", {}),
        )
        self.db.add(doc)
        self.db.flush()
        return doc, "created"
