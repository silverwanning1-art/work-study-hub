"""Source plugin: an MCP server that wraps the existing RAG server (read-only)."""

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

RAG_URL = os.environ.get("RAG_URL", "http://host.docker.internal:5678")
MAX_QUESTION_LENGTH = 1000
MAX_TOP_K = 20
TIMEOUT_SECONDS = 30.0

server = MCPServer("source-rag")


def _citation(chunk: dict[str, Any]) -> str:
    """Build the citation string the agent must use: ``[Quelle: Datei, S. X]``."""
    page = chunk.get("page_start")
    name = chunk.get("source_file") or chunk.get("source_path", "unbekannt")
    return f"[Quelle: {name}, S. {page}]" if page is not None else f"[Quelle: {name}]"


def _normalize(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": chunk["content"],
        "source_path": chunk["source_path"],
        "source_file": chunk.get("source_file"),
        "subject": chunk.get("subject"),
        "page": chunk.get("page_start"),
        "score": chunk.get("score"),
        "citation": _citation(chunk),
    }


async def search_chunks(
    question: str, top_k: int = 5, client: httpx.AsyncClient | None = None
) -> list[dict[str, Any]]:
    """Query the RAG server and return normalized chunks with citations."""
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"question must not exceed {MAX_QUESTION_LENGTH} characters")
    if not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")

    owns_client = client is None
    http = client or httpx.AsyncClient(base_url=RAG_URL, timeout=TIMEOUT_SECONDS)
    try:
        response = await http.post("/query", json={"question": question, "top_k": top_k})
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            await http.aclose()
    return [_normalize(chunk) for chunk in payload.get("chunks", [])]


@server.tool()
async def search(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the lecture scripts; returns chunks with source path, page and a citation."""
    return await search_chunks(question, top_k)


@server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health(_request: Request) -> JSONResponse:
    """Liveness check for the container runtime."""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal
