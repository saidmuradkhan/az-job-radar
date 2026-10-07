from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.ejob import EJobScraper


def parse(read_fixture):
    return EJobScraper().parse_listing(read_fixture("ejob_listing.html"))


def test_parses_every_card(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 32
    assert len({v.uid for v in vacancies}) == 32


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "ejob.az"
    assert first.external_id == "104489"
    assert first.title == "Satış təmsilcisi"
    assert first.company == "Aura Məişət Texnikası MMC"
    assert first.url == "https://ejob.az/is-elani/104489-satis-temsilcisi/"
    assert first.location == "Bakı"
    assert first.published_on is None
    assert (first.salary_min, first.salary_max) == (Decimal("400"), Decimal("1500"))


def test_single_salary_and_negotiable(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert by_id["104799"].salary_min == by_id["104799"].salary_max == Decimal("500")
    assert by_id["104797"].salary_min is None
    assert by_id["104797"].salary_max is None


def test_skips_cards_without_id_or_title():
    html = """
    <div class="list"><ul>
      <li><a href="/is-elanlari/">Bütün elanlar</a></li>
      <li><a href="/is-elani/12-x/"> </a></li>
    </ul></div>
    """
    assert EJobScraper().parse_listing(html) == []


def test_next_page_url(read_fixture):
    scraper = EJobScraper()
    next_url = scraper.next_page_url(
        read_fixture("ejob_listing.html"), "https://ejob.az/is-elanlari/"
    )
    assert next_url == "https://ejob.az/is-elanlari/page-2/"
    assert scraper.next_page_url("<html></html>", "https://ejob.az/is-elanlari/") is None


def test_detail_adds_full_description_and_date(read_fixture):
    scraper = EJobScraper()
    vacancy = {v.external_id: v for v in parse(read_fixture)}["103695"]
    assert scraper.detail_url(vacancy) == "https://ejob.az/is-elani/103695-logistika-koordinatoru/"

    detailed = scraper.parse_detail(read_fixture("ejob_detail.html"), vacancy)
    assert "Kuryer heyətinin idarə olunması" in detailed.description
    assert "Tələblər" in detailed.description
    assert detailed.published_on == date(2026, 9, 30)
    assert detailed.company == "My Kuryer MMC"
    assert detailed.title == "Logistika Koordinatoru"
