import re
from dataclasses import replace
from datetime import date

from az_job_radar.models import Vacancy

URGENT_MARK = re.compile(r"\b(?:[tT][əƏeE][cC][iİI][lL][iİI]|urgent)\b[!:.]*", re.IGNORECASE)
EDGE_JUNK = " -–—|,.!*\"'"

TECH_TAGS = {
    "python": r"\bpython\b",
    "django": r"\bdjango\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "typescript": r"\btypescript\b",
    "react": r"\breact\b",
    "vue": r"\bvue(?:\.js)?\b",
    "angular": r"\bangular\b",
    "node.js": r"\bnode(?:\.?js)?\b",
    "java": r"\bjava\b",
    "c#": r"(?<!\w)c#",
    ".net": r"\.net\b",
    "php": r"\bphp\b",
    "laravel": r"\blaravel\b",
    "go": r"\bgolang\b|\bgo\b",
    "sql": r"\b(?:sql|postgresql|mysql|oracle)\b",
    "1c": r"\b1[cс]\b",
    "docker": r"\bdocker\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "devops": r"\bdevops\b",
    "qa": r"\bqa\b|\btester\b|\btestçi\b",
    "android": r"\bandroid\b",
    "ios": r"\bios\b",
    "flutter": r"\bflutter\b",
    "data": r"\bdata\b|\bbi\b|\bpower bi\b",
    "ml": r"\bmachine learning\b|\bml\b|\bai\b|\bsüni intellekt\b",
    "ui/ux": r"\bui\b|\bux\b",
    "backend": r"\bback-?end\b",
    "frontend": r"\bfront-?end\b",
    "fullstack": r"\bfull-?stack\b",
    "sysadmin": r"\bsystem administrator\b|\bsistem administratoru?\b|\bsysadmin\b",
    "security": r"\bcyber ?security\b|\bkibertəhlükəsizlik\b",
}
TAG_PATTERNS = {tag: re.compile(pattern, re.IGNORECASE) for tag, pattern in TECH_TAGS.items()}


def clean_title(title: str) -> str:
    cleaned = URGENT_MARK.sub("", title)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(EDGE_JUNK)
    return cleaned or title.strip()


def extract_tags(text: str) -> tuple[str, ...]:
    return tuple(tag for tag, pattern in TAG_PATTERNS.items() if pattern.search(text))


def dedupe(vacancies: list[Vacancy]) -> list[Vacancy]:
    newest: dict[str, Vacancy] = {}
    for vacancy in vacancies:
        current = newest.get(vacancy.uid)
        if current is None or (vacancy.published_on or date.min) > (
            current.published_on or date.min
        ):
            newest[vacancy.uid] = vacancy
    return list(newest.values())


def process(vacancies: list[Vacancy]) -> list[Vacancy]:
    cleaned = []
    for vacancy in vacancies:
        title = clean_title(vacancy.title)
        cleaned.append(
            replace(
                vacancy,
                title=title,
                company=vacancy.company.strip(),
                tags=extract_tags(title),
            )
        )
    return dedupe(cleaned)
