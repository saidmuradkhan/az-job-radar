"""Remove length limits from text columns.

The first tables had limits like VARCHAR(60), and some sites use longer ids.
SQLite ignores these limits, so only Postgres needs the change.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

COLUMNS = {
    "vacancies": [
        "uid",
        "source",
        "external_id",
        "title",
        "company",
        "url",
        "location",
        "currency",
        "category",
        "seniority",
        "work_mode",
        "employment_type",
        "duplicate_of",
    ],
    "scrape_runs": ["status"],
}


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, columns in COLUMNS.items():
        for column in columns:
            op.alter_column(table, column, type_=sa.String)


def downgrade() -> None:
    pass
