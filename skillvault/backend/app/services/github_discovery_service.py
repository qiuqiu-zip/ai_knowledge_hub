from __future__ import annotations

import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.core.config import settings
from app.db import models
from app.services.github_service import GithubRateLimitError, GithubService

logger = logging.getLogger(__name__)


def _score_repo(item: dict) -> float:
    stars = int(item.get("stargazers_count") or 0)
    if not settings.github_discovery_prefer_chinese:
        return float(stars)
    chinese = GithubService.is_chinese_friendly_repo(item)
    boost = min(100, int(stars * 0.1) + 20) if chinese else 0
    return float(stars + boost)


def run_github_discovery(db: Session, *, force: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    result = {
        "enabled": bool(settings.github_discovery_enabled),
        "force": force,
        "queries": settings.github_discovery_queries_list,
        "min_stars": settings.github_discovery_min_stars,
        "max_repos_per_run": settings.github_discovery_max_repos_per_run,
        "fetched": 0,
        "filtered": 0,
        "filter_reasons": {"fork": 0, "archived": 0, "low_stars": 0},
        "created_sources": 0,
        "existing_sources": 0,
        "updated_sources": 0,
        "enqueued_jobs": 0,
        "skipped_jobs": 0,
        "rate_limit": {"limited": False, "message": ""},
        "message": "",
    }

    if not settings.github_discovery_enabled:
        result["message"] = "GitHub 自动发现未启用，请检查 GITHUB_DISCOVERY_ENABLED。"
        logger.info(result["message"])
        return result

    if not result["queries"]:
        result["message"] = "GitHub 自动发现查询关键词为空，已跳过。"
        logger.warning(result["message"])
        return result

    gh = GithubService()
    raw_candidates: list[dict] = []
    for query in result["queries"]:
        try:
            repos = gh.search_repositories(
                query=query,
                min_stars=settings.github_discovery_min_stars,
                per_page=min(settings.github_discovery_max_repos_per_run * 3, 50),
            )
            logger.info("github discovery query=%s fetched=%s", query, len(repos))
            result["fetched"] += len(repos)
            for item in repos:
                stars = int(item.get("stargazers_count") or 0)
                if bool(item.get("fork")):
                    result["filter_reasons"]["fork"] += 1
                    continue
                if bool(item.get("archived")):
                    result["filter_reasons"]["archived"] += 1
                    continue
                if stars < settings.github_discovery_min_stars:
                    result["filter_reasons"]["low_stars"] += 1
                    continue
                raw_candidates.append(item)
        except GithubRateLimitError as exc:
            result["rate_limit"]["limited"] = True
            result["rate_limit"]["message"] = str(exc)
            logger.warning("github discovery rate-limited query=%s err=%s", query, exc)
            break
        except Exception as exc:  # noqa: BLE001
            logger.exception("github discovery query failed query=%s err=%s", query, exc)

    dedup: dict[str, dict] = {}
    for item in raw_candidates:
        full_name = str(item.get("full_name") or "").lower()
        if not full_name:
            continue
        if full_name not in dedup or int(item.get("stargazers_count") or 0) > int(dedup[full_name].get("stargazers_count") or 0):
            dedup[full_name] = item
    candidates = list(dedup.values())
    candidates.sort(key=_score_repo, reverse=True)
    selected = candidates[: settings.github_discovery_max_repos_per_run]

    result["filtered"] = sum(result["filter_reasons"].values())

    for item in selected:
        full_name = str(item.get("full_name") or "").strip()
        if not full_name or "/" not in full_name:
            continue

        owner, repo = full_name.split("/", 1)
        repo_url = f"https://github.com/{owner}/{repo}"
        stars = int(item.get("stargazers_count") or 0)
        metadata = {
            "stars": stars,
            "language": item.get("language"),
            "description": item.get("description"),
            "topics": item.get("topics") or [],
            "pushed_at": item.get("pushed_at"),
            "html_url": item.get("html_url"),
            "is_chinese_friendly": GithubService.is_chinese_friendly_repo(item),
            "discovered_by": "scheduler_github_discovery",
            "discovered_at": now.isoformat(),
        }

        source = db.scalar(
            select(models.Source)
            .where(models.Source.source_type == models.SourceType.github_api)
            .where(models.Source.url == repo_url)
            .limit(1)
        )
        created = False
        if not source:
            source = db.scalar(
                select(models.Source)
                .where(models.Source.source_type == models.SourceType.github_api)
                .where(models.Source.name == full_name)
                .limit(1)
            )
        if not source:
            source = models.Source(
                source_type=models.SourceType.github_api,
                name=full_name,
                url=repo_url,
                owner=owner,
                license=(item.get("license") or {}).get("spdx_id") if isinstance(item.get("license"), dict) else None,
                metadata_json=metadata,
                auto_sync_enabled=True,
                sync_interval_minutes=max(settings.default_github_sync_interval_minutes, settings.github_sync_min_interval_minutes),
                next_sync_at=now,
            )
            db.add(source)
            db.flush()
            result["created_sources"] += 1
            created = True
        else:
            result["existing_sources"] += 1
            source.name = source.name or full_name
            source.url = source.url or repo_url
            source.owner = source.owner or owner
            source.auto_sync_enabled = True
            source.sync_interval_minutes = max(source.sync_interval_minutes, settings.github_sync_min_interval_minutes)
            if not source.next_sync_at:
                source.next_sync_at = now
            merged = dict(source.metadata_json or {})
            merged.update(metadata)
            source.metadata_json = merged
            result["updated_sources"] += 1

        github_repo = db.scalar(select(models.GithubRepo).where(models.GithubRepo.full_name == full_name).limit(1))
        if not github_repo:
            github_repo = models.GithubRepo(
                source_id=source.id,
                full_name=full_name,
                description=item.get("description"),
                stars=stars,
                forks=int(item.get("forks_count") or 0),
                language=item.get("language"),
                topics=item.get("topics") or [],
                license=(item.get("license") or {}).get("spdx_id") if isinstance(item.get("license"), dict) else None,
                default_branch=item.get("default_branch"),
                pushed_at=item.get("pushed_at"),
                html_url=item.get("html_url") or repo_url,
                readme_content=None,
                readme_source_url=None,
                commit_sha=None,
                content_hash=None,
                collected_at=now.isoformat(),
            )
            db.add(github_repo)
        else:
            github_repo.source_id = source.id
            github_repo.description = item.get("description")
            github_repo.stars = stars
            github_repo.forks = int(item.get("forks_count") or 0)
            github_repo.language = item.get("language")
            github_repo.topics = item.get("topics") or []
            github_repo.license = (item.get("license") or {}).get("spdx_id") if isinstance(item.get("license"), dict) else github_repo.license
            github_repo.default_branch = item.get("default_branch")
            github_repo.pushed_at = item.get("pushed_at")
            github_repo.html_url = item.get("html_url") or github_repo.html_url

        dedupe_key = f"github_sync:{full_name.lower()}"
        existing_job = db.scalar(
            select(models.SyncJob)
            .where(models.SyncJob.dedupe_key == dedupe_key)
            .where(models.SyncJob.status.in_([models.JobStatus.pending, models.JobStatus.running]))
            .limit(1)
        )
        if existing_job:
            result["skipped_jobs"] += 1
        else:
            enqueue_job(
                db,
                job_type=models.JobType.github_sync,
                payload={"source_id": source.id, "repo_url": source.url},
                priority=210 if created else 200,
                max_retry=3,
                dedupe_key=dedupe_key,
            )
            result["enqueued_jobs"] += 1

    db.commit()

    if result["created_sources"] == 0 and result["enqueued_jobs"] == 0:
        if result["fetched"] == 0:
            result["message"] = "本轮未拉取到候选仓库，请检查 GITHUB_TOKEN 或查询条件。"
        else:
            result["message"] = "本轮未新增来源，可能都已存在或被过滤。"
    else:
        result["message"] = (
            f"发现完成：新增 {result['created_sources']} 个来源，"
            f"更新 {result['updated_sources']} 个来源，"
            f"入队 {result['enqueued_jobs']} 个同步任务。"
        )
    return result
