import logging
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.core.config import settings
from app.db import models
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.github_service import GithubService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.skill_generator import SkillGeneratorService

logger = logging.getLogger(__name__)


_BADGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_BADGE_LINK_RE = re.compile(r"\[!\[[^\]]*\]\([^)]+\)\]\([^)]+\)")
_CODE_FENCE_RE = re.compile(r"```.*?```", flags=re.DOTALL)
_MD_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s*", flags=re.MULTILINE)
_MD_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$", flags=re.MULTILINE)
_MULTI_SPACE_RE = re.compile(r"\s+")
_MARKDOWN_NOISE_RE = re.compile(r"^\s*(npm|pip|curl|wget|docker|go|mvn|gradle)\b", flags=re.IGNORECASE)


def _clean_digest_summary(text: str | None) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    s = _CODE_FENCE_RE.sub(" ", raw)
    s = _BADGE_LINK_RE.sub(" ", s)
    s = _BADGE_MD_RE.sub(" ", s)
    s = _MD_HEADER_RE.sub("", s)
    s = _MD_TABLE_LINE_RE.sub(" ", s)
    lines = []
    for line in s.splitlines():
        x = line.strip()
        if not x:
            continue
        if x.startswith(("```", "    ")):
            continue
        if _MARKDOWN_NOISE_RE.match(x):
            continue
        if x.startswith(("- ", "* ", "+ ", "1. ", "2. ", "3. ")):
            x = x[2:].strip() if len(x) > 2 else ""
        if x:
            lines.append(x)
    s = " ".join(lines)
    s = _MULTI_SPACE_RE.sub(" ", s).strip(" -#|")
    if len(s) > 160:
        s = s[:160].rstrip() + "..."
    return s


def _normalize_github_links(source_url: str | None, repo: str | None, file_path: str | None) -> dict:
    s = (source_url or "").strip()
    repo_name = (repo or "").strip().strip("/")
    file_name = ((file_path or "").strip().split("/")[-1] if file_path else "").lower()
    repository_url = ""
    file_url = ""
    display_url = ""
    link_label = "查看来源"

    if s.startswith("https://raw.githubusercontent.com/"):
        rest = s.removeprefix("https://raw.githubusercontent.com/")
        parts = rest.split("/")
        if len(parts) >= 4:
            owner, r, branch = parts[0], parts[1], parts[2]
            path = "/".join(parts[3:])
            repository_url = f"https://github.com/{owner}/{r}"
            file_url = f"{repository_url}/blob/{branch}/{path}" if path else repository_url
            display_url = file_url or repository_url
            link_label = "查看README" if path.lower().endswith("readme.md") else "查看文件"

    elif s.startswith("https://github.com/"):
        no_query = s.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        parts = no_query.removeprefix("https://github.com/").split("/")
        if len(parts) >= 2:
            owner, r = parts[0], parts[1]
            repository_url = f"https://github.com/{owner}/{r}"
            if len(parts) >= 5 and parts[2] == "blob":
                file_url = no_query
                display_url = file_url
                link_label = "查看README" if no_query.lower().endswith("readme.md") else "查看文件"
            else:
                display_url = repository_url
                link_label = "查看仓库"

    if not repository_url and repo_name and "/" in repo_name:
        repository_url = f"https://github.com/{repo_name}"
        if file_path:
            if file_path.lower().startswith("readme"):
                link_label = "查看README"
            else:
                link_label = "查看文件"
        else:
            link_label = "查看仓库"

    # Conservative file URL fallback: only if source_url already points to github repo and has blob,
    # otherwise avoid fabricating branch.
    if not file_url and s.startswith("https://github.com/") and "/blob/" in s:
        file_url = s.split("?", 1)[0].split("#", 1)[0]

    if not display_url:
        if repository_url and link_label == "查看仓库":
            display_url = repository_url
        elif file_url:
            display_url = file_url
        elif repository_url:
            display_url = repository_url
        else:
            display_url = s

    if not link_label or link_label == "查看来源":
        if file_name == "readme.md":
            link_label = "查看README"
        elif display_url == repository_url and repository_url:
            link_label = "查看仓库"
        elif file_url:
            link_label = "查看文件"
        else:
            link_label = "查看来源"

    return {
        "repository_url": repository_url or None,
        "file_url": file_url or None,
        "display_url": display_url or None,
        "link_label": link_label,
    }


def _infer_repo_key(repo: str | None, source_url: str | None, repository_url: str | None, file_url: str | None, title: str | None) -> str:
    r = (repo or "").strip().strip("/")
    if r and "/" in r:
        return r.lower()
    for u in [repository_url, file_url, source_url]:
        x = (u or "").strip()
        if x.startswith("https://github.com/"):
            parts = x.removeprefix("https://github.com/").split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}".lower()
        if x.startswith("https://raw.githubusercontent.com/"):
            parts = x.removeprefix("https://raw.githubusercontent.com/").split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}".lower()
    fallback = (source_url or title or "unknown").strip().lower()
    return f"fallback:{fallback}" if fallback else "fallback:unknown"


def _build_project_groups(recommended_documents: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for rec in recommended_documents:
        key = _infer_repo_key(
            rec.get("repo"),
            rec.get("source_url"),
            rec.get("repository_url"),
            rec.get("file_url"),
            rec.get("title"),
        )
        g = groups.get(key)
        if not g:
            repo_name = (rec.get("repo") or "").strip()
            owner = ""
            project_name = repo_name
            if "/" in repo_name:
                owner, project_name = repo_name.split("/", 1)
            elif rec.get("repository_url", "").startswith("https://github.com/"):
                parts = rec["repository_url"].removeprefix("https://github.com/").split("/")
                if len(parts) >= 2:
                    owner, project_name = parts[0], parts[1]
                    repo_name = f"{owner}/{project_name}"
            g = {
                "repo": repo_name or None,
                "project_name": project_name or None,
                "owner": owner or None,
                "title": repo_name or rec.get("title") or "未命名项目",
                "summary": rec.get("summary") or "",
                "repository_url": rec.get("repository_url"),
                "display_url": rec.get("repository_url") or rec.get("display_url") or rec.get("source_url"),
                "link_label": "查看仓库" if rec.get("repository_url") else (rec.get("link_label") or "查看来源"),
                "change_types": [],
                "documents_count": 0,
                "recommended_count": 0,
                "documents": [],
            }
            groups[key] = g

        c = rec.get("change_type") or "updated"
        if c not in g["change_types"]:
            g["change_types"].append(c)
        g["documents_count"] += 1
        g["recommended_count"] += 1
        g["documents"].append(
            {
                "title": rec.get("title"),
                "file_path": rec.get("file_path"),
                "file_url": rec.get("file_url") or rec.get("display_url") or rec.get("source_url"),
                "link_label": rec.get("link_label") or "查看来源",
                "change_type": c,
                "summary": rec.get("summary"),
            }
        )
        if not g.get("summary") and rec.get("summary"):
            g["summary"] = rec.get("summary")
        if not g.get("repository_url") and rec.get("repository_url"):
            g["repository_url"] = rec.get("repository_url")
            g["display_url"] = rec.get("repository_url")
            g["link_label"] = "查看仓库"

    out = []
    for v in groups.values():
        if not (v.get("summary") or "").strip():
            v["summary"] = "该项目暂无可用简介，可点击链接查看详情。"
        out.append(v)
    out.sort(key=lambda x: (-int(x.get("recommended_count") or 0), str(x.get("title") or "")))
    return out


def _should_auto_summarize(doc: models.SourceDocument) -> bool:
    if not settings.auto_summarize_enabled or not settings.auto_summarize_after_sync:
        return False
    meta = doc.metadata_json or {}
    doc_type = str(meta.get("doc_type") or "")
    priority = int(meta.get("priority") or 99)
    path = (doc.file_path or "").lower()
    base = path.split("/")[-1] if path else ""
    if settings.auto_summarize_readme and (base.startswith("readme") or doc_type == "readme"):
        return True
    if settings.auto_summarize_skill_docs and doc_type in {"skill", "prompt"}:
        return True
    if settings.auto_summarize_docs and priority <= 1:
        return True
    return False


def _doc_recommend_sort_key(doc: models.SourceDocument) -> tuple:
    meta = doc.metadata_json or {}
    priority = int(meta.get("priority") or 99)
    language = str(meta.get("language") or "unknown")
    recommended = bool(meta.get("is_recommended"))
    path = (doc.file_path or "").lower()
    zh_boost = 0 if language == "zh" else 1
    return (priority, zh_boost, 0 if recommended else 1, path)


def _build_source_overview(source: models.Source, docs: list[models.SourceDocument], sync_stats: dict) -> str:
    if not docs:
        return "暂无可用文档。"
    top_docs = sorted(docs, key=_doc_recommend_sort_key)[:5]
    intro_doc = top_docs[0]
    intro = (intro_doc.content or "").strip()[:800]
    lines = [
        "# 项目简介",
        f"{source.name} 是一个 GitHub 项目，以下为自动概览。",
        "",
        "# 推荐先看",
    ]
    for idx, d in enumerate(top_docs, 1):
        meta = d.metadata_json or {}
        reason = meta.get("reason") or "核心文档"
        lines.append(f"{idx}. {d.file_path or d.title}：{reason}")
    lines.extend(
        [
            "",
            "# 同步概览",
            f"- 本次新增文档：{sync_stats.get('created_docs', 0)}",
            f"- 本次更新文档：{sync_stats.get('updated_docs', 0)}",
            f"- 本次跳过未变化：{sync_stats.get('unchanged_docs', 0)}",
            "",
            "# 内容摘录",
            intro if intro else "信息不足，建议查看 README。",
        ]
    )
    return "\n".join(lines)


def handle_github_sync(db: Session, payload: dict) -> None:
    repo_url = payload["repo_url"]
    logger.info("github_sync start repo_url=%s source_id=%s", repo_url, payload.get("source_id"))
    gh = GithubService()
    data = gh.normalize_repo_data(repo_url)

    ingestion = IngestionService(db)
    source, _repo, doc, readme_status = ingestion.ingest_github_repo(data)
    changed_docs = [doc] if readme_status in {"created", "updated"} else []
    created_count = 1 if readme_status == "created" else 0
    updated_count = 1 if readme_status == "updated" else 0
    unchanged_count = 1 if readme_status == "unchanged" else 0

    # Keep current MVP behavior (README) and additionally ingest useful docs/skills/prompts files.
    extra_docs = gh.collect_useful_documents(data)
    logger.info("github_sync fetched extra candidate docs repo=%s count=%s", data.get("full_name"), len(extra_docs))
    for extra in extra_docs:
        extra_doc, status = ingestion.ingest_source_document(source, extra)
        if status in {"created", "updated"}:
            changed_docs.append(extra_doc)
        if status == "created":
            created_count += 1
        elif status == "updated":
            updated_count += 1
        else:
            unchanged_count += 1

    db.commit()

    for created_doc in changed_docs:
        enqueue_job(
            db,
            job_type=models.JobType.document_chunk,
            payload={"document_id": created_doc.id},
            priority=150,
            dedupe_key=f"{models.JobType.document_chunk.value}:doc:{created_doc.id}",
        )
    if isinstance(payload, dict):
        payload["sync_stats"] = {
            "created_docs": created_count,
            "updated_docs": updated_count,
            "unchanged_docs": unchanged_count,
            "queued_chunk_docs": len(changed_docs),
        }
    sync_stats = {
        "created_docs": created_count,
        "updated_docs": updated_count,
        "unchanged_docs": unchanged_count,
        "queued_chunk_docs": len(changed_docs),
    }
    metadata = dict(source.metadata_json or {})
    metadata["last_sync_stats"] = {**sync_stats, "synced_at": datetime.now(timezone.utc).isoformat()}

    # Auto summarize only a limited number of high-value documents.
    summary_candidates = [d for d in changed_docs if _should_auto_summarize(d)]
    summary_candidates = sorted(summary_candidates, key=_doc_recommend_sort_key)[: min(settings.github_sync_auto_summary_limit, settings.auto_summarize_max_docs_per_source)]
    for d in summary_candidates:
        d_meta = dict(d.metadata_json or {})
        d_meta["summary_status"] = "pending"
        d.metadata_json = d_meta
        enqueue_job(
            db,
            job_type=models.JobType.summarize,
            payload={"document_id": d.id},
            priority=130,
            dedupe_key=f"{models.JobType.summarize.value}:doc:{d.id}",
        )

    overview_docs = list(
        db.scalars(select(models.SourceDocument).where(models.SourceDocument.source_id == source.id)).all()
    )
    metadata["recommended_documents"] = [
        {
            "document_id": d.id,
            "title": d.title,
            "file_path": d.file_path,
            "source_url": d.source_url,
            "reason": (d.metadata_json or {}).get("reason"),
            "language": (d.metadata_json or {}).get("language"),
        }
        for d in sorted(overview_docs, key=_doc_recommend_sort_key)[:8]
    ]
    try:
        llm = LLMService()
        picked = sorted(overview_docs, key=_doc_recommend_sort_key)[:5]
        context = "\n\n".join(
            [
                f"[{d.file_path or d.title}] {(d.content or '')[:1800]}"
                for d in picked
            ]
        )
        metadata["overview"] = llm.generate_repo_overview(
            repo_name=source.name,
            docs_context=context,
            sync_stats=sync_stats,
        )
    except Exception:
        metadata["overview"] = _build_source_overview(source, overview_docs, sync_stats)
    source.metadata_json = metadata
    db.commit()
    logger.info(
        "github_sync done repo=%s source_id=%s created=%s updated=%s unchanged=%s chunk_jobs=%s",
        data.get("full_name"),
        source.id,
        created_count,
        updated_count,
        unchanged_count,
        len(changed_docs),
    )


def handle_document_chunk(db: Session, payload: dict) -> None:
    doc = db.get(models.SourceDocument, payload["document_id"])
    if not doc:
        raise ValueError("Document not found")

    db.execute(delete(models.DocumentChunk).where(models.DocumentChunk.document_id == doc.id))
    chunk_service = ChunkService()
    chunks = chunk_service.split_text(doc.content)

    for chunk in chunks:
        db.add(
            models.DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                token_count=chunk["token_count"],
                metadata_json=chunk["metadata"],
            )
        )

    db.commit()

    enqueue_job(
        db,
        job_type=models.JobType.document_embed,
        payload={"document_id": doc.id},
        priority=140,
        dedupe_key=f"{models.JobType.document_embed.value}:doc:{doc.id}",
    )
    # Summarize is queued by github_sync selection policy or user manual action.
    if settings.auto_skill_generate_enabled:
        enqueue_job(
            db,
            job_type=models.JobType.skill_generate,
            payload={"document_id": doc.id},
            priority=120,
            dedupe_key=f"{models.JobType.skill_generate.value}:doc:{doc.id}",
        )


def handle_document_embed(db: Session, payload: dict) -> None:
    doc_id = payload["document_id"]
    chunks = list(
        db.scalars(
            select(models.DocumentChunk)
            .where(models.DocumentChunk.document_id == doc_id)
            .order_by(models.DocumentChunk.chunk_index.asc())
        ).all()
    )
    if not chunks:
        raise ValueError("No chunks found. Run chunk job first")

    emb_service = EmbeddingService()
    vectors = emb_service.embed_chunks([c.content for c in chunks])

    for chunk, vec in zip(chunks, vectors, strict=False):
        chunk.embedding = vec
    db.commit()


def handle_summarize(db: Session, payload: dict) -> None:
    doc = db.get(models.SourceDocument, payload["document_id"])
    if not doc:
        raise ValueError("Document not found")

    llm = LLMService()
    summary = llm.summarize_document(doc.content, file_path=doc.file_path, repo=doc.repo)

    item = db.scalar(
        select(models.KnowledgeItem)
        .where(models.KnowledgeItem.source_document_id == doc.id)
        .order_by(models.KnowledgeItem.updated_at.desc())
        .limit(1)
    )
    if not item:
        item = models.KnowledgeItem(source_document_id=doc.id, title=doc.title, summary="")
        db.add(item)

    item.title = summary.get("title") or doc.title
    item.summary = summary.get("summary") or ""
    item.key_points = summary.get("key_points") or []
    item.tags = summary.get("tags") or []
    item.category = summary.get("category") or "general"
    item.quality_score = int(summary.get("quality_score") or 50)
    item.visibility = summary.get("visibility") or "private"
    meta = dict(doc.metadata_json or {})
    meta["summary"] = item.summary
    meta["summary_status"] = "success"
    meta["summary_updated_at"] = datetime.now(timezone.utc).isoformat()
    if summary.get("recommend_level"):
        meta["recommend_level"] = summary.get("recommend_level")
    doc.metadata_json = meta
    db.commit()


def handle_skill_generate(db: Session, payload: dict) -> None:
    doc = db.get(models.SourceDocument, payload["document_id"])
    if not doc:
        raise ValueError("Document not found")
    svc = SkillGeneratorService(db)
    svc.generate_from_document(doc)
    db.commit()


def handle_daily_digest(db: Session, payload: dict) -> None:
    now = datetime.now(timezone.utc)
    digest_date = payload.get("date") or now.date().isoformat()
    window_hours = int(payload.get("window_hours") or 24)
    window_start = now - timedelta(hours=window_hours)
    logger.info(
        "daily_digest start digest_date=%s window_hours=%s window_start=%s window_end=%s",
        digest_date,
        window_hours,
        window_start.isoformat(),
        now.isoformat(),
    )

    github_jobs = list(
        db.scalars(
            select(models.SyncJob)
            .where(models.SyncJob.job_type == models.JobType.github_sync)
            .where(models.SyncJob.created_at >= window_start)
            .order_by(models.SyncJob.created_at.desc())
        ).all()
    )
    sources_synced = len({j.payload.get("source_id") for j in github_jobs if isinstance(j.payload, dict) and j.payload.get("source_id")})
    succeeded_jobs = sum(1 for j in github_jobs if j.status == models.JobStatus.success)
    failed_jobs = sum(1 for j in github_jobs if j.status == models.JobStatus.failed)
    failed_reasons = [j.error_message for j in github_jobs if j.status == models.JobStatus.failed and j.error_message]

    created_docs = db.scalar(
        select(func.count())
        .select_from(models.SourceDocument)
        .where(models.SourceDocument.source_type == models.SourceType.github_api)
        .where(models.SourceDocument.created_at >= window_start)
    ) or 0
    updated_docs = db.scalar(
        select(func.count())
        .select_from(models.SourceDocument)
        .where(models.SourceDocument.source_type == models.SourceType.github_api)
        .where(models.SourceDocument.updated_at >= window_start)
        .where(models.SourceDocument.created_at < window_start)
    ) or 0
    unchanged_docs = sum((j.payload or {}).get("sync_stats", {}).get("unchanged_docs", 0) for j in github_jobs if isinstance(j.payload, dict))

    chunks_created = db.scalar(
        select(func.count())
        .select_from(models.DocumentChunk)
        .where(models.DocumentChunk.created_at >= window_start)
    ) or 0
    embedded_chunks = db.scalar(
        select(func.count())
        .select_from(models.DocumentChunk)
        .where(models.DocumentChunk.updated_at >= window_start)
        .where(models.DocumentChunk.embedding.is_not(None))
    ) or 0
    summaries_created = db.scalar(
        select(func.count())
        .select_from(models.KnowledgeItem)
        .where(models.KnowledgeItem.created_at >= window_start)
    ) or 0
    skill_candidates_created = db.scalar(
        select(func.count())
        .select_from(models.SkillCandidate)
        .where(models.SkillCandidate.created_at >= window_start)
    ) or 0
    logger.info(
        "daily_digest stats github_jobs=%s sources_synced=%s succeeded=%s failed=%s created_docs=%s updated_docs=%s unchanged_docs=%s chunks=%s embedded=%s summaries=%s skills=%s",
        len(github_jobs),
        sources_synced,
        succeeded_jobs,
        failed_jobs,
        created_docs,
        updated_docs,
        unchanged_docs,
        chunks_created,
        embedded_chunks,
        summaries_created,
        skill_candidates_created,
    )

    recommended_rows = list(
        db.scalars(
            select(models.SourceDocument)
            .where(models.SourceDocument.updated_at >= window_start)
            .where(
                (models.SourceDocument.file_path.ilike("%readme%"))
                | (models.SourceDocument.file_path.ilike("%skill%"))
                | (models.SourceDocument.file_path.ilike("%prompt%"))
                | (models.SourceDocument.file_path.ilike("%guide%"))
                | (models.SourceDocument.file_path.ilike("%tutorial%"))
            )
            .order_by(models.SourceDocument.updated_at.desc())
            .limit(8)
        ).all()
    )
    recommended_documents = []
    for d in recommended_rows:
        meta = d.metadata_json or {}
        summary = (meta.get("summary") or "").strip()
        if not summary:
            summary = (d.content or "").strip().replace("\n", " ")
        summary = _clean_digest_summary(summary)
        if not summary:
            summary = "该项目暂无可用简介，可点击链接查看详情。"
        change_type = "updated"
        if d.created_at and d.created_at >= window_start:
            change_type = "created"
        links = _normalize_github_links(d.source_url, d.repo, d.file_path)
        recommended_documents.append(
            {
                "document_id": d.id,
                "title": d.title,
                "repo": d.repo,
                "file_path": d.file_path,
                "source_url": d.source_url,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "summary": summary,
                "change_type": change_type,
                **links,
            }
        )

    lines = [
        f"SkillVault Daily Digest - {digest_date}",
        "",
        "今天同步概览：",
        f"- 同步 source：{sources_synced} 个",
        f"- 成功任务：{succeeded_jobs} 个",
        f"- 失败任务：{failed_jobs} 个",
        f"- 新增文档：{created_docs} 篇",
        f"- 更新文档：{updated_docs} 篇",
        f"- 未变化文档：{unchanged_docs} 篇",
        f"- 新增 chunks：{chunks_created} 个",
        f"- 完成 embedding：{embedded_chunks} 个",
        f"- 新增摘要：{summaries_created} 条",
        f"- 新增 skill 草稿：{skill_candidates_created} 条",
        "",
        "推荐查看：",
    ]
    if recommended_documents:
        for idx, rec in enumerate(recommended_documents, 1):
            lines.append(f"{idx}. {rec.get('repo') or '-'} - {rec.get('file_path') or rec.get('title')}")
            lines.append(f"   来源：{rec.get('source_url') or '-'}")
            if rec.get("summary"):
                lines.append(f"   简介：{rec.get('summary')}")
    else:
        if created_docs == 0 and updated_docs == 0:
            lines.append("- 暂无推荐内容：本日未发现新增或更新项目。")
        else:
            lines.append("- 暂无推荐内容：今日没有符合推荐条件的文档。")
    if failed_reasons:
        lines.extend(["", "失败任务："])
        for idx, reason in enumerate(failed_reasons[:10], 1):
            lines.append(f"{idx}. {reason}")

    project_groups = _build_project_groups(recommended_documents)
    projects_total = len(project_groups)
    projects_recommended = sum(1 for g in project_groups if int(g.get("recommended_count") or 0) > 0)
    projects_created = sum(1 for g in project_groups if "created" in set(g.get("change_types") or []))
    projects_updated = sum(1 for g in project_groups if "updated" in set(g.get("change_types") or []))

    stats = {
        "github_sync_jobs": len(github_jobs),
        "succeeded_jobs": succeeded_jobs,
        "failed_jobs": failed_jobs,
        "sources_synced": sources_synced,
        "documents_created": int(created_docs),
        "documents_updated": int(updated_docs),
        "documents_unchanged": int(unchanged_docs),
        "chunks_created": int(chunks_created),
        "embedded_chunks": int(embedded_chunks),
        "summaries_created": int(summaries_created),
        "skill_candidates_created": int(skill_candidates_created),
        "recommended_documents": recommended_documents,
        "project_groups": project_groups,
        "projects_total": projects_total,
        "projects_created": projects_created,
        "projects_updated": projects_updated,
        "projects_recommended": projects_recommended,
        "failed_reasons": failed_reasons[:20],
    }

    digest = db.scalar(select(models.DailyDigest).where(models.DailyDigest.digest_date == digest_date).limit(1))
    created = False
    if not digest:
        digest = models.DailyDigest(digest_date=digest_date, title=f"SkillVault Daily Digest - {digest_date}", content="", stats_json={})
        db.add(digest)
        created = True
    digest.title = f"SkillVault Daily Digest - {digest_date}"
    digest.content = "\n".join(lines)
    digest.stats_json = stats
    logger.info("daily_digest content_ready digest_date=%s content_empty=%s", digest_date, not bool(digest.content.strip()))
    db.commit()
    logger.info(
        "daily_digest done digest_date=%s digest_id=%s created=%s recommended_count=%s failed_reasons_count=%s",
        digest_date,
        digest.id,
        created,
        len(recommended_documents),
        len(failed_reasons),
    )


JOB_HANDLERS = {
    models.JobType.github_sync: handle_github_sync,
    models.JobType.document_chunk: handle_document_chunk,
    models.JobType.document_embed: handle_document_embed,
    models.JobType.summarize: handle_summarize,
    models.JobType.skill_generate: handle_skill_generate,
    models.JobType.daily_digest: handle_daily_digest,
}
