import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from az_job_radar.models import Vacancy
from az_job_radar.parsing import AZ_MONTHS, parse_currency, parse_listing_date, parse_salary
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import BaseScraper, find_job_posting

BASE_URL = "https://vakansiya.biz"
VACANCY_ID = re.compile(r"/az/jobs/(\d+)/")
SHORT_DATE = re.compile(r"(\d{1,2}) ([a-zəğıöüçş]{3}) (\d{4})")
SHORT_MONTHS = {
    "yan": "yanvar",
    "fev": "fevral",
    "mar": "mart",
    "apr": "aprel",
    "may": "may",
    "iyn": "iyun",
    "iyl": "iyul",
    "avq": "avqust",
    "sen": "sentyabr",
    "okt": "oktyabr",
    "noy": "noyabr",
    "dek": "dekabr",
}


def parse_card_date(text: str | None, today: date) -> date | None:
    """The site writes "Bugün" and short months like "25 sen 2026"."""
    text = (text or "").strip().lower().replace("bugün", "bu gün")
    match = SHORT_DATE.fullmatch(text)
    if match and match.group(2) in SHORT_MONTHS:
        day, month, year = match.groups()
        return date(int(year), AZ_MONTHS[SHORT_MONTHS[month]], int(day))
    return parse_listing_date(text, today)


def card_salary(card: Tag) -> str | None:
    for span in card.select("span.font-display"):
        text = span.get_text(" ", strip=True)
        if "AZN" in text or "USD" in text or "EUR" in text:
            return text
    return None


def split_company_and_city(card: Tag) -> tuple[str, str | None]:
    line = card.p.get_text(" ", strip=True) if card.p else ""
    company, _, place = line.partition("·")
    city = place.strip().removesuffix("Azərbaycan").strip(" ,")
    return company.strip(), city or None


def to_decimal(value) -> Decimal | None:
    return Decimal(str(value)) if value not in (None, "") else None


class VakansiyaBizScraper(BaseScraper):
    source = "vakansiya.biz"
    start_urls = (f"{BASE_URL}/az/jobs",)
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
        seen = set()

        for card in soup.select('a[href*="/jobs/"]'):
            match = VACANCY_ID.search(card["href"])
            title = card.h2.get_text(" ", strip=True) if card.h2 else ""
            if not match or not title or match.group(1) in seen:
                continue
            seen.add(match.group(1))

            company, city = split_company_and_city(card)
            salary_text = card_salary(card)
            salary_min, salary_max = parse_salary(salary_text)
            date_span = card.select_one("span.font-mono")
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=match.group(1),
                    title=title,
                    company=company,
                    url=urljoin(BASE_URL, card["href"]),
                    location=city,
                    published_on=parse_card_date(
                        date_span.get_text(strip=True) if date_span else None, today
                    ),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                )
            )

        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        soup = BeautifulSoup(text, "html.parser")
        for link in soup.find_all("a", href=True):
            if link.get_text(strip=True) == "Növbəti":
                return urljoin(current_url, link["href"])
        return None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        return vacancy.url

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        posting = find_job_posting(BeautifulSoup(text, "html.parser"))
        if not posting:
            return vacancy

        address = (posting.get("jobLocation") or {}).get("address") or {}
        salary = posting.get("baseSalary") or {}
        amount = salary.get("value") or {}
        posted = posting.get("datePosted")
        salary_min = to_decimal(amount.get("minValue"))
        salary_max = to_decimal(amount.get("maxValue"))
        has_salary = salary_min is not None or salary_max is not None
        return replace(
            vacancy,
            description=(posting.get("description") or "").replace("\r\n", "\n").strip(),
            company=vacancy.company or (posting.get("hiringOrganization") or {}).get("name", ""),
            location=vacancy.location or address.get("addressLocality"),
            published_on=date.fromisoformat(posted[:10]) if posted else vacancy.published_on,
            salary_min=salary_min if has_salary else vacancy.salary_min,
            salary_max=salary_max if has_salary else vacancy.salary_max,
            currency=salary.get("currency") or vacancy.currency,
        )
