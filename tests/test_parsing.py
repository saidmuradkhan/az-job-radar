from datetime import date
from decimal import Decimal

import pytest

from az_job_radar.parsing import parse_currency, parse_listing_date, parse_salary

TODAY = date(2026, 10, 4)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1000 - 1200 ₼", (Decimal("1000"), Decimal("1200"))),
        ("1000 ₼ / ayda", (Decimal("1000"), Decimal("1000"))),
        ("2 500 - 3 000 AZN", (Decimal("2500"), Decimal("3000"))),
        ("2000 ₼-dək", (None, Decimal("2000"))),
        ("1500 AZN-dən", (Decimal("1500"), None)),
        ("3000 - 2000", (Decimal("2000"), Decimal("3000"))),
        ("₼ / ayda", (None, None)),
        ("Razılaşma ilə", (None, None)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_salary(text, expected):
    assert parse_salary(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bu gün, 10:36", date(2026, 10, 4)),
        ("Dünən, 18:00", date(2026, 10, 3)),
        ("2 gün əvvəl", date(2026, 10, 2)),
        ("26 sentyabr 2026, 09:04", date(2026, 9, 26)),
        ("7 Sentyabr 2026", date(2026, 9, 7)),
        ("sabah", None),
        (None, None),
    ],
)
def test_parse_listing_date(text, expected):
    assert parse_listing_date(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1000 - 1200 ₼", "AZN"),
        ("1500 AZN", "AZN"),
        ("2000 $", "USD"),
        ("2000 USD", "USD"),
        ("1800 €", "EUR"),
        ("Razılaşma ilə", "AZN"),
        (None, "AZN"),
    ],
)
def test_parse_currency(text, expected):
    assert parse_currency(text) == expected
