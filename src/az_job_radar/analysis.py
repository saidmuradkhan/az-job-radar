import re
from dataclasses import dataclass


def fold(text: str) -> str:
    return text.replace("İ", "i").lower()


CATEGORIES = {
    "it": r"developer|proqramçı|proqramist|programmer|software|front-?end|back-?end|full-?stack"
    r"|devops|\bqa\b(?!/qc)|tester|data (?:analyst|scientist|engineer)|sistem administrator"
    r"|system administrator|help ?desk|\bit\b|\b1c\b|\bweb\b|mobile|android|\bios\b|cyber"
    r"|kiber|ui/ux|ux/ui|şəbəkə|network|database|\bdba\b|texniki dəstək|technical support",
    "finance": r"mühasib|accountant|accounting|audit|maliyyə|financ|kassir|cashier|iqtisadçı"
    r"|economist|treasury|vergi|\btax\b|kredit|credit|investment|investisiya",
    "hr": r"\bhr\b|insan resurs|kadr|recruit|rekrut|işə qəbul|talent",
    "marketing": r"marketinq|marketing|\bsmm\b|\bseo\b|kontent|content|brand|\bpr\b|reklam",
    "design": r"dizayn|design|qrafik|graphic|videoqraf|fotoqraf|video montaj",
    "legal": r"hüquq|lawyer|legal|vəkil|compliance",
    "healthcare": r"həkim|doctor|tibb|nurse|əczaçı|pharmac|stomatoloq|dentist|laborant",
    "education": r"müəllim|teacher|təlimçi|trainer|tərbiyəçi|tutor|ielts|repetitor|instructor",
    "customer_service": r"operator|call ?cent|çağrı mərkəzi|müştəri xidm"
    r"|customer (?:service|support)",
    "hospitality": r"ofisiant|waiter|aşpaz|\bchef\b|\bcook\b|barmen|barista|\botel|hotel"
    r"|resepş|reception|turizm|tourism|reservation",
    "logistics": r"logist|sürücü|driver|anbar|warehouse|kuryer|courier|ekspeditor|supply chain"
    r"|təchizat|satınalma|procurement|purchas",
    "construction": r"inşaat|construction|usta|santexnik|qaynaqçı|welder|elektrik|electrician"
    r"|smeta|memar|architect|topoqraf|çilingər",
    "engineering": r"mühəndis|engineer|texnik|technician|mexanik|qa/qc|inspektor|inspector"
    r"|keyfiyyət|quality|\bndt\b|\bhse\b|\behs\b|əməyin mühafizəsi|sətəm|əl/tmm",
    "services": r"xadimə|təmizlik|cleaner|mühafizə|security guard|inkassator|dərzi|bərbər",
    "sales": r"satış|sales|satıcı|seller|merchandiser|mağaza|store|business development",
    "admin": r"ofis|office|katib|secretary|assistant|assistent|köməkçi|administrator"
    r"|koordinator|coordinator|document control",
    "management": r"direktor|director|rəhbər|head of|manager|menecer|müdir|team lead",
}

CATEGORY_LABELS = {
    "it": "IT",
    "finance": "Finance & accounting",
    "hr": "HR",
    "marketing": "Marketing",
    "design": "Design",
    "legal": "Legal",
    "healthcare": "Healthcare",
    "education": "Education",
    "customer_service": "Customer service",
    "hospitality": "Hospitality",
    "logistics": "Logistics",
    "construction": "Construction",
    "engineering": "Engineering & quality",
    "services": "Services & security",
    "sales": "Sales",
    "admin": "Administration",
    "management": "Management",
    "other": "Other",
}

SKILL_GROUPS = {
    "Programming languages": {
        "python": r"\bpython\b",
        "java": r"\bjava\b",
        "javascript": r"\bjavascript\b|\bjs\b",
        "typescript": r"\btypescript\b",
        "c#": r"(?<!\w)c#",
        "c++": r"(?<!\w)c\+\+",
        "php": r"\bphp\b",
        "go": r"\bgolang\b|\bgo\b(?= developer| proqramçı| engineer)",
        "kotlin": r"\bkotlin\b",
        "swift": r"\bswift\b",
        "ruby": r"\bruby\b",
        "sql": r"\b(?:t-|pl/)?sql\b",
    },
    "Frameworks": {
        "django": r"\bdjango\b",
        "flask": r"\bflask\b",
        "fastapi": r"\bfastapi\b",
        "react": r"\breact(?:\.?js)?\b(?! native)",
        "react native": r"\breact native\b",
        "vue": r"\bvue(?:\.?js)?\b",
        "angular": r"\bangular\b",
        "node.js": r"\bnode(?:\.?js)?\b",
        "spring": r"\bspring\b",
        "laravel": r"\blaravel\b",
        ".net": r"\.net\b",
        "flutter": r"\bflutter\b",
    },
    "Databases": {
        "postgresql": r"\bpostgres(?:ql)?\b",
        "mysql": r"\bmysql\b",
        "ms sql": r"\bms ?sql\b|\bsql server\b",
        "oracle": r"\boracle\b",
        "mongodb": r"\bmongo(?:db)?\b",
        "redis": r"\bredis\b",
    },
    "DevOps & cloud": {
        "docker": r"\bdocker\b",
        "kubernetes": r"\bkubernetes\b|\bk8s\b",
        "aws": r"\baws\b|amazon web services",
        "azure": r"\bazure\b",
        "linux": r"\blinux\b",
        "git": r"\bgit\b|\bgithub\b|\bgitlab\b",
        "ci/cd": r"\bci/cd\b|\bjenkins\b",
    },
    "Data & BI": {
        "power bi": r"\bpower ?bi\b",
        "tableau": r"\btableau\b",
        "machine learning": r"machine learning|\bml\b|süni intellekt|\bai\b",
        "etl": r"\betl\b",
    },
    "Accounting & finance": {
        "1c": r"\b1[cс]\b",
        "ifrs": r"\bifrs\b|\bmhbs\b|beynəlxalq standart",
        "national standards": r"\bmms\b|milli mühasibat|milli standart",
        "tax": r"\bvergi|\btax(?:es|ation)?\b",
        "audit": r"\baudit",
        "acca": r"\bacca\b",
        "sap": r"\bsap\b",
        "payroll": r"əmək haqq|payroll",
    },
    "Marketing": {
        "smm": r"\bsmm\b",
        "seo": r"\bseo\b",
        "google ads": r"google ads",
        "meta ads": r"meta ads|facebook ads|instagram ads",
        "content": r"kontent|content|copywrit",
        "crm": r"\bcrm\b",
    },
    "Design": {
        "figma": r"\bfigma\b",
        "photoshop": r"photoshop",
        "illustrator": r"illustrator",
        "autocad": r"autocad",
        "3ds max": r"3ds ?max",
        "corel": r"corel",
    },
    "Office": {
        "excel": r"\bexcel\b",
        "ms office": r"ms office|microsoft office|office proqram",
        "powerpoint": r"powerpoint",
    },
    "Other": {
        "driving licence": r"sürücülük vəsiqə|driving licen[cs]e|\bb kateqoriya",
    },
}

LANGUAGES = {
    "azerbaijani": r"azərbaycan(?=[^.\n]{0,30}dil)|azerbaijani",
    "english": r"ingilis|english",
    "russian": r"\brus\b|\brus dil|russian",
    "turkish": r"türk dil|\btürk\b|turkish",
    "german": r"alman|german",
    "arabic": r"ərəb|arabic",
    "french": r"fransız|french",
    "chinese": r"çin dil|chinese",
}

TITLE_SENIORITY = {
    "intern": r"təcrübəçi|\bintern|stajor|praktiki təcrübə",
    "lead": r"\blead\b|team ?lead|head of|rəhbər",
    "senior": r"\bsenior\b|\bsr\.?\b|aparıcı|böyük mütəxəssis",
    "middle": r"\bmiddle\b|mid-level",
    "junior": r"\bjunior\b|\bjr\.?\b|kiçik mütəxəssis",
}

# Descriptions say things like "reports to the head of sales", so only plain levels count there.
DESCRIPTION_SENIORITY = {
    "intern": r"\binternship\b",
    "senior": r"\bsenior\b",
    "middle": r"\bmiddle\b",
    "junior": r"\bjunior\b",
}

WORK_MODES = {
    "remote": r"remote|uzaqdan|distant|onlayn iş",
    "hybrid": r"hibrid|hybrid",
}

EMPLOYMENT_TYPES = {
    "part_time": r"part-?time|yarım ?ştat|natamam iş",
    "project": r"freelance|layihə əsaslı|project-based",
    "full_time": r"full-?time|tam ştat|tam iş günü",
}

HIGHER_EDUCATION = re.compile(
    r"ali təhsil|təhsil: ali\b|bakalavr|bachelor|magistr|master'?s degree|university degree"
)
NO_EXPERIENCE = re.compile(
    r"təcrübəsiz|təcrübə tələb olunmur|təcrübə: yoxdur|no experience|without experience"
)
YEARS = r"(\d{1,2})\s*(?:\+|-\s*\d{1,2})?\s*(?:il|ildən|illik|years?)\b"
EXPERIENCE = re.compile(
    YEARS + r"[^.\n]{0,40}?(?:təcrübə|experience)|(?:təcrübə|experience)[^.\n\d]{0,40}?" + YEARS
)


def compile_all(patterns: dict[str, str]) -> dict[str, re.Pattern]:
    return {name: re.compile(pattern) for name, pattern in patterns.items()}


CATEGORY_PATTERNS = compile_all(CATEGORIES)
SKILL_PATTERNS = {
    skill: re.compile(pattern)
    for group in SKILL_GROUPS.values()
    for skill, pattern in group.items()
}
LANGUAGE_PATTERNS = compile_all(LANGUAGES)
TITLE_SENIORITY_PATTERNS = compile_all(TITLE_SENIORITY)
DESCRIPTION_SENIORITY_PATTERNS = compile_all(DESCRIPTION_SENIORITY)
WORK_MODE_PATTERNS = compile_all(WORK_MODES)
EMPLOYMENT_PATTERNS = compile_all(EMPLOYMENT_TYPES)


@dataclass(frozen=True, slots=True)
class Analysis:
    category: str = "other"
    tags: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    experience_years: int | None = None
    seniority: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    higher_education: bool = False


def first_match(patterns: dict[str, re.Pattern], text: str) -> str | None:
    for name, pattern in patterns.items():
        if pattern.search(text):
            return name
    return None


def all_matches(patterns: dict[str, re.Pattern], text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in patterns.items() if pattern.search(text))


def extract_tags(text: str) -> tuple[str, ...]:
    return all_matches(SKILL_PATTERNS, fold(text))


def experience_years(text: str) -> int | None:
    if NO_EXPERIENCE.search(text):
        return 0
    years = [int(a or b) for a, b in EXPERIENCE.findall(text)]
    years = [y for y in years if y <= 20]
    return min(years) if years else None


def analyze(title: str, description: str = "") -> Analysis:
    title = fold(title)
    full_text = f"{title}\n{fold(description)}"
    return Analysis(
        category=first_match(CATEGORY_PATTERNS, title) or "other",
        tags=all_matches(SKILL_PATTERNS, full_text),
        languages=all_matches(LANGUAGE_PATTERNS, fold(description)),
        experience_years=experience_years(full_text),
        seniority=first_match(TITLE_SENIORITY_PATTERNS, title)
        or first_match(DESCRIPTION_SENIORITY_PATTERNS, full_text),
        work_mode=first_match(WORK_MODE_PATTERNS, full_text),
        employment_type=first_match(EMPLOYMENT_PATTERNS, full_text),
        higher_education=bool(HIGHER_EDUCATION.search(full_text)),
    )
