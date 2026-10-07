"""Find phrases that keep coming back in a group of vacancies, e.g. "kassa əməliyyatları"."""

import re
from collections import Counter

from az_job_radar.analysis import fold
from az_job_radar.models import Vacancy

WORD = re.compile(r"[a-zəğıöüçş0-9+#]+")
STOPWORDS = set(
    """
    və ilə üçün üzrə olan olması olmalı bilməsi bilmək biliyi bilikləri bacarığı bacarıqları
    iş işə işin işi işlər işləmək təcrübə təcrübəsi tələblər tələb namizəd namizədin namizədlər
    vəzifə vəzifələr öhdəlik öhdəliklər şərtlər şirkət şirkətin şirkətimiz bizim bir bu o da də
    ki kimi daha çox az yaxşı yüksək əla məsuliyyət həyata keçirmək etmək
    il ildən ay gün saat həftə maaş əmək haqqı azn cv göndərin ünvanına email phone mövzu
    the and of to in for with a an on as or is are be our we you your will at by from
    """.split()
)


def words(text: str) -> list[str]:
    return WORD.findall(fold(text))


def phrases_in(text: str) -> set[str]:
    """Two- and three-word phrases that are not just filler words."""
    tokens = words(text)
    found = set()
    for size in (2, 3):
        for i in range(len(tokens) - size + 1):
            gram = tokens[i : i + size]
            if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                continue
            if all(len(word) > 1 for word in gram):
                found.add(" ".join(gram))
    return found


def frequent_phrases(
    vacancies: list[Vacancy], top: int = 15, min_count: int = 3
) -> list[tuple[str, int]]:
    """Phrases used by the most vacancies (each vacancy counts once)."""
    counts = Counter()
    for vacancy in vacancies:
        counts.update(phrases_in(vacancy.description))

    picked: list[tuple[str, int]] = []
    longest_first = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    for phrase, count in longest_first:
        if count < min_count or len(picked) == top:
            break
        # Skip "kassa əməliyyatları" if "kassa əməliyyatlarının aparılması" already covers it.
        if any(phrase in longer or longer in phrase for longer, _ in picked):
            continue
        picked.append((phrase, count))
    return picked


def has_phrases(vacancy: Vacancy, wanted: list[str]) -> bool:
    text = f" {' '.join(words(vacancy.description))} "
    return all(f" {fold(phrase)} " in text for phrase in wanted)
