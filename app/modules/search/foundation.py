from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class SearchDocument:
    collection: str
    document_id: str
    title: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    collection: str
    document_id: str
    title: str
    score: float


class GlobalSearchService:
    """Simple abstraction for indexing and searching platform entities."""

    def __init__(self) -> None:
        self._documents: Dict[str, SearchDocument] = {}

    def index_document(self, document: SearchDocument) -> None:
        self._documents[document.document_id] = document

    def search(self, query: str, collection: Optional[str] = None) -> List[SearchResult]:
        normalized = query.lower()
        results: List[SearchResult] = []
        for document in self._documents.values():
            if collection and document.collection != collection:
                continue
            if normalized in document.title.lower() or normalized in document.content.lower():
                score = 1.0 if normalized in document.title.lower() else 0.5
                results.append(
                    SearchResult(
                        collection=document.collection,
                        document_id=document.document_id,
                        title=document.title,
                        score=score,
                    )
                )
        return sorted(results, key=lambda item: item.score, reverse=True)
