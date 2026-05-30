"""Pure ASGI Security headers middleware — VIT Sports Intelligence Network."""

from starlette.types import ASGIApp, Receive, Scope, Send
from app.config import ENVIRONMENT

class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware that adds security headers to every response.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add security headers
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"x-xss-protection", b"1; mode=block"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append((b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"))

                csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.puter.com; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' wss: https:; "
                    "font-src 'self' data: https://fonts.gstatic.com; "
                    "frame-src https://js.puter.com; "
                    "frame-ancestors 'none';"
                )
                headers.append((b"content-security-policy", csp.encode()))

                if ENVIRONMENT.lower() == "production":
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))

                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
