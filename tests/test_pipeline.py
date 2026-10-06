import pytest

from az_job_radar.pipeline import clean_title, extract_tags


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


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Python/Django Developer", ("python", "django")),
        ("Frontend developer (React, TypeScript)", ("typescript", "react", "frontend")),
        ("Java Developer", ("java",)),
        ("JavaScript developer", ("javascript",)),
        ("C# proqramçı", ("c#",)),
        ("ASP.NET Core developer", (".net",)),
        ("1C Proqramçı", ("1c",)),
        ("Junior System Administrator", ("sysadmin",)),
        ("QA/QC Manager", ("qa",)),
        ("Golang backend engineer", ("go", "backend")),
        ("Mühasib", ()),
    ],
)
def test_extract_tags(title, expected):
    assert extract_tags(title) == expected
