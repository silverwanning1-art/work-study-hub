from datetime import date, timedelta

import pytest
from action_study.db import init_db, make_engine
from action_study.exam_service import ExamService
from action_study.service import StudyService

TODAY = date(2026, 11, 3)


class Clock:
    """A movable 'today' for tests."""

    def __init__(self) -> None:
        self.value = TODAY

    def __call__(self) -> date:
        return self.value

    def advance(self, days: int) -> None:
        self.value += timedelta(days=days)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def service(clock: Clock) -> StudyService:
    return StudyService(init_db(make_engine("sqlite://")), clock)


@pytest.fixture
def exams() -> ExamService:
    return ExamService(init_db(make_engine("sqlite://")), Clock())
