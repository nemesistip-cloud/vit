from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class IdentityOrganization:
    id: str
    name: str
    slug: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class IdentityTeam:
    id: str
    organization_id: str
    name: str
    slug: str


@dataclass(slots=True)
class IdentityRole:
    id: str
    name: str
    slug: str
    permissions: List[str] = field(default_factory=list)


@dataclass(slots=True)
class IdentityPermission:
    id: str
    slug: str
    description: Optional[str] = None


@dataclass(slots=True)
class IdentitySession:
    id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    revoked: bool = False


@dataclass(slots=True)
class TrustedDevice:
    id: str
    user_id: str
    name: str
    fingerprint: str
    trusted: bool = True


@dataclass(slots=True)
class APIKey:
    id: str
    user_id: str
    name: str
    prefix: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False


class IdentityService:
    """Shared identity abstraction for organizations, roles, sessions, and API keys."""

    def __init__(self) -> None:
        self.organizations: Dict[str, IdentityOrganization] = {}
        self.teams: Dict[str, IdentityTeam] = {}
        self.roles: Dict[str, IdentityRole] = {}
        self.permissions: Dict[str, IdentityPermission] = {}
        self.sessions: Dict[str, IdentitySession] = {}
        self.devices: Dict[str, TrustedDevice] = {}
        self.api_keys: Dict[str, APIKey] = {}

    def create_organization(self, organization_id: str, name: str, slug: str) -> IdentityOrganization:
        org = IdentityOrganization(id=organization_id, name=name, slug=slug)
        self.organizations[organization_id] = org
        return org

    def create_team(self, team_id: str, organization_id: str, name: str, slug: str) -> IdentityTeam:
        team = IdentityTeam(id=team_id, organization_id=organization_id, name=name, slug=slug)
        self.teams[team_id] = team
        return team

    def create_role(self, role_id: str, name: str, slug: str, permissions: Optional[List[str]] = None) -> IdentityRole:
        role = IdentityRole(id=role_id, name=name, slug=slug, permissions=permissions or [])
        self.roles[role_id] = role
        return role

    def create_permission(self, permission_id: str, slug: str, description: Optional[str] = None) -> IdentityPermission:
        permission = IdentityPermission(id=permission_id, slug=slug, description=description)
        self.permissions[permission_id] = permission
        return permission

    def create_session(self, session_id: str, user_id: str) -> IdentitySession:
        session = IdentitySession(id=session_id, user_id=user_id)
        self.sessions[session_id] = session
        return session

    def revoke_session(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is not None:
            session.revoked = True

    def trust_device(self, device_id: str, user_id: str, name: str, fingerprint: str) -> TrustedDevice:
        device = TrustedDevice(id=device_id, user_id=user_id, name=name, fingerprint=fingerprint)
        self.devices[device_id] = device
        return device

    def create_api_key(self, api_key_id: str, user_id: str, name: str, prefix: str) -> APIKey:
        api_key = APIKey(id=api_key_id, user_id=user_id, name=name, prefix=prefix)
        self.api_keys[api_key_id] = api_key
        return api_key

    def revoke_api_key(self, api_key_id: str) -> None:
        api_key = self.api_keys.get(api_key_id)
        if api_key is not None:
            api_key.revoked = True
