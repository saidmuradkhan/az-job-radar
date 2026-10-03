from decimal import Decimal

import pytest

from az_job_radar.models import Vacancy


def make_vacancy(**overrides) -> Vacancy:
    data = {
        "source": "test-site",
        "external_id": "42",
        "title": "Python Developer",
        "company": "Acme",
        "url": "https://example.com/jobs/42",
    }
    data.update(overrides)
    return Vacancy(**data)


def test_uid_combines_source_and_external_id():
    assert make_vacancy().uid == "test-site:42"


def test_empty_title_is_rejected():
    with pytest.raises(ValueError):
        make_vacancy(title="   ")


def test_salary_range_must_be_ordered():
    with pytest.raises(ValueError):
        make_vacancy(salary_min=Decimal("3000"), salary_max=Decimal("1000"))
