"""Pydantic models for tool inputs and outputs."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Line = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CardText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

MAX_CARDS_PER_SAVE = 100
MAX_DUE_LIMIT = 100


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CardIn(_Input):
    """A new card with an optional source reference."""

    front: CardText
    back: CardText
    source_citation: Line = ""
    source_path: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class CardOut(BaseModel):
    """A card with its learning state."""

    id: int
    deck_id: int
    front: str
    back: str
    source_citation: str
    source_path: str
    due: date
    interval_days: int
    reps: int
    lapses: int


class CardList(BaseModel):
    """Result of a card query."""

    cards: list[CardOut]


class DeckOut(BaseModel):
    """A deck with counters."""

    id: int
    name: str
    subject: str
    card_count: int
    due_count: int


class DeckList(BaseModel):
    """All decks."""

    decks: list[DeckOut]


class SaveCardsResult(BaseModel):
    """Result of saving cards."""

    deck: DeckOut
    saved: int


class Deleted(BaseModel):
    """Result of a delete."""

    deleted: bool


class Stats(BaseModel):
    """Overall learning statistics."""

    deck_count: int
    card_count: int
    due_today: int
    reviewed_today: int
    retention_percent: Annotated[
        int | None, Field(description="Share of 'good'/'easy' in the last 30 days")
    ]
