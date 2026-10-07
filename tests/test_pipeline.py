from datetime import date

import pytest

from az_job_radar.models import Vacancy
from az_job_radar.pipeline import clean_title, dedupe, process


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Python   Developer ", "Python Developer"),
        ("TƏCİLİ! Backend developer", "Backend developer"),
        ("Frontend developer (təcili)", "Frontend developer"),
        ("Urgent: QA engineer", "QA engineer"),
        ("- Data Analyst -", "Data Analyst"),
        ("1C Proqramçı (remote-təcrübəçi)", "1C Proqramçı (remote-təcrübəçi)"),
        ("Təcili", "Təcili"),
    ],
)
def test_clean_title(raw, expected):
    assert clean_title(raw) == expected


def make_vacancy(external_id="1", **overrides) -> Vacancy:
    data = {
        "source": "boss.az",
        "external_id": external_id,
        "title": "Python Developer",
        "company": "Acme",
        "url": f"https://example.com/{external_id}",
    }
    data.update(overrides)
    return Vacancy(**data)


def test_dedupe_keeps_the_most_recent_copy():
    old = make_vacancy(published_on=date(2026, 10, 1), title="Old title")
    new = make_vacancy(published_on=date(2026, 10, 5), title="New title")
    other = make_vacancy("2")

    result = dedupe([old, other, new])

    assert [(v.uid, v.title) for v in result] == [
        ("boss.az:1", "New title"),
        ("boss.az:2", "Python Developer"),
    ]


def test_dedupe_keeps_first_copy_when_dates_are_missing():
    first = make_vacancy(title="First")
    second = make_vacancy(title="Second")

    assert [v.title for v in dedupe([first, second])] == ["First"]


def test_process_cleans_tags_and_dedupes():
    raw = [
        make_vacancy(title="TƏCİLİ! React developer", company="  Acme  "),
        make_vacancy(title="React developer"),
        make_vacancy("2", title="Mühasib", description="1C və Excel biliyi, 2 il təcrübə"),
    ]

    result = process(raw)

    assert len(result) == 2
    react, accountant = result
    assert react.title == "React developer"
    assert react.company == "Acme"
    assert react.category == "it"
    assert react.tags == ("react",)
    assert accountant.category == "finance"
    assert accountant.tags == ("1c", "excel")
    assert accountant.experience_years == 2
