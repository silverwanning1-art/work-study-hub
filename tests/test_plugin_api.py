from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.server.mcpserver import MCPServer

from hub import main, mcp_client
from hub.confirmations import ConfirmationStore
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

    @server.tool()
    def write_thing(value: str) -> str:
        return f"wrote {value}"

    # Route the client to the in-process server so no network is needed.
    monkeypatch.setattr(mcp_client, "Client", lambda _url: Client(server))
    monkeypatch.setattr(
        main, "registry", Registry(plugins=[PluginManifest.model_validate(MANIFEST)])
    )
    monkeypatch.setattr(main, "confirmations", ConfirmationStore())
    yield TestClient(main.app)


def test_list_tools(client: TestClient) -> None:
    response = client.get("/api/plugins/source-hello/tools")

    assert response.status_code == 200
    assert {t["name"] for t in response.json()} == {"hello", "write_thing"}


def test_call_tool(client: TestClient) -> None:
    response = client.post(
        "/api/plugins/source-hello/tools/hello/call", json={"arguments": {"name": "Test"}}
    )

    assert response.status_code == 200
    assert response.json()["text"] == ["Hello, Test!"]


def test_unknown_plugin_and_tool(client: TestClient) -> None:
    assert client.get("/api/plugins/nope/tools").status_code == 404
    assert client.post("/api/plugins/source-hello/tools/nope/call", json={}).status_code == 404


def request_write(client: TestClient, value: str = "x") -> str:
    response = client.post(
        "/api/plugins/source-hello/tools/write_thing/call", json={"arguments": {"value": value}}
    )
    assert response.status_code == 202
    return str(response.json()["confirmation_id"])


def test_writing_tool_is_not_executed_before_confirmation(client: TestClient) -> None:
    response = client.post(
        "/api/plugins/source-hello/tools/write_thing/call", json={"arguments": {"value": "x"}}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["tool"] == "write_thing"
    assert "text" not in body


def test_confirm_executes_with_original_arguments(client: TestClient) -> None:
    confirmation_id = request_write(client, "abc")

    response = client.post(f"/api/confirmations/{confirmation_id}/confirm")

    assert response.status_code == 200
    assert response.json()["text"] == ["wrote abc"]


def test_confirmation_cannot_be_reused(client: TestClient) -> None:
    confirmation_id = request_write(client)
    client.post(f"/api/confirmations/{confirmation_id}/confirm")

    assert client.post(f"/api/confirmations/{confirmation_id}/confirm").status_code == 404


def test_unknown_confirmation_is_404(client: TestClient) -> None:
    assert client.post("/api/confirmations/nope/confirm").status_code == 404


def test_unreachable_plugin_gives_generic_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_url: str) -> Any:
        raise OSError("connect failed: internal-host:8000")

    monkeypatch.setattr(mcp_client, "Client", broken)

    response = client.get("/api/plugins/source-hello/tools")

    assert response.status_code == 502
    assert response.json() == {"detail": "Plugin unavailable"}
