import re
from dataclasses import asdict, replace
from datetime import date

from az_job_radar.analysis import analyze
from az_job_radar.models import Vacancy

URGENT_MARK = re.compile(r"\b(?:[tT][əƏeE][cC][iİI][lL][iİI]|urgent)\b[!:.]*", re.IGNORECASE)
EDGE_JUNK = " -–—|,.!*\"'"
EMAIL = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?:\+?994|\(?\b0)[\s(-]*\d{2}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b")


def clean_title(title: str) -> str:
    cleaned = URGENT_MARK.sub("", title)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(EDGE_JUNK)
    return cleaned or title.strip()


def remove_contacts(text: str) -> str:
    """We link to the original ad, so personal emails and phone numbers are not stored."""
    return PHONE.sub("[phone]", EMAIL.sub("[email]", text))


def dedupe(vacancies: list[Vacancy]) -> list[Vacancy]:
    newest: dict[str, Vacancy] = {}
    for vacancy in vacancies:
        current = newest.get(vacancy.uid)
        if current is None or (vacancy.published_on or date.min) > (
            current.published_on or date.min
        ):
            newest[vacancy.uid] = vacancy
    return list(newest.values())


def posting_date(published_on: date | None, today: date) -> date | None:
    """A date in the future is usually the application deadline, not the posting date."""
    if published_on is None or published_on > today:
        return None
    return published_on


def process(vacancies: list[Vacancy], today: date | None = None) -> list[Vacancy]:
    today = today or date.today()
    cleaned = []
    for vacancy in vacancies:
        title = clean_title(vacancy.title)
        description = remove_contacts(vacancy.description)
        analysis = analyze(title, description)
        cleaned.append(
            replace(
                vacancy,
                title=title,
                company=vacancy.company.strip(),
                description=description,
                published_on=posting_date(vacancy.published_on, today),
                **asdict(analysis),
            )
        )
    return dedupe(cleaned)
