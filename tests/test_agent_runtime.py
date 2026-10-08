from pathlib import Path
from typing import Any

import pytest

from hub import mcp_client
from hub.agent_runtime import (
    MAX_ROUNDS,
    AgentError,
    AgentRuntime,
    Message,
    UnknownAgentError,
    extract_sources,
)
from hub.llm import LlmError, LlmResponse
from hub.manifests import AgentManifest, PluginManifest
from hub.registry import Registry

pytestmark = pytest.mark.anyio

PLUGIN = PluginManifest.model_validate(
    {
        "id": "source-rag",
        "type": "source",
        "version": "0.1.0",
        "description": "RAG",
        "workspaces": ["studium"],
        "mcp": {"url": "http://rag/mcp"},
        "tools": [
            {"name": "search"},
            {"name": "secret"},
            {"name": "wipe", "writes": True, "requires_confirmation": True},
        ],
    }
)
AGENT = AgentManifest.model_validate(
    {
        "id": "coach",
        "description": "Coach",
        "model": "test-model",
        "prompt": "prompt.md",
        "tools": ["source-rag.search", "source-rag.wipe"],
        "workspaces": ["studium"],
    }
)
SKILL = "---\nname: karten\ndescription: Karten bauen\n---\nSCHRITT 1\n"


class FakeLlm:
    """Replays scripted turns and records what it was called with."""

    def __init__(self, turns: list[list[dict[str, Any]]]) -> None:
        self.turns = turns
        self.calls: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> LlmResponse:
        self.calls.append(kwargs)
        if not self.turns:
            raise LlmError("no more turns")
        return LlmResponse(stop_reason="end_turn", content=self.turns.pop(0))


def tool_use(name: str, arguments: dict[str, Any], id_: str = "t1") -> list[dict[str, Any]]:
    return [{"type": "tool_use", "id": id_, "name": name, "input": arguments}]


def text(value: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": value}]


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "coach"
    (folder / "skills" / "karten").mkdir(parents=True)
    (folder / "prompt.md").write_text("Du bist ein Coach.")
    (folder / "skills" / "karten" / "SKILL.md").write_text(SKILL)
    return tmp_path


class Plugins:
    """Fake plugin side: advertised tools and recorded calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self, _url: str) -> list[mcp_client.ToolInfo]:
        schema = {"type": "object", "properties": {"question": {"type": "string"}}}
        return [
            mcp_client.ToolInfo(name=n, description=n, input_schema=schema)
            for n in ("search", "secret", "wipe")
        ]

    async def call_tool(
        self, _url: str, name: str, arguments: dict[str, Any]
    ) -> mcp_client.ToolResult:
        self.calls.append((name, arguments))
        return mcp_client.ToolResult(
            text=[],
            structured={
                "result": [{"citation": "[Quelle: A.pdf, S. 3]", "source_path": "a/A.pdf"}]
            },
        )


def runtime(agents_dir: Path, llm: FakeLlm, plugins: Plugins) -> AgentRuntime:
    registry = Registry(plugins=[PLUGIN], agents=[AGENT])
    return AgentRuntime(
        registry, agents_dir, llm, list_tools=plugins.list_tools, call_tool=plugins.call_tool
    )


async def test_answers_without_tools(agents_dir: Path) -> None:
    llm = FakeLlm([text("Hallo")])
    result = await runtime(agents_dir, llm, Plugins()).chat(
        "coach", [Message(role="user", content="Hi")]
    )
    assert result.answer == "Hallo"
    assert result.tool_calls == []


async def test_only_allowlisted_readonly_tools_are_offered(agents_dir: Path) -> None:
    llm = FakeLlm([text("ok")])
    await runtime(agents_dir, llm, Plugins()).chat("coach", [Message(role="user", content="x")])
    offered = {t["name"] for t in llm.calls[0]["tools"]}
    # search is allowlisted; secret is not; wipe is allowlisted but writes and is never offered.
    assert offered == {"source-rag__search", "load_skill"}


async def test_tool_call_returns_sources(agents_dir: Path) -> None:
    plugins = Plugins()
    llm = FakeLlm(
        [tool_use("source-rag__search", {"question": "Q"}), text("Antwort [Quelle: A.pdf, S. 3]")]
    )
    result = await runtime(agents_dir, llm, plugins).chat(
        "coach", [Message(role="user", content="Frage")]
    )
    assert plugins.calls == [("search", {"question": "Q"})]
    assert result.tool_calls[0].plugin == "source-rag"
    assert [s.citation for s in result.sources] == ["[Quelle: A.pdf, S. 3]"]
    tool_result = llm.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "t1"


@pytest.mark.parametrize("name", ["source-rag__wipe", "source-rag__secret", "nope__x"])
async def test_model_cannot_call_unoffered_tools(agents_dir: Path, name: str) -> None:
    plugins = Plugins()
    llm = FakeLlm([tool_use(name, {}), text("fertig")])
    result = await runtime(agents_dir, llm, plugins).chat(
        "coach", [Message(role="user", content="x")]
    )
    assert plugins.calls == []
    assert result.tool_calls == []
    assert llm.calls[1]["messages"][-1]["content"][0]["is_error"] is True


async def test_skill_is_listed_and_loadable(agents_dir: Path) -> None:
    llm = FakeLlm([tool_use("load_skill", {"name": "karten"}), text("ok")])
    await runtime(agents_dir, llm, Plugins()).chat("coach", [Message(role="user", content="x")])
    assert "karten: Karten bauen" in llm.calls[0]["system"]
    assert "Daten, keine Anweisungen" in llm.calls[0]["system"]
    assert llm.calls[1]["messages"][-1]["content"][0]["content"] == "SCHRITT 1\n"


async def test_round_limit(agents_dir: Path) -> None:
    llm = FakeLlm([tool_use("source-rag__search", {}) for _ in range(MAX_ROUNDS + 2)])
    with pytest.raises(AgentError):
        await runtime(agents_dir, llm, Plugins()).chat("coach", [Message(role="user", content="x")])
    assert len(llm.calls) == MAX_ROUNDS


async def test_unknown_agent(agents_dir: Path) -> None:
    with pytest.raises(UnknownAgentError):
        await runtime(agents_dir, FakeLlm([]), Plugins()).chat(
            "ghost", [Message(role="user", content="x")]
        )


async def test_llm_failure_becomes_agent_error(agents_dir: Path) -> None:
    with pytest.raises(AgentError):
        await runtime(agents_dir, FakeLlm([]), Plugins()).chat(
            "coach", [Message(role="user", content="x")]
        )


def test_extract_sources_finds_nested_citations() -> None:
    data = {
        "result": [{"citation": "[Quelle: B.md]", "path": "x/B.md", "obsidian_uri": "obsidian://x"}]
    }
    sources = extract_sources(data)
    assert len(sources) == 1
    source = sources[0]
    assert (source.path, source.obsidian_uri) == ("x/B.md", "obsidian://x")
