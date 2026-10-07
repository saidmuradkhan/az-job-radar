"""Find the same job posted by one company on several sites."""

import re
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from typing import Protocol

from az_job_radar.analysis import fold

TRANSLIT = str.maketrans("əıöüçşğ", "eioucsg")
LEGAL_FORMS = re.compile(
    r"\b(?:mmc|asc|qsc|aşc|llc|ltd|limited|inc|jsc|cjsc|company|şirkəti|firması)\b"
)
TITLE_THRESHOLD = 0.85
DESCRIPTION_THRESHOLD = 0.9
MAX_DAYS_APART = 30


class Posting(Protocol):
    uid: str
    source: str
    title: str
    company: str
    description: str
    published_on: date | None


def normalize(text: str) -> str:
    text = fold(text).translate(TRANSLIT)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def company_key(company: str) -> str:
    return normalize(LEGAL_FORMS.sub(" ", fold(company).translate(TRANSLIT)))


def similarity(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    words_a, words_b = set(a.split()), set(b.split())
    overlap = len(words_a & words_b) / len(words_a | words_b)
    return max(overlap, SequenceMatcher(None, a, b).ratio())


def close_in_time(a: Posting, b: Posting) -> bool:
    if a.published_on is None or b.published_on is None:
        return True
    return abs((a.published_on - b.published_on).days) <= MAX_DAYS_APART


def same_job(a: Posting, b: Posting) -> bool:
    if a.source == b.source or not close_in_time(a, b):
        return False
    if similarity(a.title, b.title) < TITLE_THRESHOLD:
        return False
    if company_key(a.company) and company_key(a.company) == company_key(b.company):
        return True
    # Some sites hide the company, so fall back to comparing the full text.
    return (
        bool(a.description and b.description)
        and similarity(a.description[:1500], b.description[:1500]) >= DESCRIPTION_THRESHOLD
    )


def keep_order(posting: Posting) -> tuple:
    """The copy with a description and a company wins, then the oldest one."""
    return (
        not posting.description,
        not posting.company,
        posting.published_on or date.max,
        posting.uid,
    )


def candidate_pairs(postings: list[Posting]):
    by_company: dict[str, list[Posting]] = defaultdict(list)
    by_word: dict[str, list[Posting]] = defaultdict(list)
    for posting in postings:
        by_company[company_key(posting.company)].append(posting)
        for word in set(normalize(posting.title).split()):
            by_word[word].append(posting)

    for key, group in by_company.items():
        if not key:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                yield a, b

    for a in by_company.get("", []):
        seen = set()
        for word in set(normalize(a.title).split()):
            for b in by_word[word]:
                if b.uid != a.uid and b.uid not in seen:
                    seen.add(b.uid)
                    yield a, b


def find_duplicates(postings: list[Posting]) -> dict[str, str]:
    """Map the uid of every duplicate to the uid of the copy we keep."""
    parent = {p.uid: p.uid for p in postings}

    def root(uid: str) -> str:
        while parent[uid] != uid:
            uid = parent[uid]
        return uid

    for a, b in candidate_pairs(postings):
        if root(a.uid) != root(b.uid) and same_job(a, b):
            parent[root(a.uid)] = root(b.uid)

    groups: dict[str, list[Posting]] = defaultdict(list)
    for posting in postings:
        groups[root(posting.uid)].append(posting)

    duplicates = {}
    for members in groups.values():
        keep = min(members, key=keep_order)
        for posting in members:
            if posting is not keep:
                duplicates[posting.uid] = keep.uid
    return duplicates
