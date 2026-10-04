import logging
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsPolicy:
    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._parsers: dict[str, RobotFileParser] = {}

    async def allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._parsers:
            self._parsers[origin] = await self._load(client, origin)
        return self._parsers[origin].can_fetch(self.user_agent, url)

    async def _load(self, client: httpx.AsyncClient, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            response = await client.get(f"{origin}/robots.txt")
        except httpx.HTTPError as error:
            logger.warning("Could not read robots.txt for %s: %s", origin, error)
            parser.disallow_all = True
            return parser

        if response.status_code in (401, 403):
            parser.disallow_all = True
        elif response.status_code >= 400:
            parser.allow_all = True
        else:
            parser.parse(response.text.splitlines())
        parser.modified()
        return parser
