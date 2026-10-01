from typing import Any

import pytest
from pydantic import ValidationError

from hub.manifests import AgentManifest, PluginManifest


def plugin_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "source-hello",
        "type": "source",
        "version": "0.1.0",
        "description": "Example plugin",
        "workspaces": ["global"],
        "mcp": {"url": "http://source-hello:8000/mcp"},
        "tools": [{"name": "hello"}],
    }
    return data | overrides


def agent_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "friday",
        "description": "Everyday assistant",
        "model": "example-model",
        "prompt": "prompt.md",
        "tools": ["source-hello.*"],
        "channels": ["web"],
        "workspaces": ["global"],
    }
    return data | overrides


def test_valid_plugin_manifest() -> None:
    manifest = PluginManifest.model_validate(plugin_data())

    assert manifest.id == "source-hello"
    assert manifest.tools[0].writes is False


def test_writing_tool_requires_confirmation() -> None:
    tools = [{"name": "issue_invoice", "writes": True}]

    with pytest.raises(ValidationError, match="requires_confirmation"):
        PluginManifest.model_validate(plugin_data(tools=tools))


def test_writing_tool_with_confirmation_is_valid() -> None:
    tools = [{"name": "issue_invoice", "writes": True, "requires_confirmation": True}]

    assert PluginManifest.model_validate(plugin_data(tools=tools)).tools[0].writes


def test_duplicate_tool_names_rejected() -> None:
    with pytest.raises(ValidationError, match="unique"):
        PluginManifest.model_validate(plugin_data(tools=[{"name": "a"}, {"name": "a"}]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "Bad Id"},
        {"type": "unknown"},
        {"version": "1.0"},
        {"workspaces": []},
        {"mcp": {"url": "ftp://example"}},
        {"unexpected": 1},
    ],
)
def test_invalid_plugin_manifest(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(plugin_data(**overrides))


def test_valid_agent_manifest() -> None:
    assert AgentManifest.model_validate(agent_data()).id == "friday"


@pytest.mark.parametrize("prompt", ["../secrets.md", "dir/prompt.md", ""])
def test_agent_prompt_must_be_plain_filename(prompt: str) -> None:
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(agent_data(prompt=prompt))
