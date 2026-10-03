from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Vacancy:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    published_on: date | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    currency: str = "AZN"
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.external_id}"

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Vacancy title cannot be empty")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot be greater than salary_max")
