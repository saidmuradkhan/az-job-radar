from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.hellojob import HelloJobScraper

TODAY = date(2026, 10, 7)


def parse(read_fixture):
    return HelloJobScraper(today=TODAY).parse_listing(read_fixture("hellojob_listing.html"))


def test_parses_every_card(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 80
    assert len({v.uid for v in vacancies}) == 80


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "hellojob.az"
    assert first.external_id == "16757558"
    assert first.title == "Administrator"
    assert first.company == "Tahiroğlu İnşaat MMC"
    assert first.url == "https://www.hellojob.az/vakansiya/administrator-16757558"
    assert first.published_on == TODAY
    assert (first.salary_min, first.salary_max) == (Decimal("1000"), Decimal("1200"))
    assert first.currency == "AZN"


def test_id_comes_from_card_not_url(read_fixture):
    second = parse(read_fixture)[1]
    assert second.url.endswith("/vakansiya/qerarlarin-mecburi-icrasi-uzre-huquqsunas")
    assert second.external_id == "16727927"
    assert second.salary_min == second.salary_max == Decimal("600")
    assert second.published_on == date(2026, 10, 6)


def test_negotiable_salary_is_empty(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert by_id["16707805"].salary_min is None
    assert by_id["16707805"].salary_max is None


def test_skips_cards_without_id_or_title():
    page = """
    <a class="vacancies__body" href="/vakansiya/no-id">
      <h2 class="vacancies__title">No id</h2>
    </a>
    <a class="vacancies__body" href="/vakansiya/no-title-2">
      <button add-to-wishlist="2"></button>
    </a>
    <a class="vacancies__body" href="/vakansiya/tester-3">
      <h2 class="vacancies__title">Tester</h2>
      <button add-to-wishlist="3"></button>
    </a>
    """
    vacancies = HelloJobScraper(today=TODAY).parse_listing(page)
    assert [v.external_id for v in vacancies] == ["3"]
    assert vacancies[0].url == "https://www.hellojob.az/vakansiya/tester-3"
    assert vacancies[0].company == ""
    assert vacancies[0].published_on is None


def test_next_page_url(read_fixture):
    scraper = HelloJobScraper()
    next_url = scraper.next_page_url(
        read_fixture("hellojob_listing.html"), "https://www.hellojob.az/vakansiyalar"
    )
    assert next_url == "https://www.hellojob.az/vakansiyalar?page=2"
    last_page = '<ul class="pagination"><li><span class="pagination__btn next"></span></li></ul>'
    assert scraper.next_page_url(last_page, "https://www.hellojob.az/vakansiyalar") is None


def test_parse_detail_fills_description_and_location(read_fixture):
    scraper = HelloJobScraper(today=TODAY)
    vacancy = parse(read_fixture)[0]
    assert scraper.detail_url(vacancy) == vacancy.url

    detailed = scraper.parse_detail(read_fixture("hellojob_detail.html"), vacancy)
    assert "mağazamıza Administrator tələb olunur" in detailed.description
    assert "Mağaza ünvanı: Binə" in detailed.description
    assert "Telegram" not in detailed.description
    assert detailed.location == "Bakı"
    assert detailed.company == "Tahiroğlu İnşaat MMC"


def test_parse_detail_fills_missing_company_and_date(read_fixture):
    scraper = HelloJobScraper(today=TODAY)
    vacancy = HelloJobScraper(today=TODAY).parse_listing(
        '<a class="vacancies__body" href="/vakansiya/administrator-16757558">'
        '<h2 class="vacancies__title">Administrator</h2>'
        '<button add-to-wishlist="16757558"></button></a>'
    )[0]
    detailed = scraper.parse_detail(read_fixture("hellojob_detail.html"), vacancy)
    assert detailed.company == "Tahiroğlu İnşaat MMC"
    assert detailed.published_on == TODAY
