import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import date
from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from az_job_radar import gate
from az_job_radar.collect import collect
from az_job_radar.models import Vacancy

Fetch = Callable[[], Awaitable[list[Vacancy]]]


class VacancyCache:
    """Until the database exists, vacancies are scraped live and kept in memory for a while."""

    def __init__(self, fetch: Fetch, ttl_seconds: float) -> None:
        self.fetch = fetch
        self.ttl_seconds = ttl_seconds
        self.vacancies: list[Vacancy] = []
        self.fetched_at: float | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> list[Vacancy]:
        async with self._lock:
            if self.fetched_at is None or time.time() - self.fetched_at > self.ttl_seconds:
                self.vacancies = await self.fetch()
                self.fetched_at = time.time()
        return self.vacancies


def sort_newest_first(vacancies: list[Vacancy]) -> list[Vacancy]:
    return sorted(vacancies, key=lambda v: v.published_on or date.min, reverse=True)


def format_salary(vacancy: Vacancy) -> str:
    low, high = vacancy.salary_min, vacancy.salary_max
    if low is None and high is None:
        return ""
    if low is not None and high is not None and low != high:
        return f"{low:,.0f} – {high:,.0f} {vacancy.currency}"
    return f"{(low or high):,.0f} {vacancy.currency}"


def vacancy_to_dict(vacancy: Vacancy) -> dict:
    return {
        "uid": vacancy.uid,
        "source": vacancy.source,
        "title": vacancy.title,
        "company": vacancy.company,
        "url": vacancy.url,
        "location": vacancy.location,
        "published_on": vacancy.published_on.isoformat() if vacancy.published_on else None,
        "salary_min": float(vacancy.salary_min) if vacancy.salary_min is not None else None,
        "salary_max": float(vacancy.salary_max) if vacancy.salary_max is not None else None,
        "currency": vacancy.currency,
        "tags": list(vacancy.tags),
    }


def create_app(
    fetch: Fetch = collect,
    preview_gate: gate.PreviewGate | None = None,
    cache_ttl_seconds: float = 30 * 60,
) -> FastAPI:
    app = FastAPI(title="az-job-radar", version="0.1.0")
    app.state.gate = preview_gate
    app.state.cache = VacancyCache(fetch, cache_ttl_seconds)

    app.middleware("http")(gate.gate_middleware)
    app.add_api_route("/login", gate.show_login, methods=["GET"], include_in_schema=False)
    app.add_api_route("/login", gate.submit_login, methods=["POST"], include_in_schema=False)
    app.add_api_route("/logout", gate.logout, methods=["GET"], include_in_schema=False)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/vacancies")
    async def list_vacancies(request: Request, source: str | None = None) -> dict:
        vacancies = sort_newest_first(await request.app.state.cache.get())
        if source:
            vacancies = [v for v in vacancies if v.source == source]
        return {"count": len(vacancies), "items": [vacancy_to_dict(v) for v in vacancies]}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request) -> str:
        vacancies = sort_newest_first(await request.app.state.cache.get())
        return render_dashboard(vacancies, show_logout=request.app.state.gate is not None)

    return app


def render_dashboard(vacancies: list[Vacancy], show_logout: bool) -> str:
    per_source = Counter(v.source for v in vacancies)
    sources = " · ".join(f"{escape(name)}: {count}" for name, count in per_source.most_common())
    rows = "\n".join(
        "<tr>"
        f'<td><a href="{escape(v.url, quote=True)}" target="_blank" rel="noopener">'
        f"{escape(v.title)}</a></td>"
        f"<td>{escape(v.company)}</td>"
        f"<td>{escape(format_salary(v))}</td>"
        f"<td>{escape(v.location or '')}</td>"
        f"<td>{v.published_on.isoformat() if v.published_on else ''}</td>"
        f"<td>{escape(v.source)}</td>"
        "</tr>"
        for v in vacancies
    )
    logout = '<a href="/logout">Log out</a>' if show_logout else ""
    return DASHBOARD_HTML.format(
        count=len(vacancies), sources=sources or "no data", rows=rows, logout=logout
    )


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>az-job-radar</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1.5rem 1rem;
         color: #1f2328; background: #f6f8fa; }}
  main {{ max-width: 1100px; margin: 0 auto; }}
  header {{ display: flex; justify-content: space-between; align-items: baseline;
           gap: 1rem; flex-wrap: wrap; }}
  h1 {{ margin: 0; font-size: 1.5rem; }}
  .meta {{ color: #656d76; }}
  .table {{ overflow-x: auto; background: #fff; border-radius: 10px; margin-top: 1rem;
           box-shadow: 0 1px 3px rgba(0, 0, 0, .08); }}
  table {{ border-collapse: collapse; width: 100%; font-size: .92rem; }}
  th, td {{ text-align: left; padding: .55rem .75rem; border-bottom: 1px solid #eaeef2; }}
  th {{ background: #f6f8fa; position: sticky; top: 0; }}
  a {{ color: #0969da; text-decoration: none; }}
  td:nth-child(3), td:nth-child(5) {{ white-space: nowrap; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>az-job-radar</h1>
    <span class="meta"><a href="/docs">API docs</a> {logout}</span>
  </header>
  <p class="meta">{count} vacancies · {sources}</p>
  <div class="table">
    <table>
      <thead>
        <tr><th>Title</th><th>Company</th><th>Salary</th><th>City</th><th>Date</th>
        <th>Source</th></tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
</main>
</body>
</html>
"""
