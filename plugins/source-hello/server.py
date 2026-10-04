"""Example source plugin: an MCP server exposing a single greeting tool."""

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

server = MCPServer("source-hello")


@server.tool()
def hello(name: str) -> str:
    """Greet ``name``."""
    return f"Hello, {name}!"


@server.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    """Liveness check for the container runtime."""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal
