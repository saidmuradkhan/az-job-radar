from az_job_radar.models import Vacancy
from az_job_radar.stats import technology_stats


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
