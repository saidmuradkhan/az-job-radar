# az-job-radar

![CI](https://github.com/saidmuradkhan/az-job-radar/actions/workflows/ci.yml/badge.svg)

Async scraper and data pipeline that collects job vacancies from Azerbaijani job sites,
cleans and stores them, and exposes tech-demand analytics through a FastAPI REST API.

**Live demo:** [radar.saidmuradkhan.dev](https://radar.saidmuradkhan.dev) · [API docs](https://radar.saidmuradkhan.dev/docs) *(private preview, login required for now)*

> Part of a 3-service system: **az-job-radar** (Python) · [cbar-rates](https://github.com/saidmuradkhan/cbar-rates) (Go) · [jobtrack](https://github.com/saidmuradkhan/jobtrack) (Django + React)

## Tech stack

Python 3.12+ · asyncio · httpx · BeautifulSoup · FastAPI · pytest · Ruff · GitHub Actions · Vercel
*(planned: PostgreSQL, SQLAlchemy, Docker)*

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
pytest
```

Run the web app (dashboard at `/`, JSON at `/vacancies`, API docs at `/docs`):

```bash
uvicorn index:app --reload
```

Run a live scrape:

```bash
python -c "import asyncio; from az_job_radar.collect import collect; print(len(asyncio.run(collect())))"
```

## Deployment

The app runs on Vercel as a single Python function (`index.py`, see `vercel.json`).
Until the database lands, vacancies are scraped on demand and cached in memory for 30 minutes,
so the first request after a cold start takes ~20 seconds.

While the project is in review, the site is behind a small login page. It is turned on by
environment variables and turned off by removing them:

| Variable | Purpose |
|---|---|
| `PREVIEW_USER`, `PREVIEW_PASSWORD` | Login credentials. If either is missing, the site is public. |
| `PREVIEW_SECRET` | Key for signing the session cookie. Other services can send it as `X-Preview-Token`. |

`/health` is always public.

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
- [x] FastAPI: `/vacancies` and a simple dashboard
- [x] Preview deployment on Vercel behind a login page
- [ ] FastAPI: `/stats/technologies`, `/stats/salaries`
- [ ] Docker + docker-compose
- [ ] Scheduled scraping (GitHub Actions cron)

## Ethics

The scraper identifies itself with a clear User-Agent, waits between requests,
and respects each site's `robots.txt`.

## License

MIT
