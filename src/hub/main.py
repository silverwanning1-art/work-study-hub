"""FastAPI entry point."""

import base64
import binascii
import logging
import re
import sys
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from hub import mcp_client
from hub.agent_runtime import AgentError, AgentRuntime, ChatResult, Message, UnknownAgentError
from hub.config import Settings
from hub.confirmations import ConfirmationError, ConfirmationStore, TooManyPendingError
from hub.llm import AnthropicLlm
from hub.manifests import PluginManifest
from hub.registry import Registry, load_registry

settings = Settings()
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=settings.log_level)

app = FastAPI(title="hub")
registry = load_registry(settings.plugins_dir, settings.agents_dir)
confirmations = ConfirmationStore()


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


async def _execute(
    plugin: PluginManifest, tool_name: str, arguments: dict[str, Any]
) -> mcp_client.ToolResult:
    try:
        return await mcp_client.call_tool(plugin.mcp.url, tool_name, arguments)
    except mcp_client.PluginUnavailableError:
        raise HTTPException(status_code=502, detail="Plugin unavailable") from None


@app.post("/api/plugins/{plugin_id}/tools/{tool_name}/call", response_model=None)
async def call_plugin_tool(
    plugin_id: str, tool_name: str, body: ToolCallRequest
) -> mcp_client.ToolResult | JSONResponse:
    """Call a tool declared in the plugin's manifest.

    Reading tools run immediately. Writing tools are not executed: the response is
    ``202`` with a ``confirmation_id`` that must be sent to ``/api/confirmations/{id}/confirm``.
    """
    plugin = _plugin_or_404(plugin_id)
    spec = next((t for t in plugin.tools if t.name == tool_name), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown tool")
    if not spec.writes:
        return await _execute(plugin, tool_name, body.arguments)
    try:
        pending = confirmations.create(plugin_id, tool_name, body.arguments)
    except TooManyPendingError:
        raise HTTPException(status_code=429, detail="Too many pending confirmations") from None
    return JSONResponse(
        status_code=202,
        content={
            "confirmation_id": pending.id,
            "plugin_id": pending.plugin_id,
            "tool": pending.tool,
        },
    )


@app.post("/api/confirmations/{confirmation_id}/confirm")
async def confirm_tool_call(confirmation_id: str) -> mcp_client.ToolResult:
    """Execute a previously requested writing tool call. Each id works once."""
    try:
        pending = confirmations.consume(confirmation_id)
    except ConfirmationError:
        raise HTTPException(status_code=404, detail="Unknown or expired confirmation") from None
    plugin = _plugin_or_404(pending.plugin_id)
    return await _execute(plugin, pending.tool, pending.arguments)


class ChatRequest(BaseModel):
    """Body of an agent chat request; the UI sends the whole conversation."""

    messages: list[Message] = Field(min_length=1, max_length=40)


_runtime: AgentRuntime | None = None


def get_runtime() -> AgentRuntime:
    """Build the agent runtime once; fails with 503 while no API key is configured."""
    global _runtime  # noqa: PLW0603 - lazily created singleton
    if _runtime is None:
        if settings.anthropic_api_key is None or not settings.anthropic_api_key.get_secret_value():
            raise HTTPException(status_code=503, detail="Language model is not configured")
        _runtime = AgentRuntime(
            registry, settings.agents_dir, AnthropicLlm(settings.anthropic_api_key)
        )
    return _runtime


@app.post("/api/agents/{agent_id}/chat")
async def chat_with_agent(
    agent_id: str,
    body: ChatRequest,
    runtime: AgentRuntime = Depends(get_runtime),  # noqa: B008
) -> ChatResult:
    """Run an agent on a conversation. The last message must come from the user."""
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must be from the user")
    try:
        return await runtime.chat(agent_id, body.messages)
    except UnknownAgentError:
        raise HTTPException(status_code=404, detail="Unknown agent") from None
    except AgentError as exc:
        logger.error("Agent %s failed: %s", agent_id, exc)
        raise HTTPException(status_code=502, detail="The agent could not answer") from None


INVOICE_PLUGIN_ID = "action-invoice"


@app.get("/api/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(invoice_id: int) -> Response:
    """Download the PDF of an issued invoice (decoded from the plugin's base64 result)."""
    plugin = _plugin_or_404(INVOICE_PLUGIN_ID)
    result = await _execute(plugin, "get_invoice_pdf", {"invoice_id": invoice_id})
    data = result.structured or {}
    try:
        content = base64.b64decode(str(data.get("content_base64", "")), validate=True)
    except binascii.Error:
        content = b""
    if result.is_error or not content:
        raise HTTPException(status_code=404, detail="PDF not available")
    # The plugin controls the name; keep only safe characters for the header.
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", str(data.get("filename", "invoice.pdf")))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
