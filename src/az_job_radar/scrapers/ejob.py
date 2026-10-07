import re
from dataclasses import replace
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_salary
from az_job_radar.scrapers.base import BaseScraper, find_job_posting, html_to_text

BASE_URL = "https://ejob.az"
VACANCY_ID = re.compile(r"/is-elani/(\d+)")


def text_of(card: Tag, selector: str) -> str | None:
    element = card.select_one(selector)
    if element is None:
        return None
    return element.get_text(" ", strip=True) or None


def city_of(card: Tag) -> str | None:
    """The second "city" block reads "Bakı 07-10-26 501"; only the first part is the city."""
    blocks = card.select("div.city")
    if len(blocks) < 2:
        return None
    return next(blocks[1].stripped_strings, None)


class EJobScraper(BaseScraper):
    source = "ejob.az"
    start_urls = (f"{BASE_URL}/is-elanlari/",)
    max_pages = 5

    def parse_listing(self, text: str) -> list[Vacancy]:
        soup = BeautifulSoup(text, "html.parser")
        vacancies = []

        for card in soup.select("div.list ul > li"):
            link = card.select_one('a[href^="/is-elani/"]')
            match = VACANCY_ID.match(link["href"]) if link else None
            title = link.get_text(" ", strip=True).removesuffix(" işi") if link else ""
            if not match or not title:
                continue

            salary_text = text_of(card, "div.salary")
            salary_min, salary_max = parse_salary(salary_text)
            # The card date can be a paid "bump", so the real one comes from the detail page.
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=text_of(card, "div.company") or "",
                    url=urljoin(BASE_URL, link["href"]),
                    location=city_of(card),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                )
            )

        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        link = BeautifulSoup(text, "html.parser").select_one("a.to_forward[href]")
        return urljoin(current_url, link["href"]) if link else None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        posting = find_job_posting(soup)
        table = soup.select_one("table.description")
        company = (posting.get("hiringOrganization") or {}).get("name")
        posted = posting.get("datePosted")
        return replace(
            vacancy,
            description=html_to_text(str(table)) if table else vacancy.description,
            company=vacancy.company or company or "",
            published_on=date.fromisoformat(posted[:10]) if posted else vacancy.published_on,
        )
