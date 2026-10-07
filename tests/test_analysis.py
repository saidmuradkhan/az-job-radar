import pytest

from az_job_radar.analysis import CATEGORY_LABELS, SKILL_GROUPS, analyze, extract_tags

ACCOUNTANT_AD = """
Tələblər:
- Ali təhsil (iqtisadiyyat, mühasibat uçotu)
- Mühasibat sahəsində minimum 3 il iş təcrübəsi
- 1C proqramını və MS Excel-i mükəmməl bilməsi
- Vergi qanunvericiliyini və MHBS-ni bilməsi
- Azərbaycan və rus dillərini bilməsi
İş qrafiki: tam ştat, 09:00-18:00
"""

DEVELOPER_AD = """
Requirements:
- 2+ years of experience with Python and Django
- PostgreSQL, Docker, Git
- Good English
We offer a hybrid schedule.
"""


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("Senior Python Developer", "it"),
        ("1C Proqramçı", "it"),
        ("İT mütəxəssisi", "it"),
        ("Baş mühasib", "finance"),
        ("HR Compliance & Employee Relations Specialist", "hr"),
        ("Marketinq direktoru", "marketing"),
        ("IELTS müəllimi", "education"),
        ("Satış təmsilçisi", "sales"),
        ("Çağrı mərkəzi operatoru", "customer_service"),
        ("QA/QC Manager", "engineering"),
        ("Texniki dəstək mütəxəssisi", "it"),
        ("Facility Operations Manager", "management"),
        ("Xadimə", "services"),
        ("Keyfiyyətə Nəzarət üzrə İnspektor", "engineering"),
        ("Smeta və layihə mütəxəssisi", "construction"),
        ("Satınalma üzrə kiçik mütəxəssis", "logistics"),
        ("Operations Coordinator – Incoming Tourism", "hospitality"),
        ("Layihə assistenti", "admin"),
        ("General English Instructor", "education"),
        ("Videoqraf", "design"),
        ("Rəqəmsal dələduzluq əməliyyatlarının monitorinqi üzrə mütəxəssis", "finance"),
        ("Педагог Английского языка", "education"),
        ("Руководитель отдела маркетинга", "marketing"),
        ("Merçendayzer", "sales"),
        ("Kargüzar", "admin"),
        ("Növbə rəisi", "management"),
        ("Salatçı", "hospitality"),
        ("Mal qəbulçusu", "logistics"),
        ("Şəki filialı üzrə Universal işçi", "services"),
        ("Xərclərə nəzarət üzrə aparıcı mühəndis", "engineering"),
        ("Milli Mühasib Sertifikatı üzrə təlimçi", "education"),
        ("Satınalma üzrə mütəxəssis (İnvestisiya Layihələri Üzrə)", "logistics"),
        ("Gözəllik salonu üçün kosmetoloq", "other"),
    ],
)
def test_category_comes_from_the_title(title, category):
    assert analyze(title).category == category


def test_every_category_has_a_label():
    assert {analyze("x").category} <= set(CATEGORY_LABELS)


def test_accountant_ad():
    result = analyze("Baş mühasib", ACCOUNTANT_AD)

    assert result.category == "finance"
    assert set(result.tags) >= {"1c", "excel", "tax", "ifrs"}
    assert result.languages == ("azerbaijani", "russian")
    assert result.experience_years == 3
    assert result.employment_type == "full_time"
    assert result.higher_education is True
    assert result.work_mode is None


def test_developer_ad():
    result = analyze("Backend Developer (Python)", DEVELOPER_AD)

    assert result.category == "it"
    assert set(result.tags) == {"python", "django", "postgresql", "docker", "git"}
    assert result.languages == ("english",)
    assert result.experience_years == 2
    assert result.work_mode == "hybrid"
    assert result.higher_education is False


@pytest.mark.parametrize(
    ("title", "description", "seniority"),
    [
        ("Junior Frontend Developer", "", "junior"),
        ("Team Lead (Java)", "", "lead"),
        ("Satış üzrə təcrübəçi", "", "intern"),
        ("Data analyst", "We are looking for a senior analyst", "senior"),
        ("Mühasib", "Maliyyə rəhbərinə hesabat verir", None),
    ],
)
def test_seniority(title, description, seniority):
    assert analyze(title, description).seniority == seniority


@pytest.mark.parametrize(
    ("description", "years"),
    [
        ("3 ildən az olmayaraq iş təcrübəsi", 3),
        ("İş təcrübəsi: 1-3 il", 1),
        ("at least 5 years of experience", 5),
        ("Təcrübəsiz namizədlər də müraciət edə bilər", 0),
        ("Təcrübə: 1 ildən 3 ilə qədər", 1),
        ("Təcrübə: 5 ildən artıq", 5),
        ("2010-cu ildən fəaliyyət göstərən şirkət", None),
        ("", None),
    ],
)
def test_experience_years(description, years):
    assert analyze("Mütəxəssis", description).experience_years == years


@pytest.mark.parametrize(
    ("description", "mode"),
    [
        ("İş uzaqdan (remote) formatdadır", "remote"),
        ("Hibrid iş rejimi", "hybrid"),
        ("Ofisdə iş", None),
    ],
)
def test_work_mode(description, mode):
    assert analyze("Developer", description).work_mode == mode


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Python/Django Developer", ("python", "django")),
        ("Frontend developer (React, TypeScript)", ("typescript", "react")),
        ("Java Developer", ("java",)),
        ("JavaScript developer", ("javascript",)),
        ("C# proqramçı", ("c#",)),
        ("ASP.NET Core developer", (".net",)),
        ("1C Proqramçı", ("1c",)),
        ("Go developer", ("go",)),
        ("React Native developer", ("react native",)),
        ("SMM menecer", ("smm",)),
        ("Mühasib", ()),
    ],
)
def test_extract_tags(title, expected):
    assert extract_tags(title) == expected


def test_skill_names_are_unique_across_groups():
    names = [skill for group in SKILL_GROUPS.values() for skill in group]
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    ("description", "has_payroll"),
    [
        ("Əmək haqqının hesablanması və uçotu", True),
        ("Payroll experience", True),
        ("Əmək haqqı: 1500 AZN", False),
        ("Əmək haqqı razılaşma yolu ilə", False),
    ],
)
def test_payroll_is_a_skill_not_a_salary_line(description, has_payroll):
    assert ("payroll" in analyze("Mühasib", description).tags) is has_payroll


def test_ai_skill():
    assert "ai" in analyze("SMM", "Süni intellekt alətləri ilə işləmək").tags
