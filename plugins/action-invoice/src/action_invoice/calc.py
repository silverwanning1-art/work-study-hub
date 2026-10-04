"""Pure money arithmetic on integer cents. No floats anywhere.

Rounding: half away from zero. Net per line is rounded to cents; tax is computed once per
tax rate on the summed net amounts of that rate (not per line).
"""

from collections.abc import Iterable
from dataclasses import dataclass


def round_div(numerator: int, denominator: int) -> int:
    """Divide and round half away from zero."""
    sign = -1 if numerator < 0 else 1
    return sign * ((abs(numerator) * 2 + denominator) // (denominator * 2))


@dataclass(frozen=True)
class Line:
    """Input of the calculation for one invoice line."""

    quantity_milli: int
    unit_price_cents: int
    tax_rate_percent: int


@dataclass(frozen=True)
class TaxGroup:
    """Net and tax for one tax rate."""

    tax_rate_percent: int
    net_cents: int
    tax_cents: int


@dataclass(frozen=True)
class Totals:
    """Invoice totals in cents."""

    net_cents: int
    groups: list[TaxGroup]
    tax_cents: int
    gross_cents: int


def line_net_cents(line: Line) -> int:
    """Net amount of a line: quantity (in thousandths) times unit price, rounded to cents."""
    return round_div(line.quantity_milli * line.unit_price_cents, 1000)


def compute_totals(lines: Iterable[Line], exempt: bool = False) -> Totals:
    """Sum lines per tax rate. With ``exempt`` every line is taxed at 0 %."""
    net_by_rate: dict[int, int] = {}
    for line in lines:
        rate = 0 if exempt else line.tax_rate_percent
        net_by_rate[rate] = net_by_rate.get(rate, 0) + line_net_cents(line)
    groups = [
        TaxGroup(rate, net, round_div(net * rate, 100)) for rate, net in sorted(net_by_rate.items())
    ]
    net_total = sum(g.net_cents for g in groups)
    tax_total = sum(g.tax_cents for g in groups)
    return Totals(net_total, groups, tax_total, net_total + tax_total)


def cents_to_str(cents: int) -> str:
    """Format cents as a decimal string such as ``-1234.50``."""
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{whole}.{fraction:02d}"


def milli_to_str(milli: int) -> str:
    """Format thousandths as a decimal string without trailing zeros (``2.5``, ``3``)."""
    sign = "-" if milli < 0 else ""
    whole, fraction = divmod(abs(milli), 1000)
    text = f"{whole}.{fraction:03d}".rstrip("0").rstrip(".")
    return sign + text
