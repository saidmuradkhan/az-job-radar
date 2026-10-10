from collections import Counter, defaultdict
from statistics import quantiles

from az_job_radar.analysis import SKILL_GROUPS
from az_job_radar.models import Vacancy

SKILL_GROUP = {skill: group for group, skills in SKILL_GROUPS.items() for skill in skills}
SENIORITY_ORDER = ["intern", "junior", "middle", "senior", "lead"]
# Smaller amounts are daily or hourly pay, not a monthly salary.
MIN_MONTHLY_SALARY = 100


def technology_stats(vacancies: list[Vacancy], group: str | None = None, top: int = 20) -> dict:
    """How many vacancies ask for each skill, most requested first."""
    counts = Counter(
        tag
        for vacancy in vacancies
        for tag in vacancy.tags
        if group is None or SKILL_GROUP.get(tag) == group
    )
    total = len(vacancies)
    return {
        "vacancies": total,
        "items": [
            {
                "name": tag,
                "group": SKILL_GROUP.get(tag, "Other"),
                "count": count,
                "share": round(count / total, 3),
            }
            for tag, count in counts.most_common(top)
        ],
    }


def monthly_salary(vacancy: Vacancy) -> float | None:
    """The middle of the range in AZN, or None when we cannot compare it."""
    values = [value for value in (vacancy.salary_min, vacancy.salary_max) if value is not None]
    if not values or vacancy.currency != "AZN":
        return None
    salary = float(sum(values)) / len(values)
    return salary if salary >= MIN_MONTHLY_SALARY else None


def summarise(salaries: list[float]) -> dict:
    low, middle, high = quantiles(salaries, n=4, method="inclusive")
    return {
        "count": len(salaries),
        "min": round(min(salaries)),
        "p25": round(low),
        "median": round(middle),
        "p75": round(high),
        "max": round(max(salaries)),
    }


def salary_stats(vacancies: list[Vacancy], min_group_size: int = 3) -> dict:
    """Salary spread overall, per category and per level (AZN only)."""
    salaries: list[float] = []
    by_category: dict[str, list[float]] = defaultdict(list)
    by_seniority: dict[str, list[float]] = defaultdict(list)
    for vacancy in vacancies:
        salary = monthly_salary(vacancy)
        if salary is None:
            continue
        salaries.append(salary)
        by_category[vacancy.category].append(salary)
        if vacancy.seniority:
            by_seniority[vacancy.seniority].append(salary)

    categories = [
        {"category": name, **summarise(values)}
        for name, values in by_category.items()
        if len(values) >= min_group_size
    ]
    levels = [
        {"seniority": name, **summarise(by_seniority[name])}
        for name in SENIORITY_ORDER
        if len(by_seniority[name]) >= min_group_size
    ]
    return {
        "currency": "AZN",
        "vacancies": len(vacancies),
        "with_salary": len(salaries),
        "overall": summarise(salaries) if len(salaries) >= 2 else None,
        "by_category": sorted(categories, key=lambda row: row["median"], reverse=True),
        "by_seniority": levels,
    }
