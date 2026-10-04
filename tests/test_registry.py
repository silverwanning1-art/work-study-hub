from pathlib import Path

import pytest

from hub.registry import load_registry

PLUGIN_YAML = """
id: {id}
type: source
version: 0.1.0
description: Example
workspaces: [global]
mcp:
  url: http://example:8000/mcp
tools:
  - name: hello
"""

AGENT_YAML = """
id: {id}
description: Example agent
model: example-model
prompt: prompt.md
tools: ["source-hello.*"]
channels: [web]
workspaces: [global]
"""


def write(base: Path, folder: str, filename: str, content: str) -> None:
    (base / folder).mkdir(parents=True)
    (base / folder / filename).write_text(content, encoding="utf-8")


def test_missing_directories_give_empty_registry(tmp_path: Path) -> None:
    registry = load_registry(tmp_path / "plugins", tmp_path / "agents")

    assert registry.plugins == []
    assert registry.agents == []


def test_loads_plugin_and_agent(tmp_path: Path) -> None:
    write(
        tmp_path / "plugins", "source-hello", "plugin.yaml", PLUGIN_YAML.format(id="source-hello")
    )
    write(tmp_path / "agents", "friday", "agent.yaml", AGENT_YAML.format(id="friday"))
    (tmp_path / "agents" / "friday" / "prompt.md").write_text("Hi", encoding="utf-8")

    registry = load_registry(tmp_path / "plugins", tmp_path / "agents")

    assert [p.id for p in registry.plugins] == ["source-hello"]
    assert [a.id for a in registry.agents] == ["friday"]
    assert registry.get_plugin("source-hello") is not None
    assert registry.get_plugin("nope") is None


def test_invalid_manifest_is_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    write(tmp_path / "plugins", "good", "plugin.yaml", PLUGIN_YAML.format(id="good"))
    write(tmp_path / "plugins", "broken", "plugin.yaml", "id: [unclosed")
    write(tmp_path / "plugins", "mismatch", "plugin.yaml", PLUGIN_YAML.format(id="other"))

    registry = load_registry(tmp_path / "plugins", tmp_path / "agents")

    assert [p.id for p in registry.plugins] == ["good"]
    assert "Skipping invalid manifest" in caplog.text


def test_agent_without_prompt_file_is_skipped(tmp_path: Path) -> None:
    write(tmp_path / "agents", "friday", "agent.yaml", AGENT_YAML.format(id="friday"))

    assert load_registry(tmp_path / "plugins", tmp_path / "agents").agents == []
