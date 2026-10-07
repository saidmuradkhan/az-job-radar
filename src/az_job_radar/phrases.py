"""Find phrases that keep coming back in a group of vacancies, e.g. "kassa əməliyyatları"."""

import re
from collections import Counter

from az_job_radar.analysis import SKILL_PATTERNS, fold
from az_job_radar.models import Vacancy

WORD = re.compile(r"[a-zəğıöüçş0-9+#]+")
SENTENCE_BREAK = re.compile(r"[.,;:!?\n•·()|*]+")
STOPWORDS = set(
    """
    və ilə üçün üzrə olan olması olmalı bilməsi bilmək biliyi bilikləri bacarığı bacarıqları
    iş işə işin işi işlər işləmək təcrübə təcrübəsi tələblər tələb namizəd namizədin namizədlər
    vəzifə vəzifələr öhdəlik öhdəliklər şərtlər şirkət şirkətin şirkətimiz bizim bir bu o da də
    ki kimi daha çox az yaxşı yüksək əla məsuliyyət həyata keçirmək etmək
    il ildən ay gün saat həftə maaş əmək haqqı azn cv göndərin ünvanına email phone mövzu
    qeyd olunan edilməsi olunması bilər bilərlər göndərə müraciət edə edərək sətrində adını
    vakansiyanın vakansiya namizədlərin istəyən şəxslər tələb olunur
    the and of to in for with a an on as or is are be our we you your will at by from
    """.split()
)


def words(text: str) -> list[str]:
    return WORD.findall(fold(text))


SKILL_PHRASES = {" ".join(words(skill)) for skill in SKILL_PATTERNS}


def phrases_in(text: str) -> set[str]:
    """Two- and three-word phrases that are not just filler words, within one sentence."""
    found = set()
    for sentence in SENTENCE_BREAK.split(text):
        tokens = words(sentence)
        for size in (2, 3):
            for i in range(len(tokens) - size + 1):
                gram = tokens[i : i + size]
                if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                    continue
                if all(len(word) > 1 and not word.isdigit() for word in gram):
                    found.add(" ".join(gram))
    return found


def employer(vacancy: Vacancy) -> str:
    return fold(vacancy.company).strip() or vacancy.uid


def employer_count(vacancies: list[Vacancy]) -> int:
    return len({employer(vacancy) for vacancy in vacancies})


def phrase_counts(vacancies: list[Vacancy]) -> Counter:
    """How many employers use each phrase, so one company's ad template counts once."""
    employers: dict[str, set[str]] = {}
    for vacancy in vacancies:
        for phrase in phrases_in(vacancy.description):
            employers.setdefault(phrase, set()).add(employer(vacancy))
    return Counter({phrase: len(names) for phrase, names in employers.items()})


def frequent_phrases(
    vacancies: list[Vacancy],
    top: int = 15,
    min_count: int = 3,
    background: Counter | None = None,
    background_size: int = 0,
) -> list[tuple[str, int]]:
    """Phrases used by the most vacancies.

    Counts are employers, not ads. With a background (counts over all vacancies and the
    number of employers there), phrases every kind of ad uses, like a site's "apply" text,
    are dropped: a phrase must be at least twice as common here as it is everywhere.
    """
    counts = phrase_counts(vacancies)
    employers_here = employer_count(vacancies)
    picked: list[tuple[str, int]] = []
    longest_first = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    for phrase, count in longest_first:
        if count < min_count or len(picked) == top:
            break
        if phrase in SKILL_PHRASES:
            continue
        if background and background_size:
            share_here = count / employers_here
            share_everywhere = background[phrase] / background_size
            if share_here < 2 * share_everywhere:
                continue
        # Skip "kassa əməliyyatları" if "kassa əməliyyatlarının aparılması" already covers it.
        if any(phrase in longer or longer in phrase for longer, _ in picked):
            continue
        picked.append((phrase, count))
    return picked


def has_phrases(vacancy: Vacancy, wanted: list[str]) -> bool:
    text = f" {' '.join(words(vacancy.description))} "
    return all(f" {fold(phrase)} " in text for phrase in wanted)
