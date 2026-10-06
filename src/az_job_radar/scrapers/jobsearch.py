import json
from datetime import date

from az_job_radar.models import Vacancy
from az_job_radar.parsing import parse_currency, parse_salary
from az_job_radar.scrapers.base import BaseScraper

API_URL = "https://jobsearch.az/api-az/vacancies-az?hl=az"
VACANCY_URL = "https://jobsearch.az/vacancies/{slug}"


class JobSearchScraper(BaseScraper):
    source = "jobsearch.az"
    start_urls = (API_URL,)
    request_headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
    max_pages = 3

    def parse_listing(self, text: str) -> list[Vacancy]:
        vacancies = []
        for item in json.loads(text).get("items", []):
            title = (item.get("title") or "").strip()
            if not title or not item.get("id"):
                continue

            company = item.get("company") or {}
            created_at = item.get("created_at")
            salary_text = item.get("salary")
            salary_min, salary_max = parse_salary(salary_text)
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=str(item["id"]),
                    title=title,
                    company="" if item.get("hide_company") else company.get("title", ""),
                    url=VACANCY_URL.format(slug=item.get("slug") or item["id"]),
                    published_on=date.fromisoformat(created_at[:10]) if created_at else None,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=parse_currency(salary_text),
                )
            )
        return vacancies

    def next_page_url(self, text: str, current_url: str) -> str | None:
        return json.loads(text).get("next")
