"""Pydantic schemas for plugin and agent manifests (``plugin.yaml``, ``agent.yaml``)."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Lowercase slug, used as identifier and in URLs and tool allowlists.
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")]


class PluginType(StrEnum):
    """Kinds of plugins the core knows about."""

    SOURCE = "source"
    ACTION = "action"
    AGENT = "agent"
    CHANNEL = "channel"


class Workspace(StrEnum):
    """Workspaces a plugin or agent is visible in."""

    STUDIUM = "studium"
    ARBEIT = "arbeit"
    GLOBAL = "global"


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolSpec(_Manifest):
    """A tool exposed by a plugin's MCP server."""

    name: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    writes: bool = False
    requires_confirmation: bool = False

    @model_validator(mode="after")
    def _writes_need_confirmation(self) -> Self:
        if self.writes and not self.requires_confirmation:
            raise ValueError(f"tool '{self.name}' writes and must set requires_confirmation")
        return self


class McpEndpoint(_Manifest):
    """Where the plugin's MCP server (Streamable HTTP) can be reached."""

    url: Annotated[str, Field(pattern=r"^https?://")]


class PluginManifest(_Manifest):
    """Manifest of a source, action or channel plugin."""

    id: Identifier
    type: PluginType
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    description: Annotated[str, Field(min_length=1, max_length=300)]
    workspaces: Annotated[list[Workspace], Field(min_length=1)]
    mcp: McpEndpoint
    tools: list[ToolSpec] = []
    secrets: list[str] = []

    @model_validator(mode="after")
    def _unique_tools(self) -> Self:
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("tool names must be unique")
        return self


class AgentManifest(_Manifest):
    """Manifest of an agent: prompt, model, tool allowlist and channels."""

    id: Identifier
    description: Annotated[str, Field(min_length=1, max_length=300)]
    model: Annotated[str, Field(min_length=1)]
    prompt: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+$")]
    tools: list[str] = []
    channels: list[str] = []
    workspaces: Annotated[list[Workspace], Field(min_length=1)]
