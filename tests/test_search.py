from datetime import date
from decimal import Decimal

import pytest

from az_job_radar.models import Vacancy
from az_job_radar.search import Filters, facets, search


def make_vacancy(external_id, title, **extra) -> Vacancy:
    return Vacancy(
        source=extra.pop("source", "boss.az"),
        external_id=external_id,
        title=title,
        company=extra.pop("company", "Acme"),
        url=f"https://example.com/{external_id}",
        **extra,
    )


VACANCIES = [
    make_vacancy(
        "1",
        "Python Developer",
        category="it",
        tags=("python", "django", "docker"),
        languages=("english",),
        experience_years=2,
        seniority="middle",
        work_mode="hybrid",
        salary_min=Decimal("2000"),
        salary_max=Decimal("3000"),
        location="Bakı",
        published_on=date(2026, 10, 5),
    ),
    make_vacancy(
        "2",
        "Senior Java Developer",
        category="it",
        tags=("java", "docker"),
        languages=("english", "russian"),
        experience_years=5,
        seniority="senior",
        higher_education=True,
        location="Bakı",
        published_on=date(2026, 10, 6),
    ),
    make_vacancy(
        "3",
        "Baş mühasib",
        category="finance",
        tags=("1c", "excel", "tax"),
        languages=("azerbaijani", "russian"),
        experience_years=3,
        employment_type="full_time",
        higher_education=True,
        salary_min=Decimal("1500"),
        salary_max=Decimal("1500"),
        location="Sumqayıt",
        source="jobsearch.az",
        description="1C və Excel, vergi uçotu",
        published_on=date(2026, 10, 4),
    ),
    make_vacancy("4", "Mühasib köməkçisi", category="finance", tags=("1c", "excel")),
]


def uids(found):
    return [v.external_id for v in found]


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        (Filters(), ["2", "1", "3", "4"]),
        (Filters(category="finance"), ["3", "4"]),
        (Filters(tags=["docker"]), ["2", "1"]),
        (Filters(tags=["python", "docker"]), ["1"]),
        (Filters(languages=["russian"]), ["2", "3"]),
        (Filters(seniority="senior"), ["2"]),
        (Filters(work_mode="hybrid"), ["1"]),
        (Filters(employment_type="full_time"), ["3"]),
        (Filters(max_experience=2), ["1", "4"]),
        (Filters(min_salary=1800), ["1"]),
        (Filters(salary_only=True), ["1", "3"]),
        (Filters(no_degree=True), ["1", "4"]),
        (Filters(city="Sumqayıt"), ["3"]),
        (Filters(source="jobsearch.az"), ["3"]),
        (Filters(q="vergi"), ["3"]),
        (Filters(q="java developer"), ["2"]),
        (Filters(q="MÜHASİB"), ["3", "4"]),
        (Filters(category="it", tags=["1c"]), []),
    ],
)
def test_search(filters, expected):
    assert uids(search(VACANCIES, filters)) == expected


def test_facets_show_the_most_common_requirements_first():
    finance = search(VACANCIES, Filters(category="finance"))

    result = facets(finance)

    assert result["tags"] == [("1c", 2), ("excel", 2), ("tax", 1)]
    assert result["category"] == [("finance", 2)]
    assert result["languages"] == [("azerbaijani", 1), ("russian", 1)]
    assert result["city"] == [("Sumqayıt", 1)]


def test_facets_skip_empty_values():
    result = facets(VACANCIES)

    assert ("", 1) not in result["city"]
    assert dict(result["seniority"]) == {"middle": 1, "senior": 1}
    assert dict(result["source"]) == {"boss.az": 3, "jobsearch.az": 1}
