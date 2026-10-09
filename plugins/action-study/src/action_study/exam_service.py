"""Professor profiles, mock exams, attempts and grading."""

import json
from collections.abc import Callable
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from action_study.errors import InvalidInputError, NotFoundError
from action_study.exam_schemas import (
    AnswerOut,
    AttemptList,
    AttemptOut,
    Deleted,
    ExamIn,
    ExamList,
    ExamOut,
    ExamSummary,
    GradingIn,
    ProfileIn,
    ProfileList,
    ProfileOut,
    QuestionOut,
    TopicScore,
)
from action_study.models import (
    AttemptAnswer,
    Exam,
    ExamAttempt,
    ExamQuestion,
    ProfProfile,
)

MAX_PROFILES = 100
MAX_EXAMS = 200
MAX_GRADINGS = 40


def _profile_out(profile: ProfProfile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        name=profile.name,
        subject=profile.subject,
        description=profile.description,
        question_style=profile.question_style,
        share_mc=profile.share_mc,
        share_open=profile.share_open,
        share_calc=profile.share_calc,
        difficulty=profile.difficulty,
        notes=profile.notes,
    )


def _question_out(question: ExamQuestion) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        position=question.position,
        kind=question.kind,  # type: ignore[arg-type]
        topic=question.topic,
        prompt=question.prompt,
        options=json.loads(question.options),
        model_answer=question.model_answer,
        points=question.points,
        source_citation=question.source_citation,
    )


def _exam_out(exam: Exam) -> ExamOut:
    return ExamOut(
        id=exam.id,
        title=exam.title,
        subject=exam.subject,
        profile_id=exam.profile_id,
        created_at=exam.created_at,
        total_points=sum(q.points for q in exam.questions),
        questions=[_question_out(q) for q in exam.questions],
    )


def effective_points(question: ExamQuestion, answer: AttemptAnswer) -> float | None:
    """AI points win over the self rating (0, 1, 2 = none, half, full); ``None`` if unrated."""
    if answer.ai_points is not None:
        return float(answer.ai_points)
    if answer.self_rating is not None:
        return question.points * answer.self_rating / 2
    return None


class ExamService:
    """All profile, exam and attempt use cases."""

    def __init__(
        self, session_factory: sessionmaker[Session], today: Callable[[], date] = date.today
    ) -> None:
        self._sessions = session_factory
        self._today = today

    # --- profiles ---------------------------------------------------------------------------

    def list_profiles(self) -> ProfileList:
        """List all professor profiles."""
        with self._sessions() as session:
            profiles = session.scalars(select(ProfProfile).order_by(ProfProfile.name)).all()
            return ProfileList(profiles=[_profile_out(p) for p in profiles])

    def save_profile(self, data: ProfileIn) -> ProfileOut:
        """Create a profile, or update it when ``id`` is set. Names are unique."""
        with self._sessions() as session:
            same_name = session.scalar(select(ProfProfile).where(ProfProfile.name == data.name))
            if data.id is None:
                if same_name is not None:
                    raise InvalidInputError("Ein Profil mit diesem Namen existiert bereits.")
                if (session.scalar(select(func.count(ProfProfile.id))) or 0) >= MAX_PROFILES:
                    raise InvalidInputError("Zu viele Profile.")
                profile = ProfProfile()
                session.add(profile)
            else:
                existing = session.get(ProfProfile, data.id)
                if existing is None:
                    raise NotFoundError("Profil nicht gefunden.")
                if same_name is not None and same_name.id != data.id:
                    raise InvalidInputError("Ein Profil mit diesem Namen existiert bereits.")
                profile = existing
            for field in (
                "name", "subject", "description", "question_style", "share_mc",
                "share_open", "share_calc", "difficulty", "notes",
            ):  # fmt: skip
                setattr(profile, field, getattr(data, field))
            session.commit()
            return _profile_out(profile)

    def delete_profile(self, profile_id: int) -> Deleted:
        """Delete a profile; exams made with it stay (their profile link becomes empty)."""
        with self._sessions() as session:
            profile = session.get(ProfProfile, profile_id)
            if profile is None:
                raise NotFoundError("Profil nicht gefunden.")
            for exam in session.scalars(select(Exam).where(Exam.profile_id == profile_id)):
                exam.profile_id = None
            session.delete(profile)
            session.commit()
        return Deleted(deleted=True)

    # --- exams ------------------------------------------------------------------------------

    def list_exams(self) -> ExamList:
        """List exams, newest first."""
        with self._sessions() as session:
            exams = session.scalars(select(Exam).order_by(Exam.id.desc())).all()
            return ExamList(
                exams=[
                    ExamSummary(
                        id=e.id,
                        title=e.title,
                        subject=e.subject,
                        question_count=len(e.questions),
                        total_points=sum(q.points for q in e.questions),
                        attempt_count=len(e.attempts),
                        created_at=e.created_at,
                    )
                    for e in exams
                ]
            )

    def get_exam(self, exam_id: int) -> ExamOut:
        """Return an exam with questions and model answers."""
        with self._sessions() as session:
            exam = session.get(Exam, exam_id)
            if exam is None:
                raise NotFoundError("Prüfung nicht gefunden.")
            return _exam_out(exam)

    def save_exam(self, data: ExamIn) -> ExamOut:
        """Store a new exam with its questions."""
        with self._sessions() as session:
            if data.profile_id is not None and session.get(ProfProfile, data.profile_id) is None:
                raise NotFoundError("Profil nicht gefunden.")
            if (session.scalar(select(func.count(Exam.id))) or 0) >= MAX_EXAMS:
                raise InvalidInputError("Zu viele Prüfungen.")
            exam = Exam(title=data.title, subject=data.subject, profile_id=data.profile_id)
            for position, question in enumerate(data.questions, start=1):
                exam.questions.append(
                    ExamQuestion(
                        position=position,
                        kind=question.kind,
                        topic=question.topic,
                        prompt=question.prompt,
                        options=json.dumps(question.options, ensure_ascii=False),
                        model_answer=question.model_answer,
                        points=question.points,
                        source_citation=question.source_citation,
                    )
                )
            session.add(exam)
            session.commit()
            return _exam_out(exam)

    def delete_exam(self, exam_id: int) -> Deleted:
        """Delete an exam with its questions and attempts."""
        with self._sessions() as session:
            exam = session.get(Exam, exam_id)
            if exam is None:
                raise NotFoundError("Prüfung nicht gefunden.")
            session.delete(exam)
            session.commit()
        return Deleted(deleted=True)

    # --- attempts ---------------------------------------------------------------------------

    def _attempt_out(self, attempt: ExamAttempt) -> AttemptOut:
        by_id = {a.question_id: a for a in attempt.answers}
        answers: list[AnswerOut] = []
        topics: dict[str, list[float]] = {}
        scored = 0.0
        for question in attempt.exam.questions:
            answer = by_id.get(question.id)
            points = effective_points(question, answer) if answer else None
            if answer is not None:
                answers.append(
                    AnswerOut(
                        question_id=question.id,
                        answer_text=answer.answer_text,
                        self_rating=answer.self_rating,
                        ai_points=answer.ai_points,
                        ai_feedback=answer.ai_feedback,
                        points=points,
                    )
                )
            entry = topics.setdefault(question.topic or "Ohne Thema", [0.0, 0.0])
            entry[1] += question.points
            if points is not None:
                entry[0] += points
                scored += points
        return AttemptOut(
            id=attempt.id,
            exam_id=attempt.exam_id,
            mode=attempt.mode,  # type: ignore[arg-type]
            started_at=attempt.started_at,
            answers=answers,
            scored_points=scored,
            possible_points=sum(q.points for q in attempt.exam.questions),
            answered_count=len(answers),
            by_topic=[
                TopicScore(topic=t, scored=v[0], possible=int(v[1])) for t, v in topics.items()
            ],
        )

    def start_attempt(self, exam_id: int, mode: str) -> AttemptOut:
        """Begin a run through an exam in mode ``schreiben`` or ``abfrage``."""
        if mode not in ("schreiben", "abfrage"):
            raise InvalidInputError("Modus muss 'schreiben' oder 'abfrage' sein.")
        with self._sessions() as session:
            if session.get(Exam, exam_id) is None:
                raise NotFoundError("Prüfung nicht gefunden.")
            attempt = ExamAttempt(exam_id=exam_id, mode=mode)
            session.add(attempt)
            session.commit()
            return self._attempt_out(attempt)

    def _attempt(self, session: Session, attempt_id: int) -> ExamAttempt:
        attempt = session.get(ExamAttempt, attempt_id)
        if attempt is None:
            raise NotFoundError("Durchführung nicht gefunden.")
        return attempt

    def get_attempt(self, attempt_id: int) -> AttemptOut:
        """Return an attempt with answers and totals."""
        with self._sessions() as session:
            return self._attempt_out(self._attempt(session, attempt_id))

    def list_attempts(self, exam_id: int) -> AttemptList:
        """List attempts of an exam, newest first."""
        with self._sessions() as session:
            if session.get(Exam, exam_id) is None:
                raise NotFoundError("Prüfung nicht gefunden.")
            attempts = session.scalars(
                select(ExamAttempt)
                .where(ExamAttempt.exam_id == exam_id)
                .order_by(ExamAttempt.id.desc())
            ).all()
            return AttemptList(attempts=[self._attempt_out(a) for a in attempts])

    def _answer(self, session: Session, attempt: ExamAttempt, question_id: int) -> AttemptAnswer:
        if question_id not in {q.id for q in attempt.exam.questions}:
            raise NotFoundError("Frage gehört nicht zu dieser Prüfung.")
        answer = session.scalar(
            select(AttemptAnswer).where(
                AttemptAnswer.attempt_id == attempt.id, AttemptAnswer.question_id == question_id
            )
        )
        if answer is None:
            answer = AttemptAnswer(attempt_id=attempt.id, question_id=question_id)
            session.add(answer)
        return answer

    def save_answer(
        self,
        attempt_id: int,
        question_id: int,
        answer_text: str = "",
        self_rating: int | None = None,
    ) -> AttemptOut:
        """Store the own answer text and/or the self rating (0 wrong, 1 partly, 2 right)."""
        if self_rating is not None and self_rating not in (0, 1, 2):
            raise InvalidInputError("Selbstbewertung muss 0, 1 oder 2 sein.")
        if len(answer_text) > 4000:
            raise InvalidInputError("Die Antwort ist zu lang (höchstens 4000 Zeichen).")
        with self._sessions() as session:
            attempt = self._attempt(session, attempt_id)
            answer = self._answer(session, attempt, question_id)
            if attempt.mode == "abfrage" and answer_text:
                raise InvalidInputError("Im Modus 'abfrage' gibt es keinen Antworttext.")
            if answer_text or attempt.mode == "schreiben":
                answer.answer_text = answer_text.strip()
            if self_rating is not None:
                answer.self_rating = self_rating
            session.commit()
            return self._attempt_out(attempt)

    def save_grading(self, attempt_id: int, gradings: list[GradingIn]) -> AttemptOut:
        """Store AI gradings. Points must not exceed the question's points."""
        if not 1 <= len(gradings) <= MAX_GRADINGS:
            raise InvalidInputError(f"Es sind 1 bis {MAX_GRADINGS} Bewertungen erlaubt.")
        with self._sessions() as session:
            attempt = self._attempt(session, attempt_id)
            limits = {q.id: q.points for q in attempt.exam.questions}
            for grading in gradings:
                if grading.question_id not in limits:
                    raise NotFoundError("Frage gehört nicht zu dieser Prüfung.")
                if grading.points > limits[grading.question_id]:
                    raise InvalidInputError(
                        f"Mehr Punkte als möglich ({limits[grading.question_id]}) vergeben."
                    )
            for grading in gradings:
                answer = self._answer(session, attempt, grading.question_id)
                answer.ai_points = grading.points
                answer.ai_feedback = grading.feedback
            session.commit()
            return self._attempt_out(attempt)
