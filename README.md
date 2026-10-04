# az-job-radar

![CI](https://github.com/saidmuradkhan/az-job-radar/actions/workflows/ci.yml/badge.svg)

Async scraper and data pipeline that collects job vacancies from Azerbaijani job sites,
cleans and stores them, and exposes tech-demand analytics through a FastAPI REST API.

> Part of a 3-service system: **az-job-radar** (Python) · [cbar-rates](https://github.com/saidmuradkhan/cbar-rates) (Go) · [jobtrack](https://github.com/saidmuradkhan/jobtrack) (Django + React)

## Tech stack

Python 3.12+ · asyncio · httpx · BeautifulSoup · pytest · Ruff · GitHub Actions
*(planned: PostgreSQL, SQLAlchemy, FastAPI, Docker)*

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
pytest
```

Run a live scrape:

```bash
python -c "import asyncio; from az_job_radar.collect import collect; print(len(asyncio.run(collect())))"
```

## Sources

| Site | How | Notes |
|---|---|---|
| boss.az | HTML pages, parsed with BeautifulSoup | IT categories only |
| jobsearch.az | Public JSON endpoint used by the site itself | Follows the `next` link, 3 pages |

## Roadmap

- [x] Project setup: package layout, `Vacancy` model, tests, CI
- [x] boss.az scraper (HTML, IT categories) with an offline fixture
- [x] jobsearch.az scraper (JSON API with pagination)
- [x] Run all sources concurrently with `asyncio.gather`, polite delay between requests
- [x] Respect `robots.txt`
- [ ] Normalization: titles, salaries, tech tags (Python, React, Go...)
- [ ] Deduplication by `uid`
- [ ] Store in PostgreSQL (SQLAlchemy + Alembic migrations)
- [ ] CLI: `az-job-radar scrape`
- [ ] Analytics: most requested technologies, salary ranges
- [ ] FastAPI: `/vacancies`, `/stats/technologies`
- [ ] Docker + docker-compose
- [ ] Scheduled scraping (GitHub Actions cron)

## Ethics

The scraper identifies itself with a clear User-Agent, waits between requests,
and respects each site's `robots.txt`.

## License

MIT
