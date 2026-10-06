import hashlib
import logging
import uuid
from typing import Optional, Tuple
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import User
from app.plugins.identity.models import TrustedDevice, GlobalIdentity, IdentityStatus, IdentityType
from app.plugins.identity.services.device_trust_manager import DeviceTrustManager

logger = logging.getLogger(__name__)


def parse_user_agent(user_agent: Optional[str]) -> Tuple[str, str]:
    """Parse platform and browser from a User-Agent header string."""
    if not user_agent:
        return "Unknown Platform", "Unknown Browser"

    ua = user_agent.lower()

    # Platform detection
    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        platform = "iOS"
    elif "android" in ua:
        platform = "Android"
    elif "macintosh" in ua or "mac os" in ua:
        platform = "macOS"
    elif "windows" in ua:
        platform = "Windows"
    elif "linux" in ua:
        platform = "Linux"
    else:
        platform = "Web Device"

    # Browser detection
    if "edg" in ua or "edge" in ua:
        browser = "Microsoft Edge"
    elif "opr" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome" in ua or "crios" in ua:
        browser = "Chrome"
    elif "firefox" in ua or "fxios" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua and "crios" not in ua:
        browser = "Safari"
    else:
        browser = "Unknown Browser"

    return platform, browser


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """Extract client IP address from request headers or connection client."""
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


async def get_or_create_global_identity(db: AsyncSession, user: User) -> Optional[GlobalIdentity]:
    """Fetch the GlobalIdentity for this user, creating one if absent."""
    if not user or not user.email:
        return None
    try:
        result = await db.execute(
            select(GlobalIdentity).where(GlobalIdentity.email == user.email)
        )
        identity = result.scalar_one_or_none()
        if not identity:
            def _gid():
                raw = uuid.uuid4().hex.upper()
                return f"VIT-ID-{raw[:4]}-{raw[4:8]}"

            identity = GlobalIdentity(
                gid=_gid(),
                type=IdentityType.ADMIN if getattr(user, "role", "") == "admin" else IdentityType.INDIVIDUAL,
                status=IdentityStatus.ACTIVE,
                username=user.username,
                email=user.email,
                auth_methods=["password"],
                security_metadata={},
                profile={},
            )
            db.add(identity)
            await db.commit()
            await db.refresh(identity)
        return identity
    except Exception as exc:
        logger.error("get_or_create_global_identity failed: %s", exc)
        return None


async def register_device_for_request(
    db: AsyncSession,
    identity: GlobalIdentity,
    request: Optional[Request],
    explicit_device_id: Optional[str] = None,
) -> Optional[TrustedDevice]:
    """Auto-register or update a device for a given identity from a FastAPI Request."""
    if not identity:
        return None

    try:
        user_agent = request.headers.get("user-agent", "") if request else ""
        ip_address = get_client_ip(request)

        device_id = (
            explicit_device_id
            or (request.headers.get("x-device-id") if request else None)
            or (request.headers.get("device-id") if request else None)
        )

        if not device_id:
            raw_fingerprint = f"{identity.id}:{user_agent or 'unknown'}"
            digest = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()[:16]
            device_id = f"dev_{digest}"

        platform, browser = parse_user_agent(user_agent)

        mgr = DeviceTrustManager(db)
        device = await mgr.register_device(
            identity=identity,
            device_id=device_id,
            platform=platform,
            browser=browser,
            ip_address=ip_address,
        )
        return device
    except Exception as exc:
        logger.error("register_device_for_request failed: %s", exc)
        return None


async def register_device_for_user(
    db: AsyncSession,
    user: User,
    request: Optional[Request],
    explicit_device_id: Optional[str] = None,
) -> Optional[TrustedDevice]:
    """Helper to resolve GlobalIdentity and auto-register device for a User model."""
    identity = await get_or_create_global_identity(db, user)
    if not identity:
        return None
    return await register_device_for_request(db, identity, request, explicit_device_id)
