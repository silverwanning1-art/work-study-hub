"""FastAPI entry point."""

import logging
import sys

from fastapi import FastAPI

from hub.config import Settings

settings = Settings()
logging.basicConfig(stream=sys.stdout, level=settings.log_level)

app = FastAPI(title="hub")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for proxy and container runtime."""
    return {"status": "ok"}
