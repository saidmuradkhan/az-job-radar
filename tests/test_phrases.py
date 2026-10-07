from az_job_radar.models import Vacancy
from az_job_radar.phrases import frequent_phrases, has_phrases, phrases_in


def make_vacancy(external_id: str, description: str) -> Vacancy:
    return Vacancy(
        source="boss.az",
        external_id=external_id,
        title="Mühasib",
        company="Acme",
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
