import pytest

from az_job_radar.pipeline import clean_title


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
