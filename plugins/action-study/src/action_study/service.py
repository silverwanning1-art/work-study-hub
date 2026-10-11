"""Flashcards: decks, cards, reviews and statistics."""

from collections.abc import Callable
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from action_study.errors import InvalidInputError, NotFoundError
from action_study.models import Card, Deck, ReviewLog
from action_study.scheduling import CardState, Rating, schedule
from action_study.schemas import (
    MAX_CARDS_PER_SAVE,
    MAX_DUE_LIMIT,
    CardIn,
    CardList,
    CardOut,
    DeckList,
    DeckOut,
    Deleted,
    SaveCardsResult,
    Stats,
)


def _card_out(card: Card) -> CardOut:
    return CardOut(
        id=card.id,
        deck_id=card.deck_id,
        front=card.front,
        back=card.back,
        source_citation=card.source_citation,
        source_path=card.source_path,
        due=card.due,
        interval_days=card.interval_days,
        reps=card.reps,
        lapses=card.lapses,
    )


class StudyService:
    """All flashcard use cases. ``today`` is injectable for tests."""

    def __init__(
        self, session_factory: sessionmaker[Session], today: Callable[[], date] = date.today
    ) -> None:
        self._sessions = session_factory
        self._today = today

    def _deck_out(self, session: Session, deck: Deck) -> DeckOut:
        today = self._today()
        count = session.scalar(select(func.count()).where(Card.deck_id == deck.id)) or 0
        due = (
            session.scalar(select(func.count()).where(Card.deck_id == deck.id, Card.due <= today))
            or 0
        )
        return DeckOut(
            id=deck.id, name=deck.name, subject=deck.subject, card_count=count, due_count=due
        )

    def list_decks(self) -> DeckList:
        """List all decks with card and due counts."""
        with self._sessions() as session:
            decks = session.scalars(select(Deck).order_by(Deck.name)).all()
            return DeckList(decks=[self._deck_out(session, d) for d in decks])

    def list_cards(self, deck_id: int) -> CardList:
        """List all cards of a deck."""
        with self._sessions() as session:
            if session.get(Deck, deck_id) is None:
                raise NotFoundError("Stapel nicht gefunden.")
            cards = session.scalars(
                select(Card).where(Card.deck_id == deck_id).order_by(Card.id)
            ).all()
            return CardList(cards=[_card_out(c) for c in cards])

    def get_due_cards(self, deck_id: int | None = None, limit: int = 20) -> CardList:
        """Return cards due today or earlier, oldest first."""
        if not 1 <= limit <= MAX_DUE_LIMIT:
            raise InvalidInputError(f"limit muss zwischen 1 und {MAX_DUE_LIMIT} liegen.")
        query = select(Card).where(Card.due <= self._today())
        if deck_id is not None:
            query = query.where(Card.deck_id == deck_id)
        with self._sessions() as session:
            cards = session.scalars(query.order_by(Card.due, Card.id).limit(limit)).all()
            return CardList(cards=[_card_out(c) for c in cards])

    def rate_card(self, card_id: int, rating: int) -> CardOut:
        """Apply a rating (1 again, 2 hard, 3 good, 4 easy) and reschedule the card."""
        try:
            parsed = Rating(rating)
        except ValueError:
            raise InvalidInputError("Bewertung muss 1, 2, 3 oder 4 sein.") from None
        today = self._today()
        with self._sessions() as session:
            card = session.get(Card, card_id)
            if card is None:
                raise NotFoundError("Karte nicht gefunden.")
            new = schedule(
                CardState(card.reps, card.interval_days, card.ease, card.lapses, card.due),
                parsed,
                today,
            )
            card.reps, card.interval_days, card.ease = new.reps, new.interval_days, new.ease
            card.lapses, card.due = new.lapses, new.due
            session.add(
                ReviewLog(
                    card_id=card.id,
                    reviewed_on=today,
                    rating=int(parsed),
                    interval_after=new.interval_days,
                )
            )
            session.commit()
            return _card_out(card)

    def save_cards(self, deck_name: str, subject: str, cards: list[CardIn]) -> SaveCardsResult:
        """Add cards to the deck with that name; the deck is created if it does not exist."""
        name = deck_name.strip()
        if not name or len(name) > 200:
            raise InvalidInputError("Der Stapelname muss 1 bis 200 Zeichen lang sein.")
        if not 1 <= len(cards) <= MAX_CARDS_PER_SAVE:
            raise InvalidInputError(
                f"Es sind 1 bis {MAX_CARDS_PER_SAVE} Karten pro Speichern erlaubt."
            )
        today = self._today()
        with self._sessions() as session:
            deck = session.scalar(select(Deck).where(Deck.name == name))
            if deck is None:
                deck = Deck(name=name, subject=subject.strip()[:200])
                session.add(deck)
                session.flush()
            for card in cards:
                session.add(
                    Card(
                        deck_id=deck.id,
                        front=card.front,
                        back=card.back,
                        source_citation=card.source_citation,
                        source_path=card.source_path,
                        due=today,
                    )
                )
            session.commit()
            return SaveCardsResult(deck=self._deck_out(session, deck), saved=len(cards))

    def delete_deck(self, deck_id: int) -> Deleted:
        """Delete a deck with all its cards and review history."""
        with self._sessions() as session:
            if session.get(Deck, deck_id) is None:
                raise NotFoundError("Stapel nicht gefunden.")
            session.execute(delete(Deck).where(Deck.id == deck_id))
            session.commit()
        return Deleted(deleted=True)

    def get_stats(self) -> Stats:
        """Overall statistics."""
        today = self._today()
        since = today - timedelta(days=30)
        with self._sessions() as session:
            decks = session.scalar(select(func.count(Deck.id))) or 0
            cards = session.scalar(select(func.count(Card.id))) or 0
            due = session.scalar(select(func.count(Card.id)).where(Card.due <= today)) or 0
            reviewed = (
                session.scalar(
                    select(func.count(ReviewLog.id)).where(ReviewLog.reviewed_on == today)
                )
                or 0
            )
            recent = (
                session.scalar(
                    select(func.count(ReviewLog.id)).where(ReviewLog.reviewed_on >= since)
                )
                or 0
            )
            good = (
                session.scalar(
                    select(func.count(ReviewLog.id)).where(
                        ReviewLog.reviewed_on >= since, ReviewLog.rating >= Rating.GOOD
                    )
                )
                or 0
            )
        retention = round(100 * good / recent) if recent else None
        return Stats(
            deck_count=decks,
            card_count=cards,
            due_today=due,
            reviewed_today=reviewed,
            retention_percent=retention,
        )
