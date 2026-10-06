# az-job-radar

![CI](https://github.com/saidmuradkhan/az-job-radar/actions/workflows/ci.yml/badge.svg)

Async scraper and data pipeline that collects job vacancies from Azerbaijani job sites,
cleans and stores them, and exposes tech-demand analytics through a FastAPI REST API.

**Live demo:** [radar.saidmuradkhan.dev](https://radar.saidmuradkhan.dev) · [API docs](https://radar.saidmuradkhan.dev/docs) *(private preview, login required for now)*

> Part of a 3-service system: **az-job-radar** (Python) · [cbar-rates](https://github.com/saidmuradkhan/cbar-rates) (Go) · [jobtrack](https://github.com/saidmuradkhan/jobtrack) (Django + React)

## Tech stack

Python 3.12+ · asyncio · httpx · BeautifulSoup · SQLAlchemy · FastAPI · pytest · Ruff · GitHub Actions · Vercel
*(planned: PostgreSQL on Neon, Docker)*

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

Scrape all sources and save the results:

```bash
az-job-radar scrape
# INFO az_job_radar.collect: boss.az: 16 vacancies
# INFO az_job_radar.collect: jobsearch.az: 90 vacancies
# Run #1: ok, 106 vacancies found, 106 new
```

By default the data goes to a local SQLite file, `az_job_radar.db`. Set `DATABASE_URL`
(or pass `--database-url`) to use Postgres; install the driver with `pip install -e ".[postgres]"`.

## How the data flows

1. **Scrapers** (`scrapers/`) fetch every source at the same time and turn pages into `Vacancy` objects.
2. **Pipeline** (`pipeline.py`) cleans titles (`"TƏCİLİ! Backend developer"` → `"Backend developer"`),
   adds tech tags (`python`, `react`, `c#`, `1c`...) and drops duplicates by `uid` (`source:id`).
   Salaries are parsed while scraping: `"1500 - 2000 AZN"`, `"2000 ₼-dək"`, `"Razılaşma ilə"`, plus the currency.
3. **Database** (`db.py`) upserts into `vacancies`, keeping `first_seen_at` and updating `last_seen_at`.
   Every run is logged in `scrape_runs` (status, how many found, how many new, error).

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
- [x] Normalization: titles, salaries, tech tags (Python, React, Go...)
- [x] Deduplication by `uid`
- [x] Store with SQLAlchemy (SQLite locally, `DATABASE_URL` for Postgres), log scrape runs
- [ ] Postgres on Neon + Alembic migrations
- [x] CLI: `az-job-radar scrape`
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
