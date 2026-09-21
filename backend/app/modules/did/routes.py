"""VIT DID API routes — Module DID.

Route order matters: specific routes MUST precede the /{did:path} catch-all.

Endpoints:
  POST /api/did/user/register           — self-register user DID
  GET  /api/did/registry                — list all active DIDs (admin)
  POST /api/did/credentials/issue       — admin: issue a VC
  GET  /api/did/credentials/{id}        — list active VCs for an identity
  GET  /api/did/user/{user_id}          — get or create user DID
  GET  /api/did/agent/{agent_name}      — resolve agent DID
  GET  /api/did/{did}                   — resolve any DID document
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.modules.did.engine import (
    get_active_credentials,
    get_or_create_agent_identity,
    get_or_create_user_identity,
    issue_credential,
    list_all_identities,
    resolve_did,
)
from app.modules.did.models import VITIdentity, VerifiableCredential

router = APIRouter(prefix="/api/did", tags=["VIT DID"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ────────────────────────────────────────────────────────

class IssueCredentialRequest(BaseModel):
    identity_id: str
    credential_type: str
    claims: dict
    valid_days: Optional[int] = None


class SelfRegisterRequest(BaseModel):
    display_name: Optional[str] = None


# ── Specific routes BEFORE the catch-all /{did:path} ────────────────────────

@router.post("/user/register")
async def register_user_did(
    body: SelfRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create or retrieve the caller's DID document."""
    label = body.display_name or current_user.email.split("@")[0]
    identity = await get_or_create_user_identity(current_user.id, label, db)
    await db.commit()
    return {
        "did": identity.did,
        "document": identity.did_document,
        "created_at": identity.created_at.isoformat(),
    }


@router.get("/registry")
async def list_registry(
    subject_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: list all registered DIDs."""
    identities = await list_all_identities(subject_type, limit, offset, db)
    result = []
    for identity in identities:
        vcs = await get_active_credentials(identity.id, db)
        result.append({
            "did": identity.did,
            "id": identity.id,
            "subject_type": identity.subject_type,
            "agent_name": identity.agent_name,
            "user_id": identity.user_id,
            "credential_count": len(vcs),
            "credential_types": [vc.credential_type for vc in vcs],
            "created_at": identity.created_at.isoformat(),
        })
    return {"identities": result, "count": len(result)}


@router.post("/credentials/issue")
async def issue_vc(
    body: IssueCredentialRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: issue a Verifiable Credential to an identity."""
    try:
        vc = await issue_credential(
            body.identity_id,
            body.credential_type,
            body.claims,
            db,
            body.valid_days,
        )
        await db.commit()
        return {"status": "issued", "credential_id": vc.id, "vc": _vc_detail(vc)}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/credentials/{identity_id}")
async def list_credentials(
    identity_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: list all active VCs for an identity."""
    vcs = await get_active_credentials(identity_id, db)
    return {"credentials": [_vc_detail(vc) for vc in vcs], "count": len(vcs)}


@router.get("/user/{user_id}")
async def get_user_did(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: resolve or create a user DID."""
    from app.db.models import User
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    label = user.email.split("@")[0]
    identity = await get_or_create_user_identity(user_id, label, db)
    await db.commit()
    vcs = await get_active_credentials(identity.id, db)
    return {
        "did": identity.did,
        "document": identity.did_document,
        "credentials": [_vc_summary(vc) for vc in vcs],
        "created_at": identity.created_at.isoformat(),
    }


@router.get("/agent/{agent_name}")
async def get_agent_did(agent_name: str, db: AsyncSession = Depends(get_db)):
    """Public: resolve agent node DID."""
    identity = await get_or_create_agent_identity(agent_name, db)
    await db.commit()
    vcs = await get_active_credentials(identity.id, db)
    return {
        "did": identity.did,
        "document": identity.did_document,
        "credentials": [_vc_summary(vc) for vc in vcs],
        "created_at": identity.created_at.isoformat(),
    }


# ── Root summary (fixes 307 redirect on GET /api/did) ───────────────────────

@router.get("")
async def did_root():
    """Summary of available DID endpoints."""
    return {
        "module": "VIT DID — Decentralised Identity",
        "endpoints": {
            "POST /api/did/user/register":        "Self-register caller's DID",
            "GET  /api/did/registry":             "Admin: list all registered DIDs",
            "POST /api/did/credentials/issue":    "Admin: issue a Verifiable Credential",
            "GET  /api/did/credentials/{id}":     "Admin: list VCs for an identity",
            "GET  /api/did/user/{user_id}":       "Admin: resolve or create user DID",
            "GET  /api/did/agent/{agent_name}":   "Public: resolve agent DID",
            "GET  /api/did/{did}":                "Public: resolve any did:vit: document",
        },
    }


# ── Catch-all MUST come LAST ─────────────────────────────────────────────────

@router.get("/{did:path}")
async def resolve_did_endpoint(did: str, db: AsyncSession = Depends(get_db)):
    """Public: resolve any VIT DID to its document."""
    if not did.startswith("did:vit:"):
        raise HTTPException(400, "Only did:vit: namespace is supported")
    identity = await resolve_did(did, db)
    if not identity:
        raise HTTPException(404, f"DID not found: {did}")
    vcs = await get_active_credentials(identity.id, db)
    return {
        "did": identity.did,
        "document": identity.did_document,
        "credentials": [_vc_summary(vc) for vc in vcs],
        "subject_type": identity.subject_type,
        "active": identity.active,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _vc_summary(vc: VerifiableCredential) -> dict:
    return {
        "id": vc.id,
        "type": vc.credential_type,
        "issuer": vc.issuer,
        "issued_at": vc.issued_at.isoformat(),
        "expires_at": vc.expires_at.isoformat() if vc.expires_at else None,
        "revoked": vc.revoked,
    }


def _vc_detail(vc: VerifiableCredential) -> dict:
    return {
        **_vc_summary(vc),
        "credential": vc.credential,
    }
