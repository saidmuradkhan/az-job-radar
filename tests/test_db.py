from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from az_job_radar.db import (
    DEFAULT_DATABASE_URL,
    VacancyRow,
    database_url,
    get_engine,
    upsert_vacancies,
)
from az_job_radar.models import Vacancy


@pytest.fixture
def engine():
    engine = get_engine("sqlite://")
    yield engine
    engine.dispose()


def test_tables_are_created(engine):
    assert set(inspect(engine).get_table_names()) == {"vacancies", "scrape_runs"}


def test_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == DEFAULT_DATABASE_URL


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("sqlite:///other.db", "sqlite:///other.db"),
    ],
)
def test_database_url_uses_psycopg_for_postgres(monkeypatch, given, expected):
    monkeypatch.setenv("DATABASE_URL", given)
    assert database_url() == expected


def make_vacancy(external_id="1", **overrides) -> Vacancy:
    data = {
        "source": "boss.az",
        "external_id": external_id,
        "title": "Python Developer",
        "company": "Acme",
        "url": f"https://boss.az/vacancies/{external_id}",
        "published_on": date(2026, 10, 6),
        "salary_min": Decimal("1500"),
        "salary_max": Decimal("2000"),
        "tags": ("python",),
    }
    data.update(overrides)
    return Vacancy(**data)


MONDAY = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
TUESDAY = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def test_upsert_inserts_new_vacancies(engine):
    with Session(engine) as session:
        new = upsert_vacancies(session, [make_vacancy("1"), make_vacancy("2")], MONDAY)
        session.commit()

        row = session.get(VacancyRow, "boss.az:1")

    assert new == 2
    assert row.title == "Python Developer"
    assert row.salary_min == Decimal("1500")
    assert row.tags == ["python"]
    assert row.first_seen_at == row.last_seen_at


def test_upsert_updates_known_vacancies_and_keeps_first_seen(engine):
    with Session(engine) as session:
        upsert_vacancies(session, [make_vacancy("1")], MONDAY)
        session.commit()

    with Session(engine) as session:
        new = upsert_vacancies(
            session, [make_vacancy("1", title="Senior Python Developer")], TUESDAY
        )
        session.commit()
        rows = session.scalars(select(VacancyRow)).all()

    assert new == 0
    assert len(rows) == 1
    assert rows[0].title == "Senior Python Developer"
    assert rows[0].first_seen_at.date() == MONDAY.date()
    assert rows[0].last_seen_at.date() == TUESDAY.date()


def test_upsert_handles_duplicates_in_one_batch(engine):
    with Session(engine) as session:
        new = upsert_vacancies(session, [make_vacancy("1"), make_vacancy("1")], MONDAY)
        session.commit()

        assert new == 1
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 1
