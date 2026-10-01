"""Thin client for calling tools on plugin MCP servers (Streamable HTTP)."""

import asyncio
import logging
from typing import Any

from mcp import Client, MCPError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10.0


class PluginUnavailableError(Exception):
    """The plugin's MCP server could not be reached or answered with an error."""


class ToolInfo(BaseModel):
    """A tool as advertised by the plugin's MCP server."""

    name: str
    description: str | None = None


class ToolResult(BaseModel):
    """Result of a tool call, reduced to what the UI needs."""

    text: list[str]
    structured: dict[str, Any] | None = None
    is_error: bool = False


async def list_tools(url: str) -> list[ToolInfo]:
    """Return the tools the MCP server at ``url`` advertises."""
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS), Client(url) as client:
            result = await client.list_tools()
    except (OSError, TimeoutError, MCPError) as exc:
        logger.error("Listing tools at %s failed: %s", url, exc)
        raise PluginUnavailableError from exc
    return [ToolInfo(name=t.name, description=t.description) for t in result.tools]


async def call_tool(url: str, name: str, arguments: dict[str, Any]) -> ToolResult:
    """Call tool ``name`` on the MCP server at ``url``."""
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS), Client(url) as client:
            result = await client.call_tool(name, arguments)
    except (OSError, TimeoutError, MCPError) as exc:
        logger.error("Calling tool %s at %s failed: %s", name, url, exc)
        raise PluginUnavailableError from exc
    text = [block.text for block in result.content if block.type == "text"]
    return ToolResult(text=text, structured=result.structured_content, is_error=result.is_error)
