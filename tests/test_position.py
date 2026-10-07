from datetime import date

from az_job_radar.models import Vacancy
from az_job_radar.scrapers.position import PositionScraper

TODAY = date(2026, 10, 7)


def parse(read_fixture):
    return PositionScraper(today=TODAY).parse_listing(read_fixture("position_listing.html"))


def test_parses_every_row(read_fixture):
    vacancies = parse(read_fixture)
    assert len(vacancies) == 87
    assert len({v.uid for v in vacancies}) == 87


def test_maps_row_fields(read_fixture):
    first = parse(read_fixture)[0]
    assert first.source == "position.az"
    assert first.external_id == "1015843"
    assert first.title == "Milli Mühasib Sertifikatı üzrə təlimçi"
    assert first.company == "Barattson"
    assert first.url.startswith("https://position.az/az/vacancy/milli-muhasib-")
    assert first.url.endswith("-1015843")
    assert first.location == "Bakı"
    assert first.published_on == TODAY
    assert first.salary_min is None
    assert first.salary_max is None


def test_parses_dotted_dates_next_to_premium_badge(read_fixture):
    by_id = {v.external_id: v for v in parse(read_fixture)}
    assert by_id["1015831"].published_on == date(2026, 10, 2)
    assert by_id["1014995"].published_on == date(2025, 12, 4)


def test_has_a_single_page(read_fixture):
    scraper = PositionScraper()
    assert scraper.max_pages == 1
    listing = read_fixture("position_listing.html")
    assert scraper.next_page_url(listing, "https://position.az/") is None


def test_detail_adds_description(read_fixture):
    scraper = PositionScraper()
    vacancy = Vacancy(
        source="position.az",
        external_id="1015831",
        title="QC Lead",
        company="",
        url="https://position.az/az/vacancy/qc-lead-1015831",
    )
    assert scraper.detail_url(vacancy) == vacancy.url

    detailed = scraper.parse_detail(read_fixture("position_detail.html"), vacancy)
    assert detailed.description.startswith("Job Description:")
    assert "Liaise with Client QC Procedures and processes." in detailed.description
    assert detailed.title == "QC Lead"
    assert detailed.company == "Company-"
    assert detailed.location == "Bakı"
    assert detailed.published_on == date(2026, 10, 2)


def test_ignores_pages_without_rows():
    assert PositionScraper().parse_listing("<html><body>Heç nə</body></html>") == []
