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


class ProfProfile(Base):
    """Description of a professor's examination style, used to generate mock exams."""

    __tablename__ = "prof_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    subject: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    question_style: Mapped[str] = mapped_column(Text, default="")
    share_mc: Mapped[int] = mapped_column(default=40)
    share_open: Mapped[int] = mapped_column(default=40)
    share_calc: Mapped[int] = mapped_column(default=20)
    difficulty: Mapped[int] = mapped_column(default=3)
    notes: Mapped[str] = mapped_column(Text, default="")


class Exam(Base):
    """A mock exam made of questions."""

    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(200), default="")
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("prof_profile.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExamQuestion.position",
    )
    attempts: Mapped[list["ExamAttempt"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", passive_deletes=True
    )


class ExamQuestion(Base):
    """One question; ``options`` is a JSON list for multiple choice and empty otherwise."""

    __tablename__ = "exam_question"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    kind: Mapped[str] = mapped_column(String(10))
    topic: Mapped[str] = mapped_column(String(300), default="")
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[str] = mapped_column(Text, default="[]")
    model_answer: Mapped[str] = mapped_column(Text)
    points: Mapped[int]
    source_citation: Mapped[str] = mapped_column(String(300), default="")

    exam: Mapped[Exam] = relationship(back_populates="questions")


class ExamAttempt(Base):
    """One run through an exam, in mode ``schreiben`` (own answers) or ``abfrage`` (recall)."""

    __tablename__ = "exam_attempt"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    started_at: Mapped[datetime] = mapped_column(default=datetime.now)

    exam: Mapped[Exam] = relationship(back_populates="attempts")
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", passive_deletes=True
    )


class AttemptAnswer(Base):
    """The answer to one question: own text, self rating (0, 1, 2) and/or AI grading."""

    __tablename__ = "attempt_answer"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("exam_attempt.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("exam_question.id", ondelete="CASCADE"), index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, default="")
    self_rating: Mapped[int | None] = mapped_column(default=None)
    ai_points: Mapped[int | None] = mapped_column(default=None)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")

    attempt: Mapped[ExamAttempt] = relationship(back_populates="answers")
