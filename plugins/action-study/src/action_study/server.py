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
from action_study.exam_schemas import (
    AttemptList,
    AttemptOut,
    ExamIn,
    ExamList,
    ExamOut,
    GradingIn,
    ProfileIn,
    ProfileList,
    ProfileOut,
)
from action_study.exam_schemas import Deleted as ExamDeleted
from action_study.exam_service import ExamService
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


def build_server(service: StudyService, exams: ExamService) -> MCPServer:
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

    @server.tool()
    def list_profiles() -> ProfileList:
        """List all professor profiles."""
        return _call(exams.list_profiles)

    @server.tool()
    def save_profile(profile: ProfileIn) -> ProfileOut:
        """Create a professor profile, or update it when ``id`` is set."""
        return _call(exams.save_profile, profile)

    @server.tool()
    def delete_profile(profile_id: int) -> ExamDeleted:
        """Delete a professor profile (exams made with it stay). Needs confirmation."""
        return _call(exams.delete_profile, profile_id)

    @server.tool()
    def list_exams() -> ExamList:
        """List mock exams, newest first."""
        return _call(exams.list_exams)

    @server.tool()
    def get_exam(exam_id: int) -> ExamOut:
        """Return an exam with questions and model answers."""
        return _call(exams.get_exam, exam_id)

    @server.tool()
    def save_exam(exam: ExamIn) -> ExamOut:
        """Store a new exam with its questions. Needs confirmation."""
        return _call(exams.save_exam, exam)

    @server.tool()
    def delete_exam(exam_id: int) -> ExamDeleted:
        """Delete an exam with its attempts. Needs confirmation."""
        return _call(exams.delete_exam, exam_id)

    @server.tool()
    def start_attempt(exam_id: int, mode: str) -> AttemptOut:
        """Begin a run through an exam; mode is 'schreiben' or 'abfrage'."""
        return _call(exams.start_attempt, exam_id, mode)

    @server.tool()
    def get_attempt(attempt_id: int) -> AttemptOut:
        """Return an attempt with answers, points and points per topic."""
        return _call(exams.get_attempt, attempt_id)

    @server.tool()
    def list_attempts(exam_id: int) -> AttemptList:
        """List the attempts of an exam, newest first."""
        return _call(exams.list_attempts, exam_id)

    @server.tool()
    def save_answer(
        attempt_id: int, question_id: int, answer_text: str = "", self_rating: int | None = None
    ) -> AttemptOut:
        """Store the own answer and/or the self rating (0 wrong, 1 partly, 2 right)."""
        return _call(exams.save_answer, attempt_id, question_id, answer_text, self_rating)

    @server.tool()
    def save_grading(attempt_id: int, gradings: list[GradingIn]) -> AttemptOut:
        """Store AI gradings (points, feedback) for questions of an attempt."""
        return _call(exams.save_grading, attempt_id, gradings)

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
    server = build_server(StudyService(session_factory), ExamService(session_factory))
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal


if __name__ == "__main__":
    main()
