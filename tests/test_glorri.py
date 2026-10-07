import json
from datetime import date

from az_job_radar.scrapers.glorri import GlorriScraper


def flight_page(payload: dict) -> str:
    chunk = json.dumps(json.dumps(payload, separators=(",", ":")))[1:-1]
    return f'<script>self.__next_f.push([1,"{chunk}"])</script>'


def test_parses_main_list_not_carousel(read_fixture):
    vacancies = GlorriScraper().parse_listing(read_fixture("glorri_listing.html"))
    assert len(vacancies) == 18
    assert len({v.uid for v in vacancies}) == 18


def test_maps_entity_fields(read_fixture):
    first = GlorriScraper().parse_listing(read_fixture("glorri_listing.html"))[0]
    assert first.source == "jobs.glorri.az"
    assert first.external_id == "irtelecom-satis-meslehetcisi-fuzuli-52877472"
    assert first.title == "Satış Məsləhətçisi (Füzuli)"
    assert first.company == "İrşad"
    assert first.url == (
        "https://jobs.glorri.az/vacancies/irtelecom/irtelecom-satis-meslehetcisi-fuzuli-52877472"
    )
    assert first.location == "Füzuli"
    assert first.published_on == date(2026, 9, 30)
    assert first.salary_min is None


def test_skips_entities_without_title_or_slug():
    page = flight_page(
        {
            "vacancies": {
                "entities": [
                    {"title": "", "slug": "acme-empty-1", "company": {"slug": "acme"}},
                    {"title": "QA Engineer", "company": {"slug": "acme"}},
                    {"title": "Data Analyst", "slug": "acme-data-analyst-2", "company": {}},
                    {
                        "title": "Python Developer",
                        "slug": "acme-python-developer-3",
                        "company": {"slug": "acme", "name": "Acme"},
                    },
                ],
                "totalCount": 4,
            }
        }
    )
    vacancies = GlorriScraper().parse_listing(page)
    assert [v.external_id for v in vacancies] == ["acme-python-developer-3"]
    assert vacancies[0].location is None
    assert vacancies[0].published_on is None


def test_reads_only_the_newest_page():
    assert GlorriScraper.start_urls == ("https://jobs.glorri.az/?sort=-date",)
    assert GlorriScraper().next_page_url("<html></html>", GlorriScraper.start_urls[0]) is None


def test_parse_detail_adds_description(read_fixture):
    scraper = GlorriScraper()
    vacancy = scraper.parse_listing(read_fixture("glorri_listing.html"))[-1]
    assert scraper.detail_url(vacancy) == vacancy.url

    detailed = scraper.parse_detail(read_fixture("glorri_detail.html"), vacancy)
    assert "Data Governance üzrə strategiyaya uyğun" in detailed.description
    assert "Tableau upper-intermediate səviyyədə bilik;" in detailed.description
    assert "Vakansiya haqqında" not in detailed.description
    assert detailed.location == "Bakı"


def test_parse_detail_without_body_keeps_vacancy(read_fixture):
    scraper = GlorriScraper()
    vacancy = scraper.parse_listing(read_fixture("glorri_listing.html"))[0]
    assert scraper.parse_detail("<html></html>", vacancy) is vacancy
