import pytest
from action_study.errors import InvalidInputError, NotFoundError
from action_study.schemas import MAX_CARDS_PER_SAVE, CardIn
from action_study.service import StudyService
from conftest import Clock


def cards(count: int = 2) -> list[CardIn]:
    return [
        CardIn(front=f"Frage {i}", back=f"Antwort {i}", source_citation="[Quelle: A.pdf, S. 3]")
        for i in range(count)
    ]


def test_save_creates_deck_and_adds_to_existing(service: StudyService) -> None:
    first = service.save_cards("Logistik", "Fach", cards(2))
    second = service.save_cards("Logistik", "", cards(1))
    assert (first.saved, second.saved) == (2, 1)
    assert first.deck.id == second.deck.id
    assert service.list_decks().decks[0].card_count == 3


def test_new_cards_are_due_today(service: StudyService) -> None:
    service.save_cards("D", "", cards(3))
    assert len(service.get_due_cards().cards) == 3
    assert service.list_decks().decks[0].due_count == 3


def test_rating_reschedules_and_logs(service: StudyService, clock: Clock) -> None:
    deck = service.save_cards("D", "", cards(1)).deck
    card = service.get_due_cards(deck.id).cards[0]
    rated = service.rate_card(card.id, 3)
    assert rated.interval_days == 1
    assert service.get_due_cards().cards == []
    clock.advance(1)
    assert [c.id for c in service.get_due_cards().cards] == [card.id]
    stats = service.get_stats()
    assert (stats.reviewed_today, stats.retention_percent) == (0, 100)


def test_again_keeps_card_due_tomorrow_and_counts_lapse(service: StudyService) -> None:
    service.save_cards("D", "", cards(1))
    card = service.get_due_cards().cards[0]
    rated = service.rate_card(card.id, 1)
    assert (rated.lapses, rated.interval_days) == (1, 1)
    assert service.get_stats().retention_percent == 0


@pytest.mark.parametrize("rating", [0, 5, -1])
def test_invalid_rating(service: StudyService, rating: int) -> None:
    service.save_cards("D", "", cards(1))
    with pytest.raises(InvalidInputError):
        service.rate_card(service.get_due_cards().cards[0].id, rating)


def test_unknown_ids(service: StudyService) -> None:
    for call in (
        lambda: service.rate_card(99, 3),
        lambda: service.list_cards(99),
        lambda: service.delete_deck(99),
    ):
        with pytest.raises(NotFoundError):
            call()


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_invalid_deck_name(service: StudyService, name: str) -> None:
    with pytest.raises(InvalidInputError):
        service.save_cards(name, "", cards(1))


@pytest.mark.parametrize("count", [0, MAX_CARDS_PER_SAVE + 1])
def test_card_count_limits(service: StudyService, count: int) -> None:
    with pytest.raises(InvalidInputError):
        service.save_cards("D", "", cards(count))


def test_due_limit_is_validated(service: StudyService) -> None:
    for limit in (0, 101):
        with pytest.raises(InvalidInputError):
            service.get_due_cards(limit=limit)


def test_delete_deck_removes_cards_and_history(service: StudyService) -> None:
    deck = service.save_cards("D", "", cards(2)).deck
    service.rate_card(service.get_due_cards().cards[0].id, 3)
    service.delete_deck(deck.id)
    stats = service.get_stats()
    assert (stats.deck_count, stats.card_count, stats.retention_percent) == (0, 0, None)


def test_stats_on_empty_database(service: StudyService) -> None:
    stats = service.get_stats()
    assert (stats.card_count, stats.due_today, stats.retention_percent) == (0, 0, None)
