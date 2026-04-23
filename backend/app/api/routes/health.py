"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "Smart DevOps Assistant"}


@router.get("/", tags=["Health"])
async def root():
    return {
        "name": "Agentic AI-Powered Smart DevOps Assistant",
        "version": "1.0.0",
        "docs": "/docs",
    }
