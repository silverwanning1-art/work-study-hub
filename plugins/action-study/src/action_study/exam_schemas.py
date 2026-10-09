"""Pydantic models for professor profiles, exams and attempts."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Line = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Required = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Option = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
AnswerText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Feedback = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]

Kind = Literal["mc", "open", "calc"]
Mode = Literal["schreiben", "abfrage"]
MAX_QUESTIONS = 40
MAX_POINTS = 100


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileIn(_Input):
    """A professor profile. The three shares describe the mix of question types in percent."""

    id: int | None = None
    name: Name
    subject: Line = ""
    description: Long = ""
    question_style: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    share_mc: Annotated[int, Field(ge=0, le=100)] = 40
    share_open: Annotated[int, Field(ge=0, le=100)] = 40
    share_calc: Annotated[int, Field(ge=0, le=100)] = 20
    difficulty: Annotated[int, Field(ge=1, le=5)] = 3
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""

    @model_validator(mode="after")
    def _shares_sum_to_100(self) -> Self:
        if self.share_mc + self.share_open + self.share_calc != 100:
            raise ValueError("Die Anteile der Aufgabentypen müssen zusammen 100 ergeben.")
        return self


class ProfileOut(ProfileIn):
    """A stored profile."""

    id: int


class ProfileList(BaseModel):
    """All profiles."""

    profiles: list[ProfileOut]


class QuestionIn(_Input):
    """A question with its model answer. Multiple choice needs 2 to 6 options."""

    kind: Kind
    topic: Line = ""
    prompt: Required
    options: Annotated[list[Option], Field(max_length=6)] = []
    model_answer: Required
    points: Annotated[int, Field(ge=1, le=MAX_POINTS)]
    source_citation: Line = ""

    @model_validator(mode="after")
    def _options_match_kind(self) -> Self:
        if self.kind == "mc" and not 2 <= len(self.options) <= 6:
            raise ValueError("Multiple-Choice-Fragen brauchen 2 bis 6 Antwortoptionen.")
        if self.kind != "mc" and self.options:
            raise ValueError("Nur Multiple-Choice-Fragen haben Antwortoptionen.")
        return self


class ExamIn(_Input):
    """A new exam."""

    title: Name
    subject: Line = ""
    profile_id: int | None = None
    questions: Annotated[list[QuestionIn], Field(min_length=1, max_length=MAX_QUESTIONS)]


class QuestionOut(BaseModel):
    """A stored question."""

    id: int
    position: int
    kind: Kind
    topic: str
    prompt: str
    options: list[str]
    model_answer: str
    points: int
    source_citation: str


class ExamOut(BaseModel):
    """An exam with its questions."""

    id: int
    title: str
    subject: str
    profile_id: int | None
    created_at: datetime
    total_points: int
    questions: list[QuestionOut]


class ExamSummary(BaseModel):
    """An exam in the list view."""

    id: int
    title: str
    subject: str
    question_count: int
    total_points: int
    attempt_count: int
    created_at: datetime


class ExamList(BaseModel):
    """All exams, newest first."""

    exams: list[ExamSummary]


class AnswerOut(BaseModel):
    """An answer with its effective points (AI points win over the self rating)."""

    question_id: int
    answer_text: str
    self_rating: int | None
    ai_points: int | None
    ai_feedback: str
    points: float | None


class TopicScore(BaseModel):
    """Points per topic."""

    topic: str
    scored: float
    possible: int


class AttemptOut(BaseModel):
    """An attempt with answers and totals."""

    id: int
    exam_id: int
    mode: Mode
    started_at: datetime
    answers: list[AnswerOut]
    scored_points: float
    possible_points: int
    answered_count: int
    by_topic: list[TopicScore]


class AttemptList(BaseModel):
    """Attempts of an exam, newest first."""

    attempts: list[AttemptOut]


class GradingIn(_Input):
    """An AI grading for one question."""

    question_id: int
    points: Annotated[int, Field(ge=0, le=MAX_POINTS)]
    feedback: Feedback = ""


class Deleted(BaseModel):
    """Result of a delete."""

    deleted: bool
