from dataclasses import replace
from datetime import date
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_listing_date, parse_salary
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import BaseScraper

BASE_URL = "https://www.hellojob.az"


def text_of(parent: Tag, selector: str) -> str | None:
    element = parent.select_one(selector)
    if element is None:
        return None
    return element.get_text(" ", strip=True) or None


def detail_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Read the label/value list on a vacancy page, e.g. {"Şəhər": "Bakı, Binə"}."""
    fields = {}
    for item in soup.select(".company__item__details li"):
        label, value = item.find("span"), item.find("p")
        if label and value:
            fields[label.get_text(strip=True)] = value.get_text(" ", strip=True)
    return fields


class HelloJobScraper(BaseScraper):
    source = "hellojob.az"
    start_urls = (f"{BASE_URL}/vakansiyalar",)
    max_pages = 5

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

        for card in soup.select("a.vacancies__body[href]"):
            button = card.select_one("[add-to-wishlist]")
            title = text_of(card, ".vacancies__title")
            if button is None or not button["add-to-wishlist"] or not title:
                continue

            salary_text = text_of(card, ".vacancies__price")
            salary_min, salary_max = parse_salary(salary_text)
            info = card.select(".vacancies__info__item")
            posted = info[-1].get_text(" ", strip=True) if info else None
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=button["add-to-wishlist"],
                    title=title,
                    company=text_of(card, ".vacancies__company") or "",
                    url=urljoin(BASE_URL, card["href"]),
                    published_on=parse_listing_date(posted, today),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                )
            )

        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        link = BeautifulSoup(text, "html.parser").select_one(".pagination a.next[href]")
        return urljoin(current_url, link["href"]) if link else None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        fields = detail_fields(soup)
        body = soup.select_one(".company__body .company__text")
        description = vacancy.description
        if body is not None:
            for promo in body.select('p:has(a[href*="whatsapp.com"], a[href*="t.me/"])'):
                promo.decompose()
            description = body.get_text("\n", strip=True)

        city = fields.get("Şəhər", "").split(",")[0].strip()
        return replace(
            vacancy,
            description=description,
            company=vacancy.company or text_of(soup, ".company__body a.vacancies__category") or "",
            location=vacancy.location or city or None,
            published_on=vacancy.published_on
            or parse_listing_date(fields.get("Yerləşmə tarixi"), self.today or date.today()),
        )
