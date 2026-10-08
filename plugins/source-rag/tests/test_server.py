import asyncio
import json

import httpx
import pytest
from mcp import Client
from server import search_chunks, server

CHUNK = {
    "content": "Typische Gliederung eines Lastenheftes",
    "source_path": "originals/01_Bachelor/22_Marketing/Marketing.pdf",
    "source_file": "Marketing.pdf",
    "subject": "22_Marketing",
    "pages": "29",
    "page_start": 29,
    "score": 0.88,
}


def make_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="http://rag", transport=handler)


def test_search_returns_chunks_with_citation() -> None:
    seen: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"chunks": [CHUNK]})

    async def run() -> list[dict[str, object]]:
        async with make_client(httpx.MockTransport(handle)) as client:
            return await search_chunks("Was ist ein Lastenheft?", 3, client)

    result = asyncio.run(run())
    assert seen == {"question": "Was ist ein Lastenheft?", "top_k": 3}
    assert result[0]["citation"] == "[Quelle: Marketing.pdf, S. 29]"
    assert result[0]["source_path"] == CHUNK["source_path"]
    assert result[0]["page"] == 29


def test_citation_without_page() -> None:
    chunk = {**CHUNK, "page_start": None}

    async def run() -> list[dict[str, object]]:
        transport = httpx.MockTransport(lambda _r: httpx.Response(200, json={"chunks": [chunk]}))
        async with make_client(transport) as client:
            return await search_chunks("x", 1, client)

    assert asyncio.run(run())[0]["citation"] == "[Quelle: Marketing.pdf]"


@pytest.mark.parametrize(
    ("question", "top_k"),
    [("", 5), ("   ", 5), ("a" * 1001, 5), ("ok", 0), ("ok", 21)],
)
def test_invalid_input_is_rejected(question: str, top_k: int) -> None:
    with pytest.raises(ValueError):
        asyncio.run(search_chunks(question, top_k))


def test_upstream_error_is_raised() -> None:
    async def run() -> None:
        transport = httpx.MockTransport(lambda _r: httpx.Response(500))
        async with make_client(transport) as client:
            await search_chunks("x", 1, client)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())


def test_search_tool_is_exposed_over_mcp() -> None:
    async def run() -> list[str]:
        async with Client(server) as client:
            tools = await client.list_tools()
        return [tool.name for tool in tools.tools]

    assert asyncio.run(run()) == ["search"]
