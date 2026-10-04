from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.boss import BossScraper


def parse(read_fixture):
    scraper = BossScraper(today=date(2026, 10, 4))
    return scraper.parse_listing(read_fixture("boss_listing.html"))


def test_parses_every_card(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 15
    assert len({v.uid for v in vacancies}) == 15


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "boss.az"
    assert first.external_id == "273950"
    assert first.title == "Baş texnik"
    assert first.company == "LifeGuard"
    assert first.url == "https://boss.az/vacancies/273950"
    assert first.location == "Bakı"
    assert first.published_on == date(2026, 10, 4)
    assert (first.salary_min, first.salary_max) == (Decimal("1000"), Decimal("1200"))


def test_handles_missing_salary_and_old_dates(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert by_id["273837"].salary_min is None
    assert by_id["273837"].salary_max is None
    assert by_id["272869"].published_on == date(2026, 9, 7)


def test_ignores_pages_without_cards():
    assert BossScraper().parse_listing("<html><body>Heç nə</body></html>") == []
