from __future__ import annotations

import hashlib
import json
import logging
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import EMBEDDING_DIM, EMBEDDING_MODEL, EMBEDDING_CACHE_TTL
from app.models.content_embedding import ContentEmbedding
from app.core.dependencies import get_orchestrator
from app.core.cache import get_cache

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self._st_model = None
        self._cache = get_cache()

    def _get_st_model(self):
        """Lazily load the sentence-transformers model to save RAM during bootstrap."""
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"[embedding] Loading model: {EMBEDDING_MODEL}")
                self._st_model = SentenceTransformer(EMBEDDING_MODEL)
            except ImportError:
                logger.error("[embedding] sentence-transformers not installed — semantic search disabled")
                return None
            except Exception as e:
                logger.error(f"[embedding] Failed to load model {EMBEDDING_MODEL}: {e}")
                return None
        return self._st_model

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            if i + chunk_size >= len(words):
                break
        return chunks

    async def embed_text(self, text: str) -> List[float]:
        orch = get_orchestrator()
        if orch and orch.num_models_ready() > 0:
            try:
                return await self._call_ai_core_embedding(text)
            except Exception as e:
                logger.warning(f"ai_core embedding failed, falling back: {e}")

        model = self._get_st_model()
        if model is None:
             return [0.0] * EMBEDDING_DIM
        embedding = model.encode(text).tolist()
        return embedding

    async def _call_ai_core_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("ai_core embedding not implemented, falling back to sentence-transformers")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]

    async def semantic_search(
        self, query: str, source_type: str, top_k: int, db: AsyncSession
    ) -> List[ContentEmbedding]:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cache_key = f"sem_search:{source_type}:{query_hash}"

        cached_result = await self._cache.get(cache_key)
        if cached_result:
            ids = cached_result
            stmt = select(ContentEmbedding).where(ContentEmbedding.id.in_(ids))
            res = await db.execute(stmt)
            return list(res.scalars().all())

        query_vector = await self.embed_text(query)

        stmt = (
            select(ContentEmbedding)
            .where(ContentEmbedding.source_type == source_type)
            .order_by(ContentEmbedding.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )

        res = await db.execute(stmt)
        embeddings = list(res.scalars().all())

        await self._cache.set(cache_key, [e.id for e in embeddings], ttl=EMBEDDING_CACHE_TTL)

        return embeddings

embedding_service = EmbeddingService()
