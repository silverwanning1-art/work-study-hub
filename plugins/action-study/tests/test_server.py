import asyncio
from typing import Any

from action_study.exam_service import ExamService
from action_study.server import build_server
from action_study.service import StudyService
from mcp import Client

CARD = {
    "front": "Was ist FIFO?",
    "back": "First in, first out",
    "source_citation": "[Quelle: A.pdf, S. 3]",
}


async def call(service: StudyService, tool: str, arguments: dict[str, Any]) -> Any:
    async with Client(build_server(service, ExamService(service._sessions))) as client:  # noqa: SLF001
        return await client.call_tool(tool, arguments)


def test_save_list_and_rate_over_mcp(service: StudyService) -> None:
    saved = asyncio.run(call(service, "save_cards", {"deck_name": "Logistik", "cards": [CARD]}))
    assert saved.structured_content["saved"] == 1

    due = asyncio.run(call(service, "get_due_cards", {}))
    card_id = due.structured_content["cards"][0]["id"]

    rated = asyncio.run(call(service, "rate_card", {"card_id": card_id, "rating": 3}))
    assert rated.structured_content["interval_days"] == 1


def test_domain_errors_reach_the_client_with_their_message(service: StudyService) -> None:
    result = asyncio.run(call(service, "rate_card", {"card_id": 99, "rating": 3}))
    assert result.is_error
    assert "Karte nicht gefunden" in result.content[0].text


def test_unknown_fields_are_rejected(service: StudyService) -> None:
    result = asyncio.run(
        call(service, "save_cards", {"deck_name": "D", "cards": [{**CARD, "evil": "x"}]})
    )
    assert result.is_error
    assert asyncio.run(call(service, "list_decks", {})).structured_content["decks"] == []


def test_manifest_matches_the_server(service: StudyService) -> None:
    from pathlib import Path

    import yaml

    manifest = yaml.safe_load((Path(__file__).parents[1] / "plugin.yaml").read_text())

    async def run() -> set[str]:
        async with Client(build_server(service, ExamService(service._sessions))) as client:  # noqa: SLF001
            return {t.name for t in (await client.list_tools()).tools}

    assert {t["name"] for t in manifest["tools"]} == asyncio.run(run())
    writes = {t["name"] for t in manifest["tools"] if t.get("writes")}
    assert writes == {"save_cards", "delete_deck", "save_exam", "delete_exam", "delete_profile"}
