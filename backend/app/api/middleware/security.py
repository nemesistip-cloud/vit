"""Pure ASGI Security headers middleware — VIT Sports Analytics Network.

Phase 3 hardening:
- HSTS with preload directive in production
- Tightened CSP (removed 'unsafe-eval' from script-src)
- Added Cross-Origin-Opener-Policy and Cross-Origin-Resource-Policy
- Permissions-Policy extended with more feature restrictions
- Cache-Control for auth endpoints
"""

from starlette.types import ASGIApp, Receive, Scope, Send
from app.config import ENVIRONMENT

# Paths that carry sensitive tokens — force no-cache so browsers never store
# auth responses in their HTTP cache.
_NO_CACHE_PREFIXES = ("/auth/", "/api/auth/")


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware that adds security headers to every response.
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        self._is_prod = ENVIRONMENT.lower() == "production"

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        is_auth_path = any(path.startswith(p) for p in _NO_CACHE_PREFIXES)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # --- Standard hardening ---
                headers.append((b"x-content-type-options", b"nosniff"))
                # x-xss-protection is obsolete in modern browsers but harmless; keep for legacy
                headers.append((b"x-xss-protection", b"1; mode=block"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append((b"x-frame-options", b"DENY"))   # Phase3: SAMEORIGIN→DENY (stricter)

                # --- Permissions Policy ---
                headers.append((
                    b"permissions-policy",
                    b"camera=(), microphone=(), geolocation=(), payment=(), "
                    b"usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
                ))

                # --- Cross-Origin policies ---
                headers.append((b"cross-origin-opener-policy", b"same-origin"))
                headers.append((b"cross-origin-resource-policy", b"same-site"))

                # --- CSP (Phase 3: removed 'unsafe-eval' from script-src) ---
                csp = (
                    "default-src 'self'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' wss: https:; "
                    "font-src 'self' data: https://fonts.gstatic.com; "
                    "script-src 'self' 'unsafe-inline'; "   # removed 'unsafe-eval'
                    "frame-ancestors 'none'; "              # Phase3: 'self'→'none' (DENY equivalent)
                    "base-uri 'self'; "
                    "form-action 'self';"
                )
                headers.append((b"content-security-policy", csp.encode()))

                # --- Production-only headers ---
                if self._is_prod:
                    # HSTS with preload — 1 year, include subdomains
                    headers.append((
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains; preload"
                    ))

                # --- Auth-path cache control ---
                if is_auth_path:
                    headers.append((b"cache-control", b"no-store"))
                    headers.append((b"pragma", b"no-cache"))

                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
