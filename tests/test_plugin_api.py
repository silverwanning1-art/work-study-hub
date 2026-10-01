from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.server.mcpserver import MCPServer

from hub import main, mcp_client
from hub.manifests import PluginManifest
from hub.registry import Registry

MANIFEST = {
    "id": "source-hello",
    "type": "source",
    "version": "0.1.0",
    "description": "Example",
    "workspaces": ["global"],
    "mcp": {"url": "http://source-hello:8000/mcp"},
    "tools": [
        {"name": "hello"},
        {"name": "write_thing", "writes": True, "requires_confirmation": True},
    ],
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    server = MCPServer("hello")

    @server.tool()
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    # Route the client to the in-process server so no network is needed.
    monkeypatch.setattr(mcp_client, "Client", lambda _url: Client(server))
    monkeypatch.setattr(
        main, "registry", Registry(plugins=[PluginManifest.model_validate(MANIFEST)])
    )
    yield TestClient(main.app)


def test_list_tools(client: TestClient) -> None:
    response = client.get("/api/plugins/source-hello/tools")

    assert response.status_code == 200
    assert [t["name"] for t in response.json()] == ["hello"]


def test_call_tool(client: TestClient) -> None:
    response = client.post(
        "/api/plugins/source-hello/tools/hello/call", json={"arguments": {"name": "Test"}}
    )

    assert response.status_code == 200
    assert response.json()["text"] == ["Hello, Test!"]


def test_unknown_plugin_and_tool(client: TestClient) -> None:
    assert client.get("/api/plugins/nope/tools").status_code == 404
    assert client.post("/api/plugins/source-hello/tools/nope/call", json={}).status_code == 404


def test_writing_tool_is_refused(client: TestClient) -> None:
    response = client.post("/api/plugins/source-hello/tools/write_thing/call", json={})

    assert response.status_code == 403


def test_unreachable_plugin_gives_generic_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_url: str) -> Any:
        raise OSError("connect failed: internal-host:8000")

    monkeypatch.setattr(mcp_client, "Client", broken)

    response = client.get("/api/plugins/source-hello/tools")

    assert response.status_code == 502
    assert response.json() == {"detail": "Plugin unavailable"}
