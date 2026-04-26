"""JWT middleware: validates bearer tokens on every request and populates request.state."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Paths that do NOT require a valid token
_PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class JWTMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that:
      1. Skips public paths entirely.
      2. On protected paths, extracts and validates the Bearer token.
      3. Populates ``request.state.user_payload`` on success.
      4. Returns 401 JSON if the token is missing or invalid.

    Routes decorated with ``@require_role(...)`` read from
    ``request.state.user_payload``; FastAPI dependencies that use
    ``Depends(get_current_user_payload)`` re-decode the token from the
    Authorization header so both patterns work correctly.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow public paths (and preflight OPTIONS)
        if path in _PUBLIC_PATHS or request.method == "OPTIONS":
            request.state.user_payload = None
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated — Bearer token required."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[len("Bearer "):]
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            if payload.get("type") != "access":
                raise ValueError("Not an access token")
        except (JWTError, ValueError):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Could not validate credentials."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.user_payload = payload
        return await call_next(request)
