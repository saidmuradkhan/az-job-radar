import asyncio
import logging

from az_job_radar.models import Vacancy
from az_job_radar.pipeline import process
from az_job_radar.robots import RobotsPolicy
from az_job_radar.scrapers.base import USER_AGENT, BaseScraper, build_client
from az_job_radar.scrapers.boss import BossScraper
from az_job_radar.scrapers.ejob import EJobScraper
from az_job_radar.scrapers.glorri import GlorriScraper
from az_job_radar.scrapers.hellojob import HelloJobScraper
from az_job_radar.scrapers.ishelanlari import IshElanlariScraper
from az_job_radar.scrapers.jobsearch import JobSearchScraper
from az_job_radar.scrapers.oneis import OneIsScraper
from az_job_radar.scrapers.position import PositionScraper
from az_job_radar.scrapers.smartjob import SmartJobScraper
from az_job_radar.scrapers.vakansiyabiz import VakansiyaBizScraper

logger = logging.getLogger(__name__)

SCRAPERS: list[type[BaseScraper]] = [
    BossScraper,
    JobSearchScraper,
    GlorriScraper,
    HelloJobScraper,
    SmartJobScraper,
    EJobScraper,
    VakansiyaBizScraper,
    PositionScraper,
    OneIsScraper,
    IshElanlariScraper,
]


async def run_scrapers(
    scrapers: list[BaseScraper], details: bool = False, skip: set[str] | None = None
) -> list[Vacancy]:
    results = await asyncio.gather(
        *(scraper.scrape(details=details, skip=skip) for scraper in scrapers),
        return_exceptions=True,
    )

    vacancies: list[Vacancy] = []
    for scraper, result in zip(scrapers, results, strict=True):
        if isinstance(result, Exception):
            logger.warning("%s failed: %s", scraper.source, result)
            continue
        logger.info("%s: %d vacancies", scraper.source, len(result))
        vacancies.extend(result)
    return process(vacancies)


async def collect(details: bool = False, skip: set[str] | None = None) -> list[Vacancy]:
    """Scrape every site at once. With details=True, new vacancies get their full text too."""
    robots = RobotsPolicy(USER_AGENT)
    async with build_client() as client:
        scrapers = [scraper(client, robots) for scraper in SCRAPERS]
        return await run_scrapers(scrapers, details=details, skip=skip)
