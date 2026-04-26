from __future__ import annotations

import hashlib
import random
import httpx

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self) -> None:
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.api_key = settings.embedding_api_key
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    def _mock_embedding(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rnd = random.Random(seed)
        return [rnd.uniform(-1, 1) for _ in range(self.dimension)]

    def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            return self._mock_embedding(text)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": text}
        try:
            res = httpx.post(f"{self.base_url}/embeddings", headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            emb = data["data"][0]["embedding"]
            return emb
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingServiceError(f"Embedding API failed: {exc}") from exc

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        return [self.embed_text(chunk) for chunk in chunks]
