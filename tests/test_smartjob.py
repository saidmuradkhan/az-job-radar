from datetime import date
from decimal import Decimal

from az_job_radar.scrapers.smartjob import SmartJobScraper


def parse(read_fixture):
    return SmartJobScraper().parse_listing(read_fixture("smartjob_listing.html"))


def test_parses_every_card(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 20
    assert len({v.uid for v in vacancies}) == 20


def test_maps_card_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "smartjob.az"
    assert first.external_id == "169894"
    assert first.title == "Tibbi nümayəndə"
    assert first.company == "GoldenVit Pharm"
    assert first.url == "https://smartjob.az/vakansiyalar/satis-numayendesi-muwb3s9g"
    assert first.location == "Bakı"
    assert first.published_on == date(2026, 10, 6)
    assert (first.salary_min, first.salary_max) == (None, Decimal("600"))


def test_salary_range_and_negotiable(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert (by_id["169733"].salary_min, by_id["169733"].salary_max) == (
        Decimal("1500"),
        Decimal("2000"),
    )
    assert by_id["169932"].salary_min is None
    assert by_id["169932"].salary_max is None


def test_skips_cards_without_id_or_title():
    html = """
    <article class="job-row"><h3><a href="/vakansiyalar/x">No id</a></h3></article>
    <article class="job-row" id="vacancy-5"><h3><a href="/vakansiyalar/y"> </a></h3></article>
    """
    assert SmartJobScraper().parse_listing(html) == []


def test_reads_a_single_page(read_fixture):
    scraper = SmartJobScraper()
    assert scraper.max_pages == 1
    assert scraper.next_page_url(read_fixture("smartjob_listing.html"), "") is None


def test_detail_adds_description_and_date(read_fixture):
    scraper = SmartJobScraper()
    first = parse(read_fixture)[0]
    assert scraper.detail_url(first) == first.url

    detailed = scraper.parse_detail(read_fixture("smartjob_detail.html"), first)
    assert "Bazar təhlili aparmaq" in detailed.description
    assert "<li>" not in detailed.description
    assert detailed.published_on == date(2026, 10, 6)
    assert detailed.title == first.title


def test_detail_fills_missing_company_and_city(read_fixture):
    first = parse(read_fixture)[0]
    bare = SmartJobScraper().parse_listing(
        '<article class="job-row" id="vacancy-169894"><h3><a href="/v/x">Tibbi</a></h3></article>'
    )[0]
    assert bare.company == ""
    detailed = SmartJobScraper().parse_detail(read_fixture("smartjob_detail.html"), bare)
    assert detailed.company == first.company
    assert detailed.location == "Bakı"
