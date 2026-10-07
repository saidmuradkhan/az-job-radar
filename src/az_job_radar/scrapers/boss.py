import json
from datetime import date
from decimal import Decimal

from az_job_radar.models import Vacancy
from az_job_radar.scrapers.base import BaseScraper, flight_data, flight_texts, html_to_text

BASE_URL = "https://boss.az"
SEARCH_URL = f"{BASE_URL}/search/vacancies"
# Top-level categories (IT, sales, finance, ...). Each page shows its newest 24 vacancies.
CATEGORY_IDS = (36, 37, 38, 40, 42, 43, 44, 46)
TEXT_FIELDS = ("description", "responsibilities", "requirements")


def preloaded_vacancies(text: str) -> list[dict]:
    data = flight_data(text)
    key = '"preloadedAds":'
    start = data.find(key)
    if start == -1:
        return []
    ads, _ = json.JSONDecoder().raw_decode(data, start + len(key))
    nodes = (ads.get("vacancies") or {}).get("nodes") or []

    texts = flight_texts(data)
    for node in nodes:
        for field in TEXT_FIELDS:
            if isinstance(node.get(field), str) and node[field].startswith("$"):
                node[field] = texts.get(node[field], "")
    return nodes


def amount(value) -> Decimal | None:
    return Decimal(str(value)) if value else None


class BossScraper(BaseScraper):
    source = "boss.az"
    start_urls = (SEARCH_URL, *(f"{SEARCH_URL}?categoryIds={id}" for id in CATEGORY_IDS))

    def parse_listing(self, text: str) -> list[Vacancy]:
        vacancies = []
        for node in preloaded_vacancies(text):
            title = (node.get("positionName") or "").strip()
            if not title or not node.get("id"):
                continue

            posted = node.get("createdAt") or node.get("bumpedAt")
            description = "\n".join(
                html_to_text(node[field]) for field in TEXT_FIELDS if node.get(field)
            )
            vacancies.append(
                Vacancy(
                    source=self.source,
                    external_id=node["id"],
                    title=title,
                    company=(node.get("name") or "").strip(),
                    url=f"{BASE_URL}/vacancies/{node['id']}",
                    location=node.get("location"),
                    published_on=date.fromisoformat(posted[:10]) if posted else None,
                    salary_min=amount(node.get("salaryFrom")),
                    salary_max=amount(node.get("salaryTo")),
                    description=description,
                )
            )
        return vacancies
