from az_job_radar.models import Vacancy
from az_job_radar.phrases import frequent_phrases, has_phrases, phrase_counts, phrases_in


def make_vacancy(external_id: str, description: str) -> Vacancy:
    return Vacancy(
        source="boss.az",
        external_id=external_id,
        title="Mühasib",
        company=f"Company {external_id}",
        url=f"https://boss.az/vacancies/{external_id}",
        description=description,
    )


ADS = [
    make_vacancy("1", "Kassa əməliyyatlarının aparılması. E-qaimə ilə işləmək. Ali təhsil."),
    make_vacancy("2", "Kassa əməliyyatlarının aparılması, ilkin sənədlərin tərtibi"),
    make_vacancy("3", "İlkin sənədlərin tərtibi və kassa əməliyyatlarının aparılması"),
    make_vacancy("4", "E-qaimə, ilkin sənədlərin tərtibi, anbar uçotu"),
]


def test_phrases_skip_filler_words():
    found = phrases_in("İş təcrübəsi və 1C proqramını bilməsi")
    assert "1c proqramını" in found
    assert not any(phrase.startswith("və ") or phrase.endswith(" və") for phrase in found)


def test_frequent_phrases_count_each_vacancy_once():
    result = dict(frequent_phrases(ADS, min_count=2))

    assert result["kassa əməliyyatlarının aparılması"] == 3
    assert result["ilkin sənədlərin tərtibi"] == 3
    assert "kassa əməliyyatlarının" not in result
    assert "anbar uçotu" not in result


def test_has_phrases_matches_whole_words():
    assert has_phrases(ADS[0], ["kassa əməliyyatlarının aparılması"])
    assert has_phrases(ADS[0], ["KASSA əməliyyatlarının"])
    assert not has_phrases(ADS[3], ["kassa əməliyyatlarının aparılması"])
    assert not has_phrases(ADS[3], ["nbar uçotu"])


def test_times_and_application_phrases_are_ignored():
    found = phrases_in("İş saatı 09:00-18:00. CV-ni göndərə bilərlər, mövzu qeyd olunan")
    assert not any(any(ch.isdigit() for ch in phrase) for phrase in found)
    assert "göndərə bilərlər" not in found


def test_phrases_every_ad_uses_are_dropped_against_a_background():
    boilerplate = "Müraciət et düyməsinə klikləyin. "
    accountants = [
        make_vacancy(str(i), boilerplate + "Kassa əməliyyatlarının aparılması") for i in range(3)
    ]
    others = [make_vacancy(str(i + 10), boilerplate + "Satış planı") for i in range(9)]
    background = phrase_counts(accountants + others)

    result = dict(frequent_phrases(accountants, background=background, background_size=12))

    assert "kassa əməliyyatlarının aparılması" in result
    assert not any("düyməsinə" in phrase for phrase in result)


def test_skill_names_are_not_repeated_as_phrases():
    ads = [make_vacancy(str(i), "MS Office proqramları") for i in range(3)]
    assert "ms office" not in dict(frequent_phrases(ads))


def test_one_company_template_counts_once():
    template = [
        Vacancy(
            source="boss.az",
            external_id=str(i),
            title="Developer",
            company="Kapital Bank",
            url=f"https://boss.az/vacancies/{i}",
            description="Sizi komandamızda görməkdən məmnun olarıq",
        )
        for i in range(5)
    ]
    assert phrase_counts(template)["komandamızda görməkdən"] == 1
    assert frequent_phrases(template) == []
