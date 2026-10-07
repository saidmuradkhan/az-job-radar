import re
from dataclasses import replace
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_salary
from az_job_radar.scrapers.base import BaseScraper

BASE_URL = "https://ishelanlari.az"
VACANCY_ID = re.compile(r"/vacancy/(\d+)/")


def text_of(element: Tag | None) -> str:
    return element.get_text(" ", strip=True) if element else ""


def parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None


def join_lines(tags: list[Tag]) -> str:
    """Every paragraph on this site starts with a dash, so drop it along with empty lines."""
    lines = (" ".join(tag.get_text(" ").split()).lstrip("-").strip() for tag in tags)
    return "\n".join(line for line in lines if line)


class IshElanlariScraper(BaseScraper):
    source = "ishelanlari.az"
    start_urls = (f"{BASE_URL}/az/vacancies/",)
    max_pages = 2

    def parse_listing(self, text: str) -> list[Vacancy]:
        soup = BeautifulSoup(text, "html.parser")
        vacancies = []

        for card in soup.select("div.vac_item"):
            link = card.select_one("a.over_link[href]")
            match = VACANCY_ID.search(link["href"]) if link else None
            title = text_of(card.select_one("h2"))
            if not match or not title:
                continue

            salary_text = text_of(card.select_one("h4"))
            salary_min, salary_max = parse_salary(salary_text)
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=text_of(card.select_one("a.comp_name")),
                    url=urljoin(BASE_URL, link["href"]),
                    location=text_of(card.select_one("footer span")) or None,
                    published_on=parse_date(text_of(card.select_one("time"))),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                    description=join_lines(card.find_all("p")),
                )
            )

        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        soup = BeautifulSoup(text, "html.parser")
        active = soup.select_one("li.page-item.active")
        following = active.find_next_sibling("li") if active else None
        link = following.select_one("a[href]") if following else None
        return urljoin(current_url, link["href"]) if link else None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        # The listing card leaves out the candidate requirements.
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        body = soup.select_one(".row.job_desc")
        if body is None:
            return vacancy

        return replace(
            vacancy,
            title=text_of(soup.select_one("h1.text_prime")) or vacancy.title,
            description=join_lines(body.find_all(["h5", "p"])),
        )
