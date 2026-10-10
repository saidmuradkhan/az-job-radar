from decimal import Decimal

from az_job_radar.models import Vacancy
from az_job_radar.stats import monthly_salary, salary_stats, technology_stats


def make(number: int, **fields) -> Vacancy:
    return Vacancy(
        source="boss.az", external_id=str(number), title="Job", company="Acme", url="u", **fields
    )


VACANCIES = [
    make(1, tags=("python", "django", "sql")),
    make(2, tags=("python", "excel")),
    make(3, tags=("python",)),
    make(4, tags=("excel",)),
]


def test_most_requested_skills_come_first():
    stats = technology_stats(VACANCIES)
    assert stats["vacancies"] == 4
    assert stats["items"][0] == {
        "name": "python",
        "group": "Programming languages",
        "count": 3,
        "share": 0.75,
    }
    assert [item["name"] for item in stats["items"]][:2] == ["python", "excel"]


def test_skills_can_be_limited_to_one_group():
    stats = technology_stats(VACANCIES, group="Frameworks")
    assert stats["items"] == [{"name": "django", "group": "Frameworks", "count": 1, "share": 0.25}]


def test_top_limits_the_list():
    assert len(technology_stats(VACANCIES, top=2)["items"]) == 2


def test_no_vacancies_means_no_skills():
    assert technology_stats([]) == {"vacancies": 0, "items": []}


def paid(number: int, low: int | None, high: int | None, **fields) -> Vacancy:
    return make(
        number,
        salary_min=Decimal(low) if low is not None else None,
        salary_max=Decimal(high) if high is not None else None,
        **fields,
    )


def test_monthly_salary_is_the_middle_of_the_range():
    assert monthly_salary(paid(1, 1000, 2000)) == 1500
    assert monthly_salary(paid(1, None, 2000)) == 2000
    assert monthly_salary(paid(1, 800, None)) == 800


def test_monthly_salary_skips_what_cannot_be_compared():
    assert monthly_salary(make(1)) is None
    assert monthly_salary(paid(1, 1000, 2000, currency="USD")) is None
    assert monthly_salary(paid(1, 30, 40)) is None


SALARIES = [
    paid(1, 1000, 2000, category="it", seniority="junior"),
    paid(2, 2000, 3000, category="it", seniority="senior"),
    paid(3, 3000, 5000, category="it", seniority="senior"),
    paid(4, 600, 800, category="sales", seniority="junior"),
    paid(5, 700, 700, category="sales", seniority="junior"),
    paid(6, 500, 500, category="sales"),
    paid(7, 4000, 4000, category="legal", seniority="senior"),
    make(8, category="it"),
    paid(9, 9000, 9000, category="it", currency="USD"),
]


def test_salary_stats_overall():
    stats = salary_stats(SALARIES)
    assert stats["currency"] == "AZN"
    assert stats["vacancies"] == 9
    assert stats["with_salary"] == 7
    assert stats["overall"] == {
        "count": 7,
        "min": 500,
        "p25": 700,
        "median": 1500,
        "p75": 3250,
        "max": 4000,
    }


def test_salary_stats_by_category_skip_small_groups():
    rows = salary_stats(SALARIES)["by_category"]
    assert [(row["category"], row["count"], row["median"]) for row in rows] == [
        ("it", 3, 2500),
        ("sales", 3, 700),
    ]


def test_salary_stats_by_level_in_career_order():
    rows = salary_stats(SALARIES, min_group_size=2)["by_seniority"]
    assert [(row["seniority"], row["median"]) for row in rows] == [
        ("junior", 700),
        ("senior", 4000),
    ]


def test_salary_stats_without_salaries():
    stats = salary_stats([make(1)])
    assert stats["with_salary"] == 0
    assert stats["overall"] is None
    assert stats["by_category"] == []
