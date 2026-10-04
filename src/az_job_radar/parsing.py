import re
from datetime import date, timedelta
from decimal import Decimal

AZ_MONTHS = {
    "yanvar": 1,
    "fevral": 2,
    "mart": 3,
    "aprel": 4,
    "may": 5,
    "iyun": 6,
    "iyul": 7,
    "avqust": 8,
    "sentyabr": 9,
    "oktyabr": 10,
    "noyabr": 11,
    "dekabr": 12,
}

NUMBER_PATTERN = re.compile(r"\d+(?:[  ]\d{3})*")
UPPER_BOUND_WORDS = ("dək", "dek", "qədər", "kimi")
LOWER_BOUND_WORDS = ("dən", "dan", "başlayaraq")


def parse_salary(text: str | None) -> tuple[Decimal | None, Decimal | None]:
    if not text:
        return None, None

    numbers = [Decimal(re.sub(r"\s", "", n)) for n in NUMBER_PATTERN.findall(text)]
    if not numbers:
        return None, None
    if len(numbers) >= 2:
        low, high = sorted(numbers[:2])
        return low, high

    lowered = text.lower()
    if any(word in lowered for word in UPPER_BOUND_WORDS):
        return None, numbers[0]
    if any(word in lowered for word in LOWER_BOUND_WORDS):
        return numbers[0], None
    return numbers[0], numbers[0]


def parse_listing_date(text: str | None, today: date) -> date | None:
    if not text:
        return None

    lowered = text.strip().lower()
    if lowered.startswith("bu gün"):
        return today
    if lowered.startswith("dünən"):
        return today - timedelta(days=1)

    days_ago = re.match(r"(\d+)\s+gün\s+əvvəl", lowered)
    if days_ago:
        return today - timedelta(days=int(days_ago.group(1)))

    full_date = re.match(r"(\d{1,2})\s+([a-zəğıöüçş]+)\s+(\d{4})", lowered)
    if full_date and full_date.group(2) in AZ_MONTHS:
        day, month, year = full_date.groups()
        return date(int(year), AZ_MONTHS[month], int(day))

    return None
