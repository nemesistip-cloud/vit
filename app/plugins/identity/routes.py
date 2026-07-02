from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from app.db.database import get_db
from app.plugins.identity.services.identity_manager import IdentityManager
from app.plugins.identity.services.authentication_manager import AuthenticationManager
from app.plugins.identity.services.session_manager import SessionManager
from app.plugins.identity.services.password_service import PasswordService
from app.plugins.identity.services.token_manager import TokenManager
from app.plugins.identity.services.mfa_service import MFAService
from app.core.plugins.host import extension_host
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    identifier: str
    password: str
    device_id: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: str

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # In a real plugin, these would be retrieved from the plugin instance via extension_host
    # but for simplicity in this implementation we instantiate them.
    from app.plugins.identity.plugin import IdentityPlugin
    plugin = IdentityPlugin() # Should be singleton

    im = IdentityManager(db)
    sm = SessionManager(db)
    am = AuthenticationManager(db, im, plugin.password_service, plugin.token_manager, sm, plugin.mfa_service)

    success, identity, message = await am.authenticate_password(req.identifier, req.password, {})

    if not success:
        raise HTTPException(status_code=401, detail=message)

    session = await sm.create_session(identity, device_id=req.device_id)
    access_token = plugin.token_manager.create_access_token(identity.gid)

    return {
        "access_token": access_token,
        "session_token": session.session_token,
        "gid": identity.gid,
        "type": identity.type
    }

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from app.plugins.identity.plugin import IdentityPlugin
    plugin = IdentityPlugin()

    im = IdentityManager(db)

    # Validate password
    valid, msg = plugin.password_service.validate_password_policy(req.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # Create identity
    identity = await im.create_identity(
        type="individual",
        username=req.username,
        email=req.email,
        display_name=req.display_name
    )

    # Store password
    updates = {
        "security_metadata": {
            "password_hash": plugin.password_service.hash_password(req.password)
        }
    }
    await im.update_identity(identity.gid, updates)

    return {"gid": identity.gid, "status": "active"}

@router.get("/me")
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    # Session validation would happen in middleware
    return {"gid": "VIT-ID-MOCK", "status": "active"}
