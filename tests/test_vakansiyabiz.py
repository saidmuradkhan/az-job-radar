from datetime import date
from decimal import Decimal

from az_job_radar.models import Vacancy
from az_job_radar.scrapers.vakansiyabiz import VakansiyaBizScraper, parse_card_date

TODAY = date(2026, 10, 7)


def parse(read_fixture):
    scraper = VakansiyaBizScraper(today=TODAY)
    return scraper.parse_listing(read_fixture("vakansiyabiz_listing.html"))


def test_parses_every_card_once(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 25
    assert len({v.uid for v in vacancies}) == 25


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "vakansiya.biz"
    assert first.external_id == "20241"
    assert first.title == "Müşahidə kameraları üzrə nəzarətçi"
    assert first.company == "Siyəzən Broyler ASC"
    assert first.url == "https://vakansiya.biz/az/jobs/20241/musahide-kameralari-uzre-nezaretci"
    assert first.location == "Siyəzən"
    assert first.published_on == date(2026, 10, 3)
    assert (first.salary_min, first.salary_max) == (Decimal("700"), Decimal("800"))
    assert first.currency == "AZN"


def test_handles_missing_salary_city_and_dates(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert by_id["20148"].published_on == date(2026, 9, 25)
    assert by_id["20352"].published_on == TODAY
    assert by_id["20349"].published_on == date(2026, 10, 6)
    assert by_id["20352"].salary_min is None
    assert by_id["20352"].salary_max is None
    assert by_id["20165"].salary_min == by_id["20165"].salary_max == Decimal("800")
    assert by_id["20334"].company == "Birbank"
    assert by_id["20334"].location is None


def test_parses_short_month_dates():
    assert parse_card_date("1 iyl 2026", TODAY) == date(2026, 7, 1)
    assert parse_card_date("Bugün", TODAY) == TODAY
    assert parse_card_date(None, TODAY) is None


def test_next_page_url(read_fixture):
    scraper = VakansiyaBizScraper()
    current = "https://vakansiya.biz/az/jobs"
    next_url = scraper.next_page_url(read_fixture("vakansiyabiz_listing.html"), current)
    assert next_url == "https://vakansiya.biz/az/jobs?page=2"
    assert scraper.next_page_url("<html><body>1 / 1</body></html>", current) is None


def test_detail_adds_description_and_fills_gaps(read_fixture):
    scraper = VakansiyaBizScraper()
    vacancy = Vacancy(
        source="vakansiya.biz",
        external_id="20148",
        title="Dayanacaq nəzarətçisi",
        company="",
        url="https://vakansiya.biz/az/jobs/20148/dayanacaq-nezaretcisi",
    )
    assert scraper.detail_url(vacancy) == vacancy.url

    detailed = scraper.parse_detail(read_fixture("vakansiyabiz_detail.html"), vacancy)
    assert detailed.description.startswith("Vəzifə Öhdəlikləri:")
    assert "Sürücülük vəsiqəsi" in detailed.description
    assert "\r" not in detailed.description
    assert detailed.company == "Çinar Park QSC"
    assert detailed.location == "Bakı"
    assert detailed.published_on == date(2026, 9, 25)
    assert (detailed.salary_min, detailed.salary_max) == (Decimal("550"), Decimal("600"))


def test_detail_without_job_posting_keeps_vacancy(read_fixture):
    first = parse(read_fixture)[0]
    assert VakansiyaBizScraper().parse_detail("<html></html>", first) == first


def test_ignores_pages_without_cards():
    assert VakansiyaBizScraper().parse_listing("<html><body>Heç nə</body></html>") == []
