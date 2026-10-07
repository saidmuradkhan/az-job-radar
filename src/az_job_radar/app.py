import asyncio
import os
import time
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BeforeValidator, NonNegativeInt

from az_job_radar import gate
from az_job_radar.collect import collect
from az_job_radar.dashboard import render_dashboard
from az_job_radar.db import get_engine, load_recent
from az_job_radar.duplicates import find_duplicates
from az_job_radar.models import Vacancy
from az_job_radar.phrases import employer_count, phrase_counts
from az_job_radar.search import Filters, facets, search

Fetch = Callable[[], Awaitable[list[Vacancy]]]
RECENT = timedelta(days=30)

# HTML forms send "" for an empty number field; treat it as "no filter".
OptionalNumber = Annotated[
    NonNegativeInt | None, BeforeValidator(lambda value: value if value != "" else None)
]


@dataclass
class Catalog:
    """Vacancies with cross-site copies folded into the copy we show."""

    vacancies: list[Vacancy] = field(default_factory=list)
    copies: dict[str, list[Vacancy]] = field(default_factory=dict)
    phrase_background: Counter = field(default_factory=Counter)
    employers: int = 0

    @classmethod
    def build(cls, vacancies: list[Vacancy]) -> "Catalog":
        duplicates = find_duplicates(vacancies)
        copies: dict[str, list[Vacancy]] = defaultdict(list)
        for vacancy in vacancies:
            if vacancy.uid in duplicates:
                copies[duplicates[vacancy.uid]].append(vacancy)
        kept = [v for v in vacancies if v.uid not in duplicates]
        return cls(
            vacancies=kept,
            copies=dict(copies),
            phrase_background=phrase_counts(kept),
            employers=employer_count(kept),
        )

    def get(self, uid: str) -> Vacancy | None:
        return next((v for v in self.vacancies if v.uid == uid), None)

    def sources(self, vacancy: Vacancy) -> set[str]:
        return {vacancy.source, *(copy.source for copy in self.copies.get(vacancy.uid, []))}

    def facets(self, found: list[Vacancy]) -> dict[str, list[tuple[str, int]]]:
        # Compare with all ads only for a narrower group, otherwise everything looks ordinary.
        if len(found) * 2 > len(self.vacancies):
            return facets(found)
        return facets(
            found, background=self.phrase_background, background_size=self.employers
        )

    def search(self, filters: Filters) -> list[Vacancy]:
        found = search(self.vacancies, replace(filters, source=None))
        if filters.source:
            found = [v for v in found if filters.source in self.sources(v)]
        return found


class VacancyCache:
    def __init__(self, fetch: Fetch, ttl_seconds: float) -> None:
        self.fetch = fetch
        self.ttl_seconds = ttl_seconds
        self.catalog = Catalog()
        self.fetched_at: float | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> Catalog:
        async with self._lock:
            if self.fetched_at is None or time.time() - self.fetched_at > self.ttl_seconds:
                self.catalog = Catalog.build(await self.fetch())
                self.fetched_at = time.time()
        return self.catalog


def as_number(value):
    return float(value) if value is not None else None


def vacancy_to_dict(vacancy: Vacancy, copies: list[Vacancy] | None = None) -> dict:
    return {
        "uid": vacancy.uid,
        "source": vacancy.source,
        "title": vacancy.title,
        "company": vacancy.company,
        "url": vacancy.url,
        "location": vacancy.location,
        "published_on": vacancy.published_on.isoformat() if vacancy.published_on else None,
        "salary_min": as_number(vacancy.salary_min),
        "salary_max": as_number(vacancy.salary_max),
        "currency": vacancy.currency,
        "category": vacancy.category,
        "tags": list(vacancy.tags),
        "languages": list(vacancy.languages),
        "experience_years": vacancy.experience_years,
        "seniority": vacancy.seniority,
        "work_mode": vacancy.work_mode,
        "employment_type": vacancy.employment_type,
        "higher_education": vacancy.higher_education,
        "also_on": [{"source": c.source, "url": c.url} for c in copies or []],
    }


def filters_from_query(
    q: str = "",
    category: str | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    phrase: Annotated[list[str] | None, Query()] = None,
    seniority: str | None = None,
    work_mode: str | None = None,
    employment_type: str | None = None,
    max_experience: OptionalNumber = None,
    min_salary: OptionalNumber = None,
    salary_only: bool = False,
    no_degree: bool = False,
    city: str | None = None,
    source: str | None = None,
) -> Filters:
    return Filters(
        q=q,
        category=category or None,
        tags=tag or [],
        languages=language or [],
        phrases=phrase or [],
        seniority=seniority or None,
        work_mode=work_mode or None,
        employment_type=employment_type or None,
        max_experience=max_experience,
        min_salary=min_salary,
        salary_only=salary_only,
        no_degree=no_degree,
        city=city or None,
        source=source or None,
    )


def create_app(
    fetch: Fetch = collect,
    preview_gate: gate.PreviewGate | None = None,
    cache_ttl_seconds: float = 30 * 60,
    source: str = "live",
) -> FastAPI:
    app = FastAPI(title="az-job-radar", version="0.2.0")
    app.state.gate = preview_gate
    app.state.cache = VacancyCache(fetch, cache_ttl_seconds)

    app.middleware("http")(gate.gate_middleware)
    app.add_api_route("/login", gate.show_login, methods=["GET"], include_in_schema=False)
    app.add_api_route("/login", gate.submit_login, methods=["POST"], include_in_schema=False)
    app.add_api_route("/logout", gate.logout, methods=["GET"], include_in_schema=False)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "source": source}

    @app.get("/vacancies")
    async def list_vacancies(
        request: Request,
        filters: Annotated[Filters, Depends(filters_from_query)],
        page: Annotated[int, Query(ge=1)] = 1,
        per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict:
        catalog: Catalog = await request.app.state.cache.get()
        found = catalog.search(filters)
        start = (page - 1) * per_page
        return {
            "count": len(found),
            "page": page,
            "items": [
                vacancy_to_dict(v, catalog.copies.get(v.uid))
                for v in found[start : start + per_page]
            ],
            "facets": catalog.facets(found),
        }

    @app.get("/vacancies/{uid:path}")
    async def get_vacancy(request: Request, uid: str) -> dict:
        catalog: Catalog = await request.app.state.cache.get()
        vacancy = catalog.get(uid)
        if vacancy is None:
            raise HTTPException(status_code=404, detail="Vacancy not found")
        return vacancy_to_dict(vacancy, catalog.copies.get(uid)) | {
            "description": vacancy.description
        }

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(
        request: Request,
        filters: Annotated[Filters, Depends(filters_from_query)],
        page: Annotated[int, Query(ge=1)] = 1,
    ) -> str:
        catalog: Catalog = await request.app.state.cache.get()
        return render_dashboard(
            catalog,
            filters,
            query=request.url.query,
            page=page,
            show_logout=request.app.state.gate is not None,
        )

    return app


def create_app_from_env() -> FastAPI:
    """Read from the database when DATABASE_URL is set, otherwise scrape live."""
    preview_gate = gate.PreviewGate.from_env()
    if not os.environ.get("DATABASE_URL"):
        return create_app(preview_gate=preview_gate)

    engine = get_engine()

    async def fetch() -> list[Vacancy]:
        since = datetime.now(UTC) - RECENT
        return await asyncio.to_thread(load_recent, engine, since)

    return create_app(
        fetch=fetch, preview_gate=preview_gate, cache_ttl_seconds=5 * 60, source="database"
    )
