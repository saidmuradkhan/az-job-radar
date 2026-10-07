from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.oneis import OneIsScraper

PAGE_URL = "https://www.1is.az/allvacancy?page=1"


def parse(read_fixture):
    return OneIsScraper().parse_listing(read_fixture("oneis_listing.html"))


def test_skips_premium_cards(read_fixture):
    html = read_fixture("oneis_listing.html")
    assert html.count('class="premium-badge"') == 3
    vacancies = OneIsScraper().parse_listing(html)
    assert len(vacancies) == 30
    assert len({v.uid for v in vacancies}) == 30


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "1is.az"
    assert first.external_id == "23520"
    assert first.title.startswith("Əməliyyat Risklərinin")
    assert first.company == "Rabitə Bank"
    assert first.url == "https://www.1is.az/vacancy/23520"
    assert first.published_on == date(2026, 10, 2)
    assert first.salary_min is None


def test_next_page_url(read_fixture):
    scraper = OneIsScraper()
    assert scraper.next_page_url(read_fixture("oneis_listing.html"), PAGE_URL) == (
        "https://www.1is.az/allvacancy?page=2"
    )
    assert scraper.next_page_url("<html></html>", PAGE_URL) is None


def test_detail_adds_location_and_description(read_fixture):
    scraper = OneIsScraper()
    vacancy = next(v for v in parse(read_fixture) if v.external_id == "23506")
    assert scraper.detail_url(vacancy) == "https://www.1is.az/vacancy/23506"

    detailed = scraper.parse_detail(read_fixture("oneis_detail.html"), vacancy)
    assert detailed.title == "Aşpaz köməkçisi"
    assert detailed.location == "Bakı"
    assert detailed.company == "TAIS IKF MMC"
    assert detailed.description.startswith("İş rejimi: Tam iş vaxtı\nTəcrübə: 1 ildən 3 ilə")
    assert "Gündəlik menyuya uyğun yeməklərin hazırlanması" in detailed.description
    assert "Müraciət et" not in detailed.description
    assert detailed.salary_min is None


def test_detail_reads_salary_box(read_fixture):
    html = read_fixture("oneis_detail.html").replace("Müsahibə əsasında", "1500 AZN", 1)
    vacancy = parse(read_fixture)[0]
    detailed = OneIsScraper().parse_detail(html, vacancy)
    assert detailed.salary_min == detailed.salary_max == Decimal("1500")


def test_detail_without_header_keeps_vacancy(read_fixture):
    vacancy = parse(read_fixture)[0]
    assert OneIsScraper().parse_detail("<html></html>", vacancy) is vacancy


def test_ignores_pages_without_cards():
    assert OneIsScraper().parse_listing("<html><body>Heç nə</body></html>") == []
