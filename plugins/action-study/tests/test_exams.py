import pytest
from action_study.errors import InvalidInputError, NotFoundError
from action_study.exam_schemas import ExamIn, GradingIn, ProfileIn, QuestionIn
from action_study.exam_service import ExamService
from pydantic import ValidationError


def profile(**overrides: object) -> ProfileIn:
    base: dict[str, object] = {"name": "Prof. Beispiel", "subject": "Logistik"}
    return ProfileIn.model_validate({**base, **overrides})


def mc(points: int = 2, topic: str = "Lager") -> QuestionIn:
    return QuestionIn(
        kind="mc",
        topic=topic,
        prompt="Was bedeutet FIFO?",
        options=["First in, first out", "Last in, first out"],
        model_answer="First in, first out",
        points=points,
    )


def open_q(points: int = 8, topic: str = "Bestand") -> QuestionIn:
    return QuestionIn(
        kind="open",
        topic=topic,
        prompt="Erkläre den Bestellpunkt.",
        model_answer="...",
        points=points,
    )


def make_exam(exams: ExamService) -> int:
    return exams.save_exam(
        ExamIn(title="Probe 1", subject="Logistik", questions=[mc(), open_q()])
    ).id


# --- profiles ---------------------------------------------------------------------------------


def test_profile_shares_must_sum_to_100() -> None:
    with pytest.raises(ValidationError):
        profile(share_mc=50, share_open=50, share_calc=50)


@pytest.mark.parametrize("difficulty", [0, 6])
def test_profile_difficulty_range(difficulty: int) -> None:
    with pytest.raises(ValidationError):
        profile(difficulty=difficulty)


def test_profile_create_update_and_unique_name(exams: ExamService) -> None:
    created = exams.save_profile(profile(description="Mag Rechenaufgaben"))
    updated = exams.save_profile(profile(id=created.id, difficulty=5))
    assert (updated.id, updated.difficulty) == (created.id, 5)
    with pytest.raises(InvalidInputError):
        exams.save_profile(profile())
    other = exams.save_profile(profile(name="Prof. Zwei"))
    with pytest.raises(InvalidInputError):
        exams.save_profile(profile(id=other.id, name="Prof. Beispiel"))
    with pytest.raises(NotFoundError):
        exams.save_profile(profile(id=999))


def test_deleting_a_profile_keeps_its_exams(exams: ExamService) -> None:
    prof = exams.save_profile(profile())
    exam = exams.save_exam(ExamIn(title="E", profile_id=prof.id, questions=[mc()]))
    exams.delete_profile(prof.id)
    assert exams.get_exam(exam.id).profile_id is None
    with pytest.raises(NotFoundError):
        exams.delete_profile(prof.id)


# --- exams ------------------------------------------------------------------------------------


def test_save_exam_orders_questions_and_sums_points(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    assert [q.position for q in exam.questions] == [1, 2]
    assert exam.total_points == 10
    assert exam.questions[0].options == ["First in, first out", "Last in, first out"]
    summary = exams.list_exams().exams[0]
    assert (summary.question_count, summary.attempt_count) == (2, 0)


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "mc", "options": ["nur eine"]},
        {"kind": "mc", "options": []},
        {"kind": "open", "options": ["a", "b"]},
        {"kind": "essay"},
        {"points": 0},
        {"points": 101},
        {"prompt": " "},
    ],
)
def test_invalid_questions_are_rejected(bad: dict[str, object]) -> None:
    base: dict[str, object] = {
        "kind": "open",
        "prompt": "Frage",
        "model_answer": "Antwort",
        "points": 5,
    }
    with pytest.raises(ValidationError):
        QuestionIn.model_validate({**base, **bad})


def test_exam_needs_questions_and_known_profile(exams: ExamService) -> None:
    with pytest.raises(ValidationError):
        ExamIn(title="E", questions=[])
    with pytest.raises(NotFoundError):
        exams.save_exam(ExamIn(title="E", profile_id=42, questions=[mc()]))


def test_delete_exam_removes_attempts(exams: ExamService) -> None:
    exam_id = make_exam(exams)
    attempt = exams.start_attempt(exam_id, "abfrage")
    exams.delete_exam(exam_id)
    with pytest.raises(NotFoundError):
        exams.get_attempt(attempt.id)


# --- attempts: abfrage ------------------------------------------------------------------------


def test_abfrage_self_rating_gives_points(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(exam.id, "abfrage")
    exams.save_answer(attempt.id, exam.questions[0].id, self_rating=2)
    result = exams.save_answer(attempt.id, exam.questions[1].id, self_rating=1)
    assert result.scored_points == 2 + 4.0
    assert (result.possible_points, result.answered_count) == (10, 2)
    topics = {t.topic: (t.scored, t.possible) for t in result.by_topic}
    assert topics == {"Lager": (2.0, 2), "Bestand": (4.0, 8)}


def test_abfrage_rejects_answer_text_and_bad_rating(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(exam.id, "abfrage")
    qid = exam.questions[0].id
    with pytest.raises(InvalidInputError):
        exams.save_answer(attempt.id, qid, answer_text="Text")
    for rating in (-1, 3):
        with pytest.raises(InvalidInputError):
            exams.save_answer(attempt.id, qid, self_rating=rating)


# --- attempts: schreiben + grading ------------------------------------------------------------


def test_schreiben_saves_text_and_grading_overrides_self_rating(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(exam.id, "schreiben")
    qid = exam.questions[1].id
    exams.save_answer(attempt.id, qid, answer_text="  Meine Antwort  ", self_rating=2)
    graded = exams.save_grading(
        attempt.id, [GradingIn(question_id=qid, points=3, feedback="Teil fehlt")]
    )
    answer = graded.answers[0]
    assert (answer.answer_text, answer.ai_points, answer.points) == ("Meine Antwort", 3, 3.0)
    assert answer.ai_feedback == "Teil fehlt"


def test_grading_cannot_exceed_question_points(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(exam.id, "schreiben")
    qid = exam.questions[0].id  # worth 2 points
    with pytest.raises(InvalidInputError):
        exams.save_grading(attempt.id, [GradingIn(question_id=qid, points=3)])
    assert exams.get_attempt(attempt.id).answers == []


def test_grading_is_all_or_nothing(exams: ExamService) -> None:
    exam = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(exam.id, "schreiben")
    good = GradingIn(question_id=exam.questions[0].id, points=1)
    bad = GradingIn(question_id=exam.questions[1].id, points=99)
    with pytest.raises(InvalidInputError):
        exams.save_grading(attempt.id, [good, bad])
    assert exams.get_attempt(attempt.id).answers == []


def test_grading_negative_points_are_rejected() -> None:
    with pytest.raises(ValidationError):
        GradingIn(question_id=1, points=-1)


def test_question_of_another_exam_is_refused(exams: ExamService) -> None:
    first = exams.get_exam(make_exam(exams))
    second = exams.get_exam(make_exam(exams))
    attempt = exams.start_attempt(first.id, "schreiben")
    with pytest.raises(NotFoundError):
        exams.save_answer(attempt.id, second.questions[0].id, answer_text="x")
    with pytest.raises(NotFoundError):
        exams.save_grading(attempt.id, [GradingIn(question_id=second.questions[0].id, points=1)])


def test_unknown_ids_and_mode(exams: ExamService) -> None:
    exam_id = make_exam(exams)
    with pytest.raises(InvalidInputError):
        exams.start_attempt(exam_id, "blitz")
    for call in (
        lambda: exams.start_attempt(999, "abfrage"),
        lambda: exams.get_attempt(999),
        lambda: exams.list_attempts(999),
        lambda: exams.save_answer(999, 1, "x"),
    ):
        with pytest.raises(NotFoundError):
            call()


def test_list_attempts_newest_first(exams: ExamService) -> None:
    exam_id = make_exam(exams)
    first = exams.start_attempt(exam_id, "abfrage")
    second = exams.start_attempt(exam_id, "schreiben")
    assert [a.id for a in exams.list_attempts(exam_id).attempts] == [second.id, first.id]
    assert exams.list_exams().exams[0].attempt_count == 2
