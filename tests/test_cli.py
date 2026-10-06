import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from az_job_radar import cli
from az_job_radar.db import ScrapeRun, VacancyRow
from az_job_radar.models import Vacancy


async def fake_collect():
    return [
        Vacancy(
            source="jobsearch.az",
            external_id="7",
            title="Go Developer",
            company="Acme",
            url="https://jobsearch.az/vacancies/7",
        )
    ]


async def broken_collect():
    raise RuntimeError("offline")


def test_scrape_saves_vacancies(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "collect", fake_collect)
    url = f"sqlite:///{tmp_path / 'radar.db'}"

    assert cli.main(["scrape", "--database-url", url]) == 0

    assert "ok, 1 vacancies found, 1 new" in capsys.readouterr().out
    engine = create_engine(url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 1
        assert session.scalar(select(ScrapeRun.status)) == "ok"
    engine.dispose()


def test_scrape_exits_with_error_when_the_run_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "collect", broken_collect)
    url = f"sqlite:///{tmp_path / 'radar.db'}"

    assert cli.main(["scrape", "--database-url", url]) == 1


def test_command_is_required():
    with pytest.raises(SystemExit):
        cli.main([])
