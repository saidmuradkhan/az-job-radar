import os
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Engine, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
