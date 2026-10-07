from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.boss import BossScraper


def parse(read_fixture):
    return BossScraper().parse_listing(read_fixture("boss_search.html"))


def test_parses_every_vacancy_on_the_page(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 24
    assert len({v.uid for v in vacancies}) == 24


def test_maps_vacancy_fields(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    agent = by_id["274066"]

    assert agent.source == "boss.az"
    assert agent.title == "Daşınmaz əmlak agenti"
    assert agent.company == "Alo Estate"
    assert agent.url == "https://boss.az/vacancies/274066"
    assert agent.location == "Bakı"
    assert agent.published_on == date(2026, 10, 7)
    assert (agent.salary_min, agent.salary_max) == (Decimal("2500"), Decimal("5000"))


def test_description_comes_from_the_page_data(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}

    assert "Əmlak Məsləhətçisi" in by_id["274066"].description
    assert "&uuml;" not in by_id["274066"].description
    assert "ali təhsil" in by_id["274170"].description.lower()


def test_long_texts_do_not_run_into_each_other(read_fixture):
    for vacancy in parse(read_fixture):
        assert ":T" not in vacancy.description


def test_searches_every_top_category():
    urls = BossScraper.start_urls
    assert urls[0] == "https://boss.az/search/vacancies"
    assert "https://boss.az/search/vacancies?categoryIds=38" in urls


def test_ignores_pages_without_data():
    assert BossScraper().parse_listing("<html><body>Heç nə</body></html>") == []
