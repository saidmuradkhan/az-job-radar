import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from az_job_radar import cli
from az_job_radar.db import ScrapeRun, VacancyRow
from az_job_radar.models import Vacancy

calls = []


async def fake_collect(details=False, skip=None):
    calls.append((details, skip))
    return [
        Vacancy(
            source="jobsearch.az",
            external_id="7",
            title="Go Developer",
            company="Acme",
            url="https://jobsearch.az/vacancies/7",
            description="Go, Docker, 2 il təcrübə",
        )
    ]


async def broken_collect(details=False, skip=None):
    raise RuntimeError("offline")


def test_scrape_saves_vacancies(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "collect", fake_collect)
    url = f"sqlite:///{tmp_path / 'radar.db'}"

    assert cli.main(["--database-url", url, "scrape"]) == 0

    assert "ok, 1 vacancies found, 1 new" in capsys.readouterr().out
    engine = create_engine(url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 1
        assert session.scalar(select(ScrapeRun.status)) == "ok"
    engine.dispose()


def test_scrape_exits_with_error_when_the_run_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "collect", broken_collect)
    url = f"sqlite:///{tmp_path / 'radar.db'}"

    assert cli.main(["--database-url", url, "scrape"]) == 1


def test_command_is_required():
    with pytest.raises(SystemExit):
        cli.main([])


def test_second_scrape_skips_known_detail_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "collect", fake_collect)
    calls.clear()
    url = f"sqlite:///{tmp_path / 'radar.db'}"

    cli.main(["--database-url", url, "scrape"])
    cli.main(["--database-url", url, "scrape", "--no-details"])

    assert calls == [(True, set()), (False, {"jobsearch.az:7"})]


def test_reanalyze_updates_stored_vacancies(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "collect", fake_collect)
    url = f"sqlite:///{tmp_path / 'radar.db'}"
    cli.main(["--database-url", url, "scrape"])
    engine = create_engine(url)
    with Session(engine) as session:
        row = session.get(VacancyRow, "jobsearch.az:7")
        row.tags = []
        session.commit()

    assert cli.main(["--database-url", url, "reanalyze"]) == 0

    assert "Analysed 1 vacancies again" in capsys.readouterr().out
    with Session(engine) as session:
        assert session.get(VacancyRow, "jobsearch.az:7").tags == ["go", "docker"]
    engine.dispose()
