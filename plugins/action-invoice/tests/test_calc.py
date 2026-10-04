import pytest
from action_invoice.calc import (
    Line,
    cents_to_str,
    compute_totals,
    line_net_cents,
    milli_to_str,
    round_div,
)


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(5, 10, 1), (4, 10, 0), (15, 10, 2), (-5, 10, -1), (-4, 10, 0), (-15, 10, -2), (0, 7, 0)],
)
def test_round_div_rounds_half_away_from_zero(
    numerator: int, denominator: int, expected: int
) -> None:
    assert round_div(numerator, denominator) == expected


def test_line_net_uses_thousandths_of_quantity() -> None:
    # 2.5 hours at 80.00 EUR
    assert line_net_cents(Line(2500, 8000, 19)) == 20000
    # 0.333 hours at 100.00 EUR = 33.30 EUR
    assert line_net_cents(Line(333, 10000, 19)) == 3330
    # 0.005 at 1.00 EUR = 0.005 EUR -> rounds up to 0.01
    assert line_net_cents(Line(5, 100, 19)) == 1


def test_totals_compute_tax_per_rate_on_summed_net() -> None:
    # Three lines of 0.03 EUR: tax per line would be 0.01 each (0.03), tax on the sum is 0.02.
    lines = [Line(1000, 3, 19)] * 3

    totals = compute_totals(lines)

    assert totals.net_cents == 9
    assert totals.tax_cents == 2
    assert totals.gross_cents == 11


def test_totals_group_by_rate() -> None:
    totals = compute_totals([Line(1000, 10000, 19), Line(1000, 10000, 7)])

    assert [(g.tax_rate_percent, g.net_cents, g.tax_cents) for g in totals.groups] == [
        (7, 10000, 700),
        (19, 10000, 1900),
    ]
    assert totals.gross_cents == 22600


def test_exempt_forces_zero_tax() -> None:
    totals = compute_totals([Line(1000, 10000, 19)], exempt=True)

    assert totals.tax_cents == 0
    assert totals.gross_cents == 10000


def test_negative_lines_mirror_positive_ones() -> None:
    positive = compute_totals([Line(1500, 333, 19)])
    negative = compute_totals([Line(-1500, 333, 19)])

    assert negative.net_cents == -positive.net_cents
    assert negative.tax_cents == -positive.tax_cents


def test_formatting() -> None:
    assert cents_to_str(123456) == "1234.56"
    assert cents_to_str(-5) == "-0.05"
    assert milli_to_str(2500) == "2.5"
    assert milli_to_str(3000) == "3"
    assert milli_to_str(333) == "0.333"
