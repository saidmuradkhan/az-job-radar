from datetime import date

import pytest

from az_job_radar.duplicates import company_key, find_duplicates, same_job, similarity
from az_job_radar.models import Vacancy


def make_vacancy(source, external_id, title, company, **extra) -> Vacancy:
    return Vacancy(
        source=source,
        external_id=external_id,
        title=title,
        company=company,
        url=f"https://{source}/{external_id}",
        **extra,
    )


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("PASHA Bank ASC", "Pasha Bank"),
        ('"Kapital Bank" ASC', "Kapital Bank"),
        ("Azərsun Holding MMC", "Azersun Holding"),
        ("ABC LLC", "abc"),
    ],
)
def test_company_names_are_normalized(a, b):
    assert company_key(a) == company_key(b)


def test_different_companies_have_different_keys():
    assert company_key("Kapital Bank") != company_key("Kapital Holding")


@pytest.mark.parametrize(
    ("a", "b", "similar"),
    [
        ("Backend developer", "Back-end Developer", True),
        ("Baş mühasib", "BAŞ MÜHASİB", True),
        ("Mühasib", "Baş mühasib", False),
        ("Python Developer", "Java Developer", False),
        ("Satış təmsilçisi", "Satış meneceri", False),
    ],
)
def test_title_similarity(a, b, similar):
    assert (similarity(a, b) >= 0.85) is similar


def test_same_job_on_two_sites():
    boss = make_vacancy("boss.az", "1", "Baş mühasib", "Azersun Holding MMC")
    hellojob = make_vacancy("hellojob.az", "9", "Baş Mühasib", "Azərsun Holding")
    assert same_job(boss, hellojob)


def test_same_site_is_never_a_cross_site_duplicate():
    first = make_vacancy("boss.az", "1", "Baş mühasib", "Azersun")
    second = make_vacancy("boss.az", "2", "Baş mühasib", "Azersun")
    assert not same_job(first, second)


def test_old_and_new_posting_are_different_jobs():
    old = make_vacancy("boss.az", "1", "Mühasib", "Acme", published_on=date(2026, 1, 10))
    new = make_vacancy("hellojob.az", "2", "Mühasib", "Acme", published_on=date(2026, 10, 1))
    assert not same_job(old, new)


def test_hidden_company_matches_by_description():
    text = "Tələblər: 1C, Excel, 3 il təcrübə. Bakı şəhəri, tam ştat. " * 5
    visible = make_vacancy("boss.az", "1", "Mühasib", "Acme", description=text)
    hidden = make_vacancy("jobsearch.az", "2", "Mühasib", "", description=text)
    unrelated = make_vacancy("ejob.az", "3", "Mühasib", "", description="Başqa iş")

    assert same_job(visible, hidden)
    assert not same_job(visible, unrelated)


def test_find_duplicates_groups_three_sites_and_keeps_the_richest_copy():
    postings = [
        make_vacancy("boss.az", "1", "Python Developer", "PASHA Bank ASC"),
        make_vacancy(
            "hellojob.az", "2", "Python developer", "Pasha Bank", description="Django, 2 il"
        ),
        make_vacancy("smartjob.az", "3", "Python Developer", "PASHA Bank"),
        make_vacancy("boss.az", "4", "Java Developer", "PASHA Bank ASC"),
    ]

    duplicates = find_duplicates(postings)

    assert duplicates == {"boss.az:1": "hellojob.az:2", "smartjob.az:3": "hellojob.az:2"}


def test_find_duplicates_prefers_the_oldest_copy_when_equally_rich():
    postings = [
        make_vacancy("ejob.az", "5", "Mühasib", "Acme", published_on=date(2026, 10, 3)),
        make_vacancy("boss.az", "7", "Mühasib", "Acme", published_on=date(2026, 10, 1)),
    ]

    assert find_duplicates(postings) == {"ejob.az:5": "boss.az:7"}


def test_no_duplicates():
    postings = [
        make_vacancy("boss.az", "1", "Mühasib", "Acme"),
        make_vacancy("ejob.az", "2", "Satış meneceri", "Acme"),
    ]
    assert find_duplicates(postings) == {}
