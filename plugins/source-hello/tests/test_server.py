import asyncio

from mcp import Client
from server import hello, server


def test_hello_greets_by_name() -> None:
    assert hello("Silver") == "Hello, Silver!"


def test_hello_is_exposed_over_mcp() -> None:
    async def run() -> str:
        async with Client(server) as client:
            result = await client.call_tool("hello", {"name": "Test"})
        return result.content[0].text  # type: ignore[union-attr]

    assert asyncio.run(run()) == "Hello, Test!"
