import re
from datetime import date
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_listing_date, parse_salary
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import BaseScraper

BASE_URL = "https://boss.az"
IT_CATEGORY_IDS = (66, 67, 68, 69, 70, 71, 72, 159)
VACANCY_ID = re.compile(r"/vacancies/(\d+)")


def field_text(card: Tag, name: str) -> str | None:
    element = card.select_one(f'[data-cy="{name}"]')
    if element is None:
        return None
    return element.get_text(" ", strip=True) or None


class BossScraper(BaseScraper):
    source = "boss.az"
    start_urls = tuple(
        f"{BASE_URL}/search/vacancies?categoryIds={category}" for category in IT_CATEGORY_IDS
    )

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        robots: RobotsPolicy | None = None,
        today: date | None = None,
    ) -> None:
        super().__init__(client, robots)
        self.today = today

    def parse_listing(self, text: str) -> list[Vacancy]:
        soup = BeautifulSoup(text, "html.parser")
        today = self.today or date.today()
        vacancies = []

        for card in soup.select('[data-cy="ad-card"]'):
            link = card.find_parent("a", href=True)
            match = VACANCY_ID.search(link["href"]) if link else None
            title = field_text(card, "ad-card-subtitle")
            if not match or not title:
                continue

            salary_min, salary_max = parse_salary(field_text(card, "ad-card-salary"))
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=field_text(card, "ad-card-title") or "",
                    url=urljoin(BASE_URL, link["href"]),
                    location=field_text(card, "ad-card-location"),
                    published_on=parse_listing_date(field_text(card, "ad-card-date"), today),
                    salary_min=salary_min,
                    salary_max=salary_max,
                )
            )

        return vacancies
