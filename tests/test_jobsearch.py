import json
from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.jobsearch import JobSearchScraper


def test_parses_items(read_fixture):
    vacancies = JobSearchScraper().parse_listing(read_fixture("jobsearch_page.json"))
    assert len(vacancies) == 12

    first = vacancies[0]
    assert first.source == "jobsearch.az"
    assert first.external_id == "152916"
    assert first.company == "Knight Academy"
    assert first.url.startswith("https://jobsearch.az/vacancies/knight-academy-")
    assert first.published_on == date(2026, 10, 3)
    assert first.salary_min == first.salary_max == Decimal("1000")


def test_empty_salary_becomes_none(read_fixture):
    second = JobSearchScraper().parse_listing(read_fixture("jobsearch_page.json"))[1]
    assert second.salary_min is None
    assert second.salary_max is None


def test_hidden_company_is_blank():
    payload = {
        "items": [
            {
                "id": 1,
                "title": "Backend Developer",
                "slug": "backend-developer-1",
                "hide_company": True,
                "company": {"title": "Secret LLC"},
                "salary": "",
                "created_at": "2026-10-01T00:00:00+04:00",
            }
        ]
    }
    vacancy = JobSearchScraper().parse_listing(json.dumps(payload))[0]
    assert vacancy.company == ""


def test_next_page_url(read_fixture):
    scraper = JobSearchScraper()
    next_url = scraper.next_page_url(read_fixture("jobsearch_page.json"), "")
    assert "page=2" in next_url
    assert scraper.next_page_url(json.dumps({"items": []}), "") is None
