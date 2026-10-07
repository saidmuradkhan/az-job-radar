import json
import re
from dataclasses import replace
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_listing_date
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import BaseScraper, html_to_text

BASE_URL = "https://position.az/"
VACANCY_ID = re.compile(r"/vacancy/[^/]*?-(\d+)$")
DOTTED_DATE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_row_date(cell: Tag | None, today: date) -> date | None:
    if cell is None:
        return None
    text = cell.get_text(" ", strip=True).replace("★ Premium", "").strip()
    match = DOTTED_DATE.search(text)
    if match:
        return datetime.strptime(match.group(), "%d.%m.%Y").date()
    return parse_listing_date(text, today)


def city_names(soup: BeautifulSoup) -> dict[str, str]:
    return {
        option["value"]: option.get_text(strip=True)
        for option in soup.select("select#city option")
        if option.get("value")
    }


def row_city(row: Tag, cities: dict[str, str]) -> str | None:
    try:
        ids = json.loads(row.get("data-city") or "[]")
    except json.JSONDecodeError:
        return None
    names = [cities[str(city_id)] for city_id in ids if str(city_id) in cities]
    return ", ".join(names) or None


def select_text(soup: BeautifulSoup, selector: str) -> str | None:
    element = soup.select_one(selector)
    if element is None:
        return None
    return element.get_text(" ", strip=True) or None


def detail_city(soup: BeautifulSoup) -> str | None:
    label = soup.find("b", string="Şəhər:")
    if label is None:
        return None
    return ", ".join(span.get_text(strip=True) for span in label.parent.select("span")) or None


class PositionScraper(BaseScraper):
    source = "position.az"
    start_urls = (BASE_URL,)
    max_pages = 1

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
        cities = city_names(soup)
        vacancies = []

        for row in soup.select("tbody.grid > tr"):
            link = row.select_one("td[title] a[href]")
            match = VACANCY_ID.search(link["href"]) if link else None
            title = link.get_text(" ", strip=True) if link else ""
            if not match or not title:
                continue

            company = row.select_one("a.vacancy-row p")
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=company.get_text(" ", strip=True) if company else "",
                    url=link["href"],
                    location=row_city(row, cities),
                    published_on=parse_row_date(row.select_one("td.vacancy-duration"), today),
                )
            )

        return vacancies

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        body = soup.select_one(".vacancy-text.vacancy-az")
        dates = ISO_DATE.findall(select_text(soup, ".vacancy-date") or "")
        return replace(
            vacancy,
            title=select_text(soup, ".vacancy-header .vacancy-title.vacancy-az") or vacancy.title,
            company=select_text(soup, ".vacancy-company-header-title") or vacancy.company,
            location=vacancy.location or detail_city(soup),
            published_on=date.fromisoformat(dates[0]) if dates else vacancy.published_on,
            description=html_to_text(str(body)) if body else vacancy.description,
        )
