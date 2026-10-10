from collections import Counter

from az_job_radar.analysis import SKILL_GROUPS
from az_job_radar.models import Vacancy

SKILL_GROUP = {skill: group for group, skills in SKILL_GROUPS.items() for skill in skills}


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
