from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.event_bus import event_bus


@dataclass(slots=True)
class SearchDocument:
    collection: str
    document_id: str
    title: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResource:
    resource_type: str
    resource_id: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    search_score: float = 0.0


@dataclass(slots=True)
class SearchResult:
    collection: str
    document_id: str
    title: str
    score: float
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    search_score: float = 0.0


class GlobalSearchService:
    """Unified in-process search service for platform resources and legacy documents."""

    def __init__(self) -> None:
        self._documents: Dict[str, SearchDocument] = {}
        self._resources: Dict[Tuple[str, str], SearchResource] = {}
        self._event_handlers_registered = False
        self._register_event_handlers()

    def reset(self) -> None:
        self._documents.clear()
        self._resources.clear()

    def index_document(self, document: SearchDocument) -> None:
        self._documents[document.document_id] = document

    def index_resource(
        self,
        resource_type: str,
        resource_id: str,
        title: str,
        description: str = "",
        tags: Optional[Sequence[str]] = None,
        owner: Optional[str] = None,
        permissions: Optional[Sequence[str]] = None,
        last_updated: Optional[str] = None,
    ) -> SearchResource:
        resource = SearchResource(
            resource_type=resource_type,
            resource_id=resource_id,
            title=title,
            description=description,
            tags=list(tags or []),
            owner=owner,
            permissions=list(permissions or []),
            last_updated=last_updated,
        )
        self._resources[(resource_type, resource_id)] = resource
        return resource

    def _register_event_handlers(self) -> None:
        if self._event_handlers_registered:
            return
        event_bus.subscribe("user.registered", self._handle_user_registered)
        event_bus.subscribe("organization.created", self._handle_organization_created)
        event_bus.subscribe("workspace.created", self._handle_workspace_created)
        event_bus.subscribe("file.uploaded", self._handle_file_uploaded)
        event_bus.subscribe("wallet.created", self._handle_wallet_created)
        event_bus.subscribe("ai.conversation.created", self._handle_ai_conversation_created)
        event_bus.subscribe("prediction.created", self._handle_prediction_created)
        event_bus.subscribe("marketplace.listing.created", self._handle_marketplace_listing_created)
        event_bus.subscribe("notification.created", self._handle_notification_created)
        event_bus.subscribe("api.key.created", self._handle_api_key_created)
        self._event_handlers_registered = True

    async def _handle_user_registered(self, event) -> None:
        payload = event.payload or {}
        user_id = payload.get("user_id") or payload.get("id")
        email = payload.get("email") or ""
        if user_id:
            self.index_resource(
                resource_type="users",
                resource_id=str(user_id),
                title=str(user_id),
                description=email,
                tags=["user"],
                owner=str(user_id),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_organization_created(self, event) -> None:
        payload = event.payload or {}
        org_id = payload.get("organization_id") or payload.get("id")
        if org_id:
            self.index_resource(
                resource_type="organizations",
                resource_id=str(org_id),
                title=str(payload.get("name") or org_id),
                description=str(payload.get("description") or ""),
                tags=["organization"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_workspace_created(self, event) -> None:
        payload = event.payload or {}
        workspace_id = payload.get("workspace_id") or payload.get("id")
        if workspace_id:
            self.index_resource(
                resource_type="workspaces",
                resource_id=str(workspace_id),
                title=str(payload.get("name") or workspace_id),
                description=str(payload.get("description") or ""),
                tags=["workspace"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_file_uploaded(self, event) -> None:
        payload = event.payload or {}
        file_id = payload.get("file_id") or payload.get("id")
        if file_id:
            self.index_resource(
                resource_type="files",
                resource_id=str(file_id),
                title=str(payload.get("filename") or file_id),
                description=str(payload.get("description") or ""),
                tags=["file"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_wallet_created(self, event) -> None:
        payload = event.payload or {}
        wallet_id = payload.get("wallet_id") or payload.get("id")
        if wallet_id:
            self.index_resource(
                resource_type="wallets",
                resource_id=str(wallet_id),
                title=str(payload.get("name") or wallet_id),
                description=str(payload.get("description") or ""),
                tags=["wallet"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_ai_conversation_created(self, event) -> None:
        payload = event.payload or {}
        conversation_id = payload.get("conversation_id") or payload.get("id")
        if conversation_id:
            self.index_resource(
                resource_type="ai_conversations",
                resource_id=str(conversation_id),
                title=str(payload.get("title") or conversation_id),
                description=str(payload.get("description") or ""),
                tags=["ai", "conversation"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_prediction_created(self, event) -> None:
        payload = event.payload or {}
        prediction_id = payload.get("prediction_id") or payload.get("id")
        if prediction_id:
            self.index_resource(
                resource_type="predictions",
                resource_id=str(prediction_id),
                title=str(payload.get("title") or prediction_id),
                description=str(payload.get("description") or ""),
                tags=["prediction"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_marketplace_listing_created(self, event) -> None:
        payload = event.payload or {}
        listing_id = payload.get("listing_id") or payload.get("id")
        if listing_id:
            self.index_resource(
                resource_type="marketplace_listings",
                resource_id=str(listing_id),
                title=str(payload.get("title") or listing_id),
                description=str(payload.get("description") or ""),
                tags=["marketplace", "listing"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_notification_created(self, event) -> None:
        payload = event.payload or {}
        notification_id = payload.get("notification_id") or payload.get("id")
        if notification_id:
            self.index_resource(
                resource_type="notifications",
                resource_id=str(notification_id),
                title=str(payload.get("title") or notification_id),
                description=str(payload.get("body") or ""),
                tags=["notification"],
                owner=payload.get("user_id"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    async def _handle_api_key_created(self, event) -> None:
        payload = event.payload or {}
        api_key_id = payload.get("api_key_id") or payload.get("id")
        if api_key_id:
            self.index_resource(
                resource_type="api_keys",
                resource_id=str(api_key_id),
                title=str(payload.get("name") or api_key_id),
                description=str(payload.get("description") or ""),
                tags=["api-key"],
                owner=payload.get("owner"),
                permissions=["read"],
                last_updated=event.timestamp.isoformat(),
            )

    def search(
        self,
        query: str,
        collection: Optional[str] = None,
        resource_type: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        category: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
        sort_by: str = "relevance",
    ) -> List[SearchResult]:
        normalized = (query or "").strip().lower()
        requested_tags = {tag.strip().lower() for tag in (tags or []) if tag and tag.strip()}
        requested_category = (category or "").strip().lower()
        offset = max(page - 1, 0) * limit
        results: List[SearchResult] = []

        for document in self._documents.values():
            if collection and document.collection != collection:
                continue
            if self._matches_query(document.title, document.content, normalized):
                score = self._score(document.title, document.content, normalized)
                results.append(
                    SearchResult(
                        collection=document.collection,
                        document_id=document.document_id,
                        title=document.title,
                        score=score,
                    )
                )

        for resource in self._resources.values():
            if resource_type and resource.resource_type != resource_type:
                continue
            if requested_tags and not requested_tags.issubset({tag.lower() for tag in resource.tags}):
                continue
            if requested_category and requested_category not in {resource.resource_type.lower(), resource.resource_type.replace("_", "-").lower()}:
                continue
            if normalized:
                if not self._matches_query(resource.title, resource.description, normalized):
                    continue
            score = self._score(resource.title, resource.description, normalized)
            if requested_tags:
                score += 0.1 * min(len(requested_tags), 3)
            if resource.owner:
                score += 0.02
            results.append(
                SearchResult(
                    collection=resource.resource_type,
                    document_id=resource.resource_id,
                    title=resource.title,
                    score=score,
                    resource_type=resource.resource_type,
                    resource_id=resource.resource_id,
                    description=resource.description,
                    tags=resource.tags,
                    owner=resource.owner,
                    permissions=resource.permissions,
                    last_updated=resource.last_updated,
                    search_score=score,
                )
            )

        ranked = sorted(results, key=lambda item: (item.score, item.title.lower()), reverse=True)
        if sort_by == "date" and results:
            ranked = sorted(ranked, key=lambda item: (item.last_updated or "", item.score), reverse=True)
        return ranked[offset: offset + limit]

    def search_resources(
        self,
        query: str = "",
        resource_type: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        category: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
        sort_by: str = "relevance",
    ) -> List[SearchResult]:
        return self.search(
            query=query,
            resource_type=resource_type,
            tags=tags,
            category=category,
            limit=limit,
            page=page,
            sort_by=sort_by,
        )

    def types(self) -> List[str]:
        return sorted({resource.resource_type for resource in self._resources.values()})

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "documents": len(self._documents),
            "resources": len(self._resources),
            "event_handlers_registered": self._event_handlers_registered,
        }

    def _matches_query(self, title: str, content: str, query: str) -> bool:
        if not query:
            return True
        haystack = " ".join([title, content]).lower()
        if query in haystack:
            return True
        if query.startswith(""):
            return False
        tokens = re.split(r"[^a-z0-9]+", query)
        return any(token and token in haystack for token in tokens if token)

    def _score(self, title: str, content: str, query: str) -> float:
        if not query:
            return 1.0
        haystack = " ".join([title, content]).lower()
        if query in haystack:
            return 2.0 + (1.0 if query in title.lower() else 0.0)
        tokens = [token for token in re.split(r"[^a-z0-9]+", query) if token]
        if not tokens:
            return 0.5
        match_score = 0.0
        for token in tokens:
            if token in haystack:
                match_score += 0.5
        return max(match_score, 0.5)
