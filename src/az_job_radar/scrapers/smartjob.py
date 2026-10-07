from dataclasses import replace
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_salary
from az_job_radar.scrapers.base import BaseScraper, find_job_posting, html_to_text

BASE_URL = "https://smartjob.az"


def text_of(card: Tag, selector: str) -> str | None:
    element = card.select_one(selector)
    if element is None:
        return None
    return element.get_text(" ", strip=True) or None


def city_of(posting: dict) -> str | None:
    place = posting.get("jobLocation") or {}
    if isinstance(place, list):
        place = place[0] if place else {}
    return (place.get("address") or {}).get("addressLocality")


def parse_day(text: str | None) -> date | None:
    try:
        return datetime.strptime(text or "", "%d.%m.%Y").date()
    except ValueError:
        return None


class SmartJobScraper(BaseScraper):
    source = "smartjob.az"
    # Only the newest 20 are on the page; "show more" goes through the blocked /api/.
    start_urls = (f"{BASE_URL}/vakansiyalar",)

    def parse_listing(self, text: str) -> list[Vacancy]:
        soup = BeautifulSoup(text, "html.parser")
        vacancies = []

        for card in soup.select("article.job-row"):
            external_id = card.get("id", "").removeprefix("vacancy-")
            link = card.select_one("h3 > a[href]")
            title = link.get_text(" ", strip=True) if link else ""
            if not external_id.isdigit() or not title:
                continue

            salary_text = text_of(card, ".job-salary-highlight strong")
            salary_min, salary_max = parse_salary(salary_text)
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=external_id,
                    title=title,
                    company=text_of(card, ".job-row-main > p") or "",
                    url=urljoin(BASE_URL, link["href"]),
                    location=text_of(card, ".job-facts span"),
                    published_on=parse_day(text_of(card, ".job-row-side-meta small")),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                )
            )

        return vacancies

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        posting = find_job_posting(BeautifulSoup(text, "html.parser"))
        if not posting:
            return vacancy

        company = (posting.get("hiringOrganization") or {}).get("name")
        posted = posting.get("datePosted")
        return replace(
            vacancy,
            description=html_to_text(posting.get("description") or ""),
            company=vacancy.company or company or "",
            location=vacancy.location or city_of(posting),
            published_on=date.fromisoformat(posted[:10]) if posted else vacancy.published_on,
        )
