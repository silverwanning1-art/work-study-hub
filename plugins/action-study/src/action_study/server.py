"""MCP server exposing the study service as tools (Streamable HTTP)."""

import logging
import sys
from collections.abc import Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse

from action_study.config import Settings
from action_study.db import init_db, make_engine
from action_study.errors import StudyError
from action_study.schemas import (
    CardIn,
    CardList,
    CardOut,
    DeckList,
    Deleted,
    SaveCardsResult,
    Stats,
)
from action_study.service import StudyService


def _call[**P, T](function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Run a service method; domain errors reach the client with their (safe) message."""
    try:
        return function(*args, **kwargs)
    except StudyError as exc:
        raise ToolError(str(exc)) from exc


def build_server(service: StudyService) -> MCPServer:
    """Create the MCP server with all tools bound to ``service``."""
    server = MCPServer("action-study")

    @server.tool()
    def list_decks() -> DeckList:
        """List all decks with card and due counts."""
        return _call(service.list_decks)

    @server.tool()
    def list_cards(deck_id: int) -> CardList:
        """List all cards of a deck."""
        return _call(service.list_cards, deck_id)

    @server.tool()
    def get_due_cards(deck_id: int | None = None, limit: int = 20) -> CardList:
        """Return cards that are due today or earlier, optionally of one deck."""
        return _call(service.get_due_cards, deck_id, limit)

    @server.tool()
    def get_stats() -> Stats:
        """Return learning statistics."""
        return _call(service.get_stats)

    @server.tool()
    def rate_card(card_id: int, rating: int) -> CardOut:
        """Rate a card (1 again, 2 hard, 3 good, 4 easy) and reschedule it."""
        return _call(service.rate_card, card_id, rating)

    @server.tool()
    def save_cards(deck_name: str, cards: list[CardIn], subject: str = "") -> SaveCardsResult:
        """Add cards to a deck (created if missing). Needs confirmation."""
        return _call(service.save_cards, deck_name, subject, cards)

    @server.tool()
    def delete_deck(deck_id: int) -> Deleted:
        """Delete a deck with all cards and history. Needs confirmation."""
        return _call(service.delete_deck, deck_id)

    @server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
    async def health(_request: Request) -> JSONResponse:
        """Liveness check for the container runtime."""
        return JSONResponse({"status": "ok"})

    return server


def main() -> None:
    """Start the server with settings from the environment."""
    settings = Settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level)
    session_factory = init_db(make_engine(f"sqlite:///{settings.study_db_path}"))
    server = build_server(StudyService(session_factory))
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal


if __name__ == "__main__":
    main()
