import asyncio
from abc import ABC, abstractmethod

import httpx

from az_job_radar.models import Vacancy

USER_AGENT = "az-job-radar/0.1 (+https://github.com/saidmuradkhan/az-job-radar)"


class BaseScraper(ABC):
    source: str
    delay_seconds: float = 1.0

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
            follow_redirects=True,
        )

    async def fetch(self, url: str) -> str:
        response = await self._client.get(url)
        response.raise_for_status()
        await asyncio.sleep(self.delay_seconds)
        return response.text

    @abstractmethod
    def parse_listing(self, html: str) -> list[Vacancy]:
        pass

    async def close(self) -> None:
        await self._client.aclose()
