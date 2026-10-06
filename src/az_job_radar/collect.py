import asyncio
import logging

from az_job_radar.models import Vacancy
from az_job_radar.pipeline import process
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import USER_AGENT, BaseScraper, build_client
from az_job_radar.scrapers.boss import BossScraper
from az_job_radar.scrapers.jobsearch import JobSearchScraper

logger = logging.getLogger(__name__)


async def run_scrapers(scrapers: list[BaseScraper]) -> list[Vacancy]:
    results = await asyncio.gather(
        *(scraper.scrape() for scraper in scrapers), return_exceptions=True
    )

    vacancies: list[Vacancy] = []
    for scraper, result in zip(scrapers, results, strict=True):
        if isinstance(result, Exception):
            logger.warning("%s failed: %s", scraper.source, result)
            continue
        logger.info("%s: %d vacancies", scraper.source, len(result))
        vacancies.extend(result)
    return process(vacancies)


async def collect() -> list[Vacancy]:
    robots = RobotsPolicy(USER_AGENT)
    async with build_client() as client:
        scrapers = [BossScraper(client, robots), JobSearchScraper(client, robots)]
        return await run_scrapers(scrapers)
