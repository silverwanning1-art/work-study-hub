"""FastAPI entry point."""

import logging
import sys

from fastapi import FastAPI

from hub.config import Settings
from hub.registry import Registry, load_registry

settings = Settings()
logging.basicConfig(stream=sys.stdout, level=settings.log_level)

app = FastAPI(title="hub")
registry = load_registry(settings.plugins_dir, settings.agents_dir)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for proxy and container runtime."""
    return {"status": "ok"}


@app.get("/api/registry")
def get_registry() -> Registry:
    """List all plugins and agents the core loaded at startup."""
    return registry
