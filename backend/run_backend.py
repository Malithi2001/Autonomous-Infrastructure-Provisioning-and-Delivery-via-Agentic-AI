"""Local/packaged backend entry point for desktop mode."""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("DISABLE_AUTH", "true")
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8000")
    os.environ.setdefault("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
