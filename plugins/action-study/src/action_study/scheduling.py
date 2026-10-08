"""Spaced repetition: an SM-2 style schedule as a pure function (integer arithmetic only)."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import IntEnum

MIN_EASE = 1300
MAX_INTERVAL_DAYS = 365


class Rating(IntEnum):
    """How well the card was remembered."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True)
class CardState:
    """The part of a card the schedule depends on."""

    reps: int
    interval_days: int
    ease: int
    lapses: int
    due: date


def _grow(interval: int, ease: int, extra_percent: int = 100) -> int:
    return (interval * ease * extra_percent + 50_000) // 100_000


def schedule(state: CardState, rating: Rating, today: date) -> CardState:
    """Return the new state after rating a card on ``today``."""
    ease, lapses = state.ease, state.lapses
    if rating is Rating.AGAIN:
        return CardState(0, 1, max(MIN_EASE, ease - 200), lapses + 1, today + timedelta(days=1))

    if rating is Rating.HARD:
        ease = max(MIN_EASE, ease - 150)
        interval = (
            1 if state.reps == 0 else max(state.interval_days + 1, _grow(state.interval_days, 1200))
        )
    elif rating is Rating.GOOD:
        interval = _good_interval(state)
    else:
        ease += 150
        if state.reps == 0:
            interval = 3
        elif state.reps == 1:
            interval = 6
        else:
            interval = _grow(state.interval_days, ease, 130)
        interval = max(interval, _good_interval(state) + 1)

    interval = min(MAX_INTERVAL_DAYS, interval)
    return CardState(state.reps + 1, interval, ease, lapses, today + timedelta(days=interval))


def _good_interval(state: CardState) -> int:
    if state.reps == 0:
        return 1
    if state.reps == 1:
        return 3
    return max(state.interval_days + 1, _grow(state.interval_days, state.ease))
