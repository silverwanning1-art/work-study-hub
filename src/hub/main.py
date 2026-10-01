"""FastAPI entry point."""

import logging
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from hub import mcp_client
from hub.config import Settings
from hub.manifests import PluginManifest
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


class ToolCallRequest(BaseModel):
    """Body of a tool call request."""

    arguments: dict[str, Any] = {}


def _plugin_or_404(plugin_id: str) -> PluginManifest:
    plugin = registry.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Unknown plugin")
    return plugin


@app.get("/api/plugins/{plugin_id}/tools")
async def list_plugin_tools(plugin_id: str) -> list[mcp_client.ToolInfo]:
    """List the tools a plugin's MCP server advertises."""
    plugin = _plugin_or_404(plugin_id)
    try:
        return await mcp_client.list_tools(plugin.mcp.url)
    except mcp_client.PluginUnavailableError:
        raise HTTPException(status_code=502, detail="Plugin unavailable") from None


@app.post("/api/plugins/{plugin_id}/tools/{tool_name}/call")
async def call_plugin_tool(
    plugin_id: str, tool_name: str, body: ToolCallRequest
) -> mcp_client.ToolResult:
    """Call a tool declared in the plugin's manifest.

    Writing tools are refused until the confirmation flow exists (later phase).
    """
    plugin = _plugin_or_404(plugin_id)
    spec = next((t for t in plugin.tools if t.name == tool_name), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown tool")
    if spec.writes:
        raise HTTPException(status_code=403, detail="Writing tools are not callable yet")
    try:
        return await mcp_client.call_tool(plugin.mcp.url, tool_name, body.arguments)
    except mcp_client.PluginUnavailableError:
        raise HTTPException(status_code=502, detail="Plugin unavailable") from None
