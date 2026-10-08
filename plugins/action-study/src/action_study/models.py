"""ORM models. Learning state lives directly on the card."""

from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DEFAULT_EASE = 2500  # ease factor in thousandths (2.5)


class Base(DeclarativeBase):
    """Declarative base for all tables."""


class Deck(Base):
    """A set of cards, usually one lecture or topic."""

    __tablename__ = "deck"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    subject: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    cards: Mapped[list["Card"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan", passive_deletes=True
    )


class Card(Base):
    """A flashcard with its spaced-repetition state."""

    __tablename__ = "card"

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("deck.id", ondelete="CASCADE"), index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    source_citation: Mapped[str] = mapped_column(String(300), default="")
    source_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    due: Mapped[date] = mapped_column(index=True)
    interval_days: Mapped[int] = mapped_column(default=0)
    ease: Mapped[int] = mapped_column(default=DEFAULT_EASE)
    reps: Mapped[int] = mapped_column(default=0)
    lapses: Mapped[int] = mapped_column(default=0)

    deck: Mapped[Deck] = relationship(back_populates="cards")
    reviews: Mapped[list["ReviewLog"]] = relationship(
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )


class ReviewLog(Base):
    """One rating of a card, kept for statistics."""

    __tablename__ = "review_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("card.id", ondelete="CASCADE"), index=True)
    reviewed_on: Mapped[date] = mapped_column(index=True)
    rating: Mapped[int]
    interval_after: Mapped[int]

    card: Mapped[Card] = relationship(back_populates="reviews")
