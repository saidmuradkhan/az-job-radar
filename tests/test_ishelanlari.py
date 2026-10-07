from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.ishelanlari import IshElanlariScraper

LISTING_URL = "https://ishelanlari.az/az/vacancies/"


def parse(read_fixture):
    return IshElanlariScraper().parse_listing(read_fixture("ishelanlari_listing.html"))


def test_parses_every_card(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 20
    assert len({v.uid for v in vacancies}) == 20


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "ishelanlari.az"
    assert first.external_id == "37237"
    assert first.title == "Gömrük işlərinə nəzarət üzrə kiçik mütəxəssis"
    assert first.company == "AzəriMed MMC"
    assert first.url.startswith("https://ishelanlari.az/az/vacancy/37237/")
    assert first.location == "Bakı"
    assert first.published_on == date(2026, 10, 4)
    assert (first.salary_min, first.salary_max) == (Decimal("600"), Decimal("700"))
    assert first.currency == "AZN"


def test_card_description_drops_dashes(read_fixture):
    description = parse(read_fixture)[0].description
    assert description.startswith("Vəzifə Öhdəlikləri:\n• Gömrükdən yüklərin")
    assert "\n-" not in description
    assert "Ətraflı" not in description


def test_next_page_url(read_fixture):
    scraper = IshElanlariScraper()
    html = read_fixture("ishelanlari_listing.html")
    assert scraper.next_page_url(html, LISTING_URL) == "https://ishelanlari.az/az/vacancies//0/20/"

    last_page = (
        '<ul><li class="page-item"><a href="/az/vacancies//0/0/">1</a></li>'
        '<li class="page-item active"><a href="/az/vacancies//0/20/">2</a></li></ul>'
    )
    assert scraper.next_page_url(last_page, LISTING_URL) is None


def test_detail_adds_requirements(read_fixture):
    scraper = IshElanlariScraper()
    vacancy = parse(read_fixture)[0]
    assert scraper.detail_url(vacancy) == vacancy.url

    detailed = scraper.parse_detail(read_fixture("ishelanlari_detail.html"), vacancy)
    assert detailed.title == vacancy.title
    assert detailed.salary_min == Decimal("600")
    assert "Vəzifə Öhdəlikləri:" in detailed.description
    assert "Namizədə tələblər\n• Ali və ya orta təhsil" in detailed.description
    assert "Redakta et" not in detailed.description


def test_detail_without_body_keeps_vacancy(read_fixture):
    vacancy = parse(read_fixture)[0]
    assert IshElanlariScraper().parse_detail("<html></html>", vacancy) is vacancy


def test_ignores_pages_without_cards():
    assert IshElanlariScraper().parse_listing("<html><body>Heç nə</body></html>") == []
