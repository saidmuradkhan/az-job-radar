import pytest
from sqlalchemy import inspect

from az_job_radar.db import DEFAULT_DATABASE_URL, database_url, get_engine


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
