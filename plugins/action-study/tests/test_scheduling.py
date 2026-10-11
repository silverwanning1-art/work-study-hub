from datetime import date, timedelta

import pytest
from action_study.scheduling import MAX_INTERVAL_DAYS, MIN_EASE, CardState, Rating, schedule

TODAY = date(2026, 11, 3)


def state(reps: int = 0, interval: int = 0, ease: int = 2500, lapses: int = 0) -> CardState:
    return CardState(reps, interval, ease, lapses, TODAY)


def test_new_card_good_then_good_then_grows() -> None:
    first = schedule(state(), Rating.GOOD, TODAY)
    assert (first.reps, first.interval_days, first.due) == (1, 1, TODAY + timedelta(days=1))
    second = schedule(first, Rating.GOOD, TODAY)
    assert second.interval_days == 3
    third = schedule(second, Rating.GOOD, TODAY)
    assert third.interval_days == 8  # 3 * 2.5 = 7.5 rounds to 8
    assert third.due == TODAY + timedelta(days=8)


def test_again_resets_and_counts_a_lapse() -> None:
    result = schedule(state(reps=5, interval=30, ease=2500), Rating.AGAIN, TODAY)
    assert (result.reps, result.interval_days, result.lapses) == (0, 1, 1)
    assert result.ease == 2300
    assert result.due == TODAY + timedelta(days=1)


def test_ease_never_drops_below_minimum() -> None:
    result = state(reps=3, interval=10, ease=MIN_EASE + 50)
    for _ in range(5):
        result = schedule(result, Rating.AGAIN, TODAY)
    assert result.ease == MIN_EASE
    assert schedule(state(reps=3, interval=10, ease=MIN_EASE), Rating.HARD, TODAY).ease == MIN_EASE


def test_hard_grows_slowly_and_lowers_ease() -> None:
    result = schedule(state(reps=3, interval=10, ease=2500), Rating.HARD, TODAY)
    assert result.interval_days == 12
    assert result.ease == 2350


def test_hard_on_new_card_is_one_day() -> None:
    assert schedule(state(), Rating.HARD, TODAY).interval_days == 1


def test_easy_is_longer_than_good_and_raises_ease() -> None:
    base = state(reps=3, interval=10, ease=2500)
    good = schedule(base, Rating.GOOD, TODAY)
    easy = schedule(base, Rating.EASY, TODAY)
    assert easy.interval_days > good.interval_days
    assert easy.ease == 2650


@pytest.mark.parametrize(("reps", "expected"), [(0, 3), (1, 6)])
def test_easy_on_young_cards(reps: int, expected: int) -> None:
    assert schedule(state(reps=reps, interval=1), Rating.EASY, TODAY).interval_days == expected


@pytest.mark.parametrize("rating", list(Rating))
def test_interval_is_capped(rating: Rating) -> None:
    result = schedule(state(reps=9, interval=MAX_INTERVAL_DAYS), rating, TODAY)
    assert result.interval_days <= MAX_INTERVAL_DAYS


@pytest.mark.parametrize("rating", [Rating.HARD, Rating.GOOD, Rating.EASY])
def test_passing_rating_never_shrinks_a_mature_interval(rating: Rating) -> None:
    result = schedule(state(reps=4, interval=20, ease=1300), rating, TODAY)
    assert result.interval_days > 20
