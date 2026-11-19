"""
WebSocket JWT Authentication Middleware for CampusOS LMS.
Validates JWT tokens passed in query params (?token=...) or Authorization headers.
"""

import urllib.parse
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from config.authentication import ExternalJWTAuthentication


class JwtAuthMiddleware:
    """
    Custom Channels ASGI middleware that authenticates WebSocket connections
    using CampusOS ExternalJWTAuthentication.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Only process websocket connections
        if scope["type"] == "websocket":
            token = self._extract_token(scope)
            if token:
                user = await self._authenticate_token(token)
                if user:
                    scope["user"] = user
                    scope["auth_error"] = None
                else:
                    scope["user"] = AnonymousUser()
                    scope["auth_error"] = "Invalid or expired token"
            else:
                scope["user"] = AnonymousUser()
                scope["auth_error"] = "Token missing"
        return await self.inner(scope, receive, send)

    def _extract_token(self, scope) -> str | None:
        """
        Extract JWT token from query string (?token=...) or headers.
        """
        # 1. Try query string: ?token=<jwt>
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            params = urllib.parse.parse_qs(query_string)
            tokens = params.get("token")
            if tokens and len(tokens) > 0:
                return tokens[0]

        # 2. Try Authorization header: Bearer <jwt>
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]

        # 3. Try Sec-WebSocket-Protocol header (e.g. ['Bearer', '<token>'])
        subprotocols = headers.get(b"sec-websocket-protocol", b"").decode("utf-8")
        if subprotocols:
            parts = [p.strip() for p in subprotocols.split(",")]
            for part in parts:
                if part.startswith("Bearer "):
                    return part.split(" ")[1]

        return None

    @database_sync_to_async
    def _authenticate_token(self, token: str):
        try:
            authenticator = ExternalJWTAuthentication()
            user, _ = authenticator.authenticate_token(token)
            return user
        except Exception:
            return None


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)

