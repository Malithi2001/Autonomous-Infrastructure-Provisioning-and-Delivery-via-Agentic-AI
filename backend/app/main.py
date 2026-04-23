"""
Smart DevOps Assistant - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import agent, auth, approvals, executions, health, webhooks
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    await init_db()
    yield
    # Shutdown (cleanup tasks if needed)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Agentic AI-Powered Smart DevOps Assistant — "
        "autonomous infrastructure management through natural language."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["HITL Approvals"])
app.include_router(executions.router, prefix="/api/v1/executions", tags=["Executions"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
