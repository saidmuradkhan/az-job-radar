import json
import re
from dataclasses import replace
from datetime import date
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from az_job_radar.models import Vacancy
from az_job_radar.scrapers.base import BaseScraper, flight_data

BASE_URL = "https://jobs.glorri.az"
LISTING_URL = BASE_URL + "/?page={page}"
VACANCY_URL = BASE_URL + "/vacancies/{company}/{slug}"


def vacancy_entities(text: str) -> list[dict]:
    """Return the main vacancy list; smaller lists on the page belong to carousels."""
    data = flight_data(text)
    decoder = json.JSONDecoder()
    best: dict = {}
    for match in re.finditer(r'"vacancies":\{', data):
        try:
            found, _ = decoder.raw_decode(data, match.end() - 1)
        except json.JSONDecodeError:
            continue
        if found.get("totalCount", 0) > best.get("totalCount", -1):
            best = found
    return best.get("entities", [])


def current_page(url: str) -> int:
    pages = parse_qs(urlparse(url).query).get("page", ["1"])
    return int(pages[0]) if pages[0].isdigit() else 1


class GlorriScraper(BaseScraper):
    source = "jobs.glorri.az"
    start_urls = (LISTING_URL.format(page=1),)
    max_pages = 5

    def parse_listing(self, text: str) -> list[Vacancy]:
        vacancies = []
        for item in vacancy_entities(text):
            title = (item.get("title") or "").strip()
            slug = item.get("slug")
            company = item.get("company") or {}
            if not title or not slug or not company.get("slug"):
                continue

            location = item.get("location") or ""
            posted = item.get("postedDate")
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=slug,
                    title=title,
                    company=company.get("name") or "",
                    url=VACANCY_URL.format(company=company["slug"], slug=slug),
                    location=location.split(",")[0].strip() or None,
                    published_on=date.fromisoformat(posted[:10]) if posted else None,
                )
            )
        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        page = current_page(current_url)
        if page >= self.max_pages or not vacancy_entities(text):
            return None
        return LISTING_URL.format(page=page + 1)

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        body = soup.select_one("div.grid.grid-cols-1 > div.sm\\:col-span-8")
        if body is None:
            return vacancy
        lines = [" ".join(block.get_text().split()) for block in body.find_all(["h3", "p", "li"])]
        description = "\n".join(line for line in lines if line)
        return replace(vacancy, description=description or body.get_text("\n", strip=True))
