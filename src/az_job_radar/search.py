from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from az_job_radar.analysis import fold
from az_job_radar.models import Vacancy


@dataclass
class Filters:
    q: str = ""
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    seniority: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    max_experience: int | None = None
    min_salary: int | None = None
    salary_only: bool = False
    no_degree: bool = False
    city: str | None = None
    source: str | None = None


def best_salary(vacancy: Vacancy):
    return vacancy.salary_max if vacancy.salary_max is not None else vacancy.salary_min


def matches(vacancy: Vacancy, filters: Filters) -> bool:
    if filters.q:
        haystack = fold(f"{vacancy.title} {vacancy.company} {vacancy.description}")
        if not all(word in haystack for word in fold(filters.q).split()):
            return False
    if filters.category and vacancy.category != filters.category:
        return False
    if not set(filters.tags) <= set(vacancy.tags):
        return False
    if not set(filters.languages) <= set(vacancy.languages):
        return False
    for name in ("seniority", "work_mode", "employment_type", "source"):
        wanted = getattr(filters, name)
        if wanted and getattr(vacancy, name) != wanted:
            return False
    if filters.city and (vacancy.location or "") != filters.city:
        return False
    required_years = vacancy.experience_years or 0
    if filters.max_experience is not None and required_years > filters.max_experience:
        return False
    if filters.no_degree and vacancy.higher_education:
        return False
    salary = best_salary(vacancy)
    if (filters.salary_only or filters.min_salary) and salary is None:
        return False
    if filters.min_salary and salary < filters.min_salary:
        return False
    return True


def search(vacancies: list[Vacancy], filters: Filters) -> list[Vacancy]:
    found = [v for v in vacancies if matches(v, filters)]
    return sorted(found, key=lambda v: v.published_on or date.min, reverse=True)


def facets(vacancies: list[Vacancy], top: int = 25) -> dict[str, list[tuple[str, int]]]:
    """Count how often each filter value appears, most common first."""
    counters: dict[str, Counter] = {
        name: Counter()
        for name in (
            "category",
            "tags",
            "languages",
            "seniority",
            "work_mode",
            "employment_type",
            "city",
            "source",
        )
    }
    for vacancy in vacancies:
        counters["category"][vacancy.category] += 1
        counters["tags"].update(vacancy.tags)
        counters["languages"].update(vacancy.languages)
        counters["source"][vacancy.source] += 1
        for name in ("seniority", "work_mode", "employment_type"):
            if getattr(vacancy, name):
                counters[name][getattr(vacancy, name)] += 1
        if vacancy.location:
            counters["city"][vacancy.location] += 1
    return {name: counter.most_common(top) for name, counter in counters.items()}
