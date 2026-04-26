from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.jobs import enqueue_job
from app.db import models
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.github_service import GithubService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.skill_generator import SkillGeneratorService


def handle_github_sync(db: Session, payload: dict) -> None:
    repo_url = payload["repo_url"]
    gh = GithubService()
    data = gh.normalize_repo_data(repo_url)

    source, _repo, doc, created = IngestionService(db).ingest_github_repo(data)
    db.commit()

    if created:
        enqueue_job(
            db,
            job_type=models.JobType.document_chunk,
            payload={"document_id": doc.id},
            priority=150,
            dedupe_key=f"{models.JobType.document_chunk.value}:doc:{doc.id}",
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
    enqueue_job(
        db,
        job_type=models.JobType.summarize,
        payload={"document_id": doc.id},
        priority=130,
        dedupe_key=f"{models.JobType.summarize.value}:doc:{doc.id}",
    )
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
    summary = llm.summarize_document(doc.content)

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
    db.commit()


def handle_skill_generate(db: Session, payload: dict) -> None:
    doc = db.get(models.SourceDocument, payload["document_id"])
    if not doc:
        raise ValueError("Document not found")
    svc = SkillGeneratorService(db)
    svc.generate_from_document(doc)
    db.commit()


JOB_HANDLERS = {
    models.JobType.github_sync: handle_github_sync,
    models.JobType.document_chunk: handle_document_chunk,
    models.JobType.document_embed: handle_document_embed,
    models.JobType.summarize: handle_summarize,
    models.JobType.skill_generate: handle_skill_generate,
}
