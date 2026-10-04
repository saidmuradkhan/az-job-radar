import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from az_job_radar.models import Vacancy
from az_job_radar.robots import RobotsPolicy

USER_AGENT = "az-job-radar/0.1 (+https://github.com/saidmuradkhan/az-job-radar)"

logger = logging.getLogger(__name__)


def build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=15.0,
        follow_redirects=True,
    )


class BaseScraper(ABC):
    source: str
    start_urls: tuple[str, ...] = ()
    request_headers: dict[str, str] = {}
    delay_seconds: float = 1.0
    max_pages: int = 1

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

    async def scrape(self) -> list[Vacancy]:
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
        return vacancies

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
