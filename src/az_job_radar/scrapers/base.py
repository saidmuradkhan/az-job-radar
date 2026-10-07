import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup

from az_job_radar.models import Vacancy
from az_job_radar.robots import RobotsPolicy

USER_AGENT = "az-job-radar/0.1 (+https://github.com/saidmuradkhan/az-job-radar)"
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)
FLIGHT_TEXT_ROW = re.compile(rb"(?:^|\n)([0-9a-f]+):T([0-9a-f]+),")

logger = logging.getLogger(__name__)


def build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=15.0,
        follow_redirects=True,
    )


def html_to_text(html: str) -> str:
    """Turn a description written in HTML into plain text, one block per line."""
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


def flight_data(text: str) -> str:
    """Join the Next.js data chunks that the page streams inside <script> tags."""
    return "".join(json.loads(f'"{chunk}"') for chunk in FLIGHT_CHUNK.findall(text))


def flight_texts(data: str) -> dict[str, str]:
    """Long strings are sent as separate rows like `16:T67b,<text>` and referenced as "$16"."""
    raw = data.encode()
    texts = {}
    for match in FLIGHT_TEXT_ROW.finditer(raw):
        start, length = match.end(), int(match.group(2), 16)
        texts["$" + match.group(1).decode()] = raw[start : start + length].decode(errors="ignore")
    return texts


def find_job_posting(soup: BeautifulSoup) -> dict:
    """Return the schema.org JobPosting that many job sites embed for search engines."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return {}


class BaseScraper(ABC):
    source: str
    start_urls: tuple[str, ...] = ()
    request_headers: dict[str, str] = {}
    delay_seconds: float = 1.0
    max_pages: int = 1
    max_details: int = 150

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        robots: RobotsPolicy | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or build_client()
        self._robots = robots or RobotsPolicy(USER_AGENT)

    async def fetch(self, url: str) -> str | None:
        if not await self._robots.allowed(self._client, url):
            logger.info("Skipping %s: disallowed by robots.txt", url)
            return None
        response = await self._client.get(url, headers=self.request_headers)
        response.raise_for_status()
        await asyncio.sleep(self.delay_seconds)
        return response.text

    @abstractmethod
    def parse_listing(self, text: str) -> list[Vacancy]:
        pass

    def next_page_url(self, text: str, current_url: str) -> str | None:
        return None

    def detail_url(self, vacancy: Vacancy) -> str | None:
        """Where the full description lives. None means the listing already has everything."""
        return None

    def parse_detail(self, text: str, vacancy: Vacancy) -> Vacancy:
        return vacancy

    async def add_details(self, vacancies: list[Vacancy], skip: set[str]) -> list[Vacancy]:
        result = []
        fetched = 0
        for vacancy in vacancies:
            url = self.detail_url(vacancy)
            if not url or vacancy.uid in skip or fetched >= self.max_details:
                result.append(vacancy)
                continue
            fetched += 1
            try:
                text = await self.fetch(url)
            except httpx.HTTPError as error:
                logger.warning("%s: detail page %s failed: %s", self.source, url, error)
                text = None
            result.append(self.parse_detail(text, vacancy) if text else vacancy)
        return result

    async def scrape(self, details: bool = False, skip: set[str] | None = None) -> list[Vacancy]:
        vacancies: list[Vacancy] = []
        for start_url in self.start_urls:
            url: str | None = start_url
            pages = 0
            while url and pages < self.max_pages:
                text = await self.fetch(url)
                if text is None:
                    break
                vacancies.extend(self.parse_listing(text))
                url = self.next_page_url(text, url)
                pages += 1
        if details:
            vacancies = await self.add_details(vacancies, skip or set())
        return vacancies

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
