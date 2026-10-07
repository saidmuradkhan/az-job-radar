import re
from dataclasses import asdict, replace
from datetime import date

from az_job_radar.analysis import analyze
from az_job_radar.models import Vacancy

URGENT_MARK = re.compile(r"\b(?:[tT][əƏeE][cC][iİI][lL][iİI]|urgent)\b[!:.]*", re.IGNORECASE)
EDGE_JUNK = " -–—|,.!*\"'"


def clean_title(title: str) -> str:
    cleaned = URGENT_MARK.sub("", title)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(EDGE_JUNK)
    return cleaned or title.strip()


def dedupe(vacancies: list[Vacancy]) -> list[Vacancy]:
    newest: dict[str, Vacancy] = {}
    for vacancy in vacancies:
        current = newest.get(vacancy.uid)
        if current is None or (vacancy.published_on or date.min) > (
            current.published_on or date.min
        ):
            newest[vacancy.uid] = vacancy
    return list(newest.values())


def process(vacancies: list[Vacancy]) -> list[Vacancy]:
    cleaned = []
    for vacancy in vacancies:
        title = clean_title(vacancy.title)
        analysis = analyze(title, vacancy.description)
        cleaned.append(
            replace(vacancy, title=title, company=vacancy.company.strip(), **asdict(analysis))
        )
    return dedupe(cleaned)
