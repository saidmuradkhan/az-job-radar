import os
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Engine, Numeric, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from az_job_radar.models import Vacancy

DEFAULT_DATABASE_URL = "sqlite:///az_job_radar.db"


class Base(DeclarativeBase):
    pass


class VacancyRow(Base):
    __tablename__ = "vacancies"

    uid: Mapped[str] = mapped_column(String(120), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    published_on: Mapped[date | None]
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    tags: Mapped[list[str]] = mapped_column(JSON)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    found: Mapped[int] = mapped_column(default=0)
    new: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def get_engine(url: str | None = None) -> Engine:
    engine = create_engine(url or database_url())
    Base.metadata.create_all(engine)
    return engine


def fill_row(row: VacancyRow, vacancy: Vacancy) -> None:
    row.source = vacancy.source
    row.external_id = vacancy.external_id
    row.title = vacancy.title
    row.company = vacancy.company
    row.url = vacancy.url
    row.location = vacancy.location
    row.published_on = vacancy.published_on
    row.salary_min = vacancy.salary_min
    row.salary_max = vacancy.salary_max
    row.currency = vacancy.currency
    row.tags = list(vacancy.tags)


def upsert_vacancies(session: Session, vacancies: list[Vacancy], seen_at: datetime) -> int:
    """Insert new vacancies and refresh known ones. Returns how many were new."""
    uids = [vacancy.uid for vacancy in vacancies]
    existing = {
        row.uid: row for row in session.scalars(select(VacancyRow).where(VacancyRow.uid.in_(uids)))
    }

    new_count = 0
    for vacancy in vacancies:
        row = existing.get(vacancy.uid)
        if row is None:
            row = VacancyRow(uid=vacancy.uid, first_seen_at=seen_at)
            session.add(row)
            existing[vacancy.uid] = row
            new_count += 1
        fill_row(row, vacancy)
        row.last_seen_at = seen_at
    return new_count
