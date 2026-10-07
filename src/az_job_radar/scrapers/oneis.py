import re
from dataclasses import replace
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_salary
from az_job_radar.scrapers.base import BaseScraper

BASE_URL = "https://www.1is.az"
VACANCY_ID = re.compile(r"/vacancy/(\d+)")
FACT_LABELS = ("İş rejimi", "Təcrübə")


def text_of(element: Tag | None) -> str:
    return element.get_text(" ", strip=True) if element else ""


def parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        return None


class OneIsScraper(BaseScraper):
    source = "1is.az"
    start_urls = (f"{BASE_URL}/allvacancy?page=1",)
    max_pages = 3

    def parse_listing(self, text: str) -> list[Vacancy]:
        soup = BeautifulSoup(text, "html.parser")
        vacancies = []

        for card in soup.select("div.vac-card"):
            # Premium cards are repeated on every page, the regular ones follow them.
            if card.select_one(".premium-badge"):
                continue
            link = card.select_one("a.vac-name[href]")
            match = VACANCY_ID.search(link["href"]) if link else None
            title = text_of(link)
            if not match or not title:
                continue

            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=text_of(card.select_one("a.comp-link")),
                    url=urljoin(BASE_URL, link["href"]),
                    published_on=parse_date(text_of(card.select_one("p.vac-time"))),
                )
            )

        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        link = BeautifulSoup(text, "html.parser").select_one('a[rel="next"][href]')
        return urljoin(current_url, link["href"]) if link else None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        soup = BeautifulSoup(text, "html.parser")
        header = soup.select_one("section.header-info")
        if header is None:
            return vacancy

        info = {}
        for box in soup.select("section.info-boxs [class^=box-info-text]"):
            paragraphs = [text_of(p) for p in box.find_all("p")]
            if len(paragraphs) >= 2 and paragraphs[1] not in ("", "-"):
                info[paragraphs[0]] = paragraphs[1]

        facts = [f"{label}: {info[label]}" for label in FACT_LABELS if label in info]
        body = [
            container.get_text("\n", strip=True)
            for container in soup.select(".position-instructions-container")
        ]
        salary_text = info.get("Maaş")
        salary_min, salary_max = parse_salary(salary_text)

        return replace(
            vacancy,
            title=text_of(header.select_one("h2")) or vacancy.title,
            location=text_of(header.select_one('a[href*="city="]')) or vacancy.location,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=parse_currency(salary_text),
            description="\n".join(facts + body),
        )
