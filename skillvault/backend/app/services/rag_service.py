from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import models
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService


class RagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding = EmbeddingService()
        self.llm = LLMService()

    def search_keyword(self, query: str, top_k: int = 5) -> list[models.DocumentChunk]:
        stmt = (
            select(models.DocumentChunk)
            .join(models.SourceDocument, models.SourceDocument.id == models.DocumentChunk.document_id)
            .where(
                or_(
                    models.DocumentChunk.content.ilike(f"%{query}%"),
                    models.SourceDocument.title.ilike(f"%{query}%"),
                )
            )
            .order_by(models.DocumentChunk.id.desc())
            .limit(top_k)
        )
        return list(self.db.scalars(stmt).all())

    def search_similar(self, query: str, top_k: int = 5) -> list[models.DocumentChunk]:
        q_emb = self.embedding.embed_text(query)
        stmt = (
            select(models.DocumentChunk)
            .where(models.DocumentChunk.embedding.is_not(None))
            .order_by(models.DocumentChunk.embedding.cosine_distance(q_emb))
            .limit(top_k)
        )
        return list(self.db.scalars(stmt).all())

    def ask(self, question: str, top_k: int = 5) -> dict:
        chunks = self.search_similar(question, top_k=top_k)
        if not chunks:
            chunks = self.search_keyword(question, top_k=top_k)

        contexts = []
        citations = []
        for chunk in chunks:
            doc = self.db.get(models.SourceDocument, chunk.document_id)
            if not doc:
                continue
            contexts.append(f"[{chunk.id}] {chunk.content}")
            citations.append(
                {
                    "source_url": doc.source_url,
                    "title": doc.title,
                    "file_path": doc.file_path,
                    "repo": doc.repo,
                    "license": doc.license,
                    "chunk_id": chunk.id,
                }
            )

        context_text = "\n\n".join(contexts)[:14000]
        answer = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": "Use only provided context to answer. If insufficient, clearly say uncertain.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context_text}",
                },
            ]
        )
        return {"answer": answer, "citations": citations}
