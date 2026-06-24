from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Index
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from app.config import EMBEDDING_DIM

class ContentEmbedding(Base):
    """
    Storage for semantic search embeddings.
    Groundwork for AI Homework Helper.
    """
    __tablename__ = "content_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String(50), nullable=False, index=True)  # e.g., 'course', 'lecture', 'assignment'
    source_id = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index(
            "idx_content_embeddings_vector",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
