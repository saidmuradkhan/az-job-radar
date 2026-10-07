import os
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Engine, Numeric, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from az_job_radar.duplicates import find_duplicates
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
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(30), index=True, default="other")
    tags: Mapped[list[str]] = mapped_column(JSON)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience_years: Mapped[int | None]
    seniority: Mapped[str | None] = mapped_column(String(20))
    work_mode: Mapped[str | None] = mapped_column(String(20))
    employment_type: Mapped[str | None] = mapped_column(String(20))
    higher_education: Mapped[bool] = mapped_column(default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String(120), index=True)
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
    duplicates: Mapped[int] = mapped_column(default=0)
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


LISTING_FIELDS = (
    "source",
    "external_id",
    "title",
    "company",
    "url",
    "location",
    "published_on",
    "salary_min",
    "salary_max",
    "currency",
)
ANALYSIS_FIELDS = (
    "description",
    "category",
    "tags",
    "languages",
    "experience_years",
    "seniority",
    "work_mode",
    "employment_type",
    "higher_education",
)


def fill_row(row: VacancyRow, vacancy: Vacancy) -> None:
    for name in LISTING_FIELDS:
        setattr(row, name, getattr(vacancy, name))

    # Known vacancies are re-scraped without their detail page,
    # so don't replace a full analysis with a title-only one.
    if vacancy.description or not row.description:
        for name in ANALYSIS_FIELDS:
            value = getattr(vacancy, name)
            setattr(row, name, list(value) if isinstance(value, tuple) else value)


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


def mark_duplicates(session: Session, since: datetime) -> int:
    """Link cross-site copies of the same job. Returns how many copies were found."""
    rows = session.scalars(select(VacancyRow).where(VacancyRow.last_seen_at >= since)).all()
    duplicates = find_duplicates(rows)
    for row in rows:
        row.duplicate_of = duplicates.get(row.uid)
    return len(duplicates)


def uids_with_description(engine: Engine) -> set[str]:
    """Vacancies whose detail page we already read, so the next scrape can skip them."""
    with Session(engine) as session:
        return set(session.scalars(select(VacancyRow.uid).where(VacancyRow.description != "")))


def row_to_vacancy(row: VacancyRow) -> Vacancy:
    values = {name: getattr(row, name) for name in (*LISTING_FIELDS, *ANALYSIS_FIELDS)}
    values["tags"] = tuple(row.tags or ())
    values["languages"] = tuple(row.languages or ())
    return Vacancy(**values)


def load_recent(engine: Engine, since: datetime) -> list[Vacancy]:
    """Vacancies that were still online at some point after `since`."""
    with Session(engine) as session:
        rows = session.scalars(select(VacancyRow).where(VacancyRow.last_seen_at >= since))
        return [row_to_vacancy(row) for row in rows]
