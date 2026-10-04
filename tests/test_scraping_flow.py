import httpx

from az_job_radar.collect import run_scrapers
from az_job_radar.models import Vacancy
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import USER_AGENT, BaseScraper

ROBOTS = "User-agent: *\nDisallow: /private\n"


def make_vacancy(external_id: str, source: str = "fake") -> Vacancy:
    return Vacancy(
        source=source,
        external_id=external_id,
        title=f"Job {external_id}",
        company="Acme",
        url=f"https://example.com/{external_id}",
    )


class FakeScraper(BaseScraper):
    source = "fake"
    delay_seconds = 0
    max_pages = 3

    def parse_listing(self, text: str) -> list[Vacancy]:
        return [make_vacancy(part) for part in text.split(",") if part]

    def next_page_url(self, text: str, current_url: str) -> str | None:
        page = int(current_url.rsplit("=", 1)[1])
        return f"https://example.com/jobs?page={page + 1}" if page < 2 else None


def client_for(pages: dict[str, str]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        body = pages.get(str(request.url))
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_scrape_follows_next_pages():
    client = client_for(
        {
            "https://example.com/jobs?page=1": "1,2",
            "https://example.com/jobs?page=2": "3",
        }
    )
    scraper = FakeScraper(client)
    scraper.start_urls = ("https://example.com/jobs?page=1",)

    vacancies = await scraper.scrape()

    assert [v.external_id for v in vacancies] == ["1", "2", "3"]
    await client.aclose()


async def test_robots_disallowed_urls_are_skipped():
    client = client_for({"https://example.com/private?page=1": "1"})
    scraper = FakeScraper(client)
    scraper.start_urls = ("https://example.com/private?page=1",)

    assert await scraper.scrape() == []
    await client.aclose()


async def test_missing_robots_file_allows_everything():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        policy = RobotsPolicy(USER_AGENT)
        assert await policy.allowed(client, "https://example.com/anything")


async def test_unreachable_robots_file_blocks_the_site():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        policy = RobotsPolicy(USER_AGENT)
        assert not await policy.allowed(client, "https://example.com/jobs")


class StaticScraper(BaseScraper):
    def __init__(self, source: str, vacancies: list[Vacancy] | Exception) -> None:
        self.source = source
        self._vacancies = vacancies

    def parse_listing(self, text: str) -> list[Vacancy]:
        return []

    async def scrape(self) -> list[Vacancy]:
        if isinstance(self._vacancies, Exception):
            raise self._vacancies
        return self._vacancies


async def test_run_scrapers_merges_and_deduplicates():
    first = StaticScraper("a", [make_vacancy("1", "a"), make_vacancy("2", "a")])
    second = StaticScraper("b", [make_vacancy("1", "b"), make_vacancy("1", "a")])

    vacancies = await run_scrapers([first, second])

    assert sorted(v.uid for v in vacancies) == ["a:1", "a:2", "b:1"]


async def test_one_failing_source_does_not_stop_the_others():
    broken = StaticScraper("broken", RuntimeError("site is down"))
    working = StaticScraper("ok", [make_vacancy("1", "ok")])

    vacancies = await run_scrapers([broken, working])

    assert [v.uid for v in vacancies] == ["ok:1"]
