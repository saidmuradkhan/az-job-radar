"""Create the vacancies and scrape_runs tables.

Databases set up before migrations existed already have them, so they are only
created when missing.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = sa.inspect(op.get_bind()).get_table_names()

    if "vacancies" not in existing:
        op.create_table(
            "vacancies",
            sa.Column("uid", sa.String, primary_key=True),
            sa.Column("source", sa.String, nullable=False, index=True),
            sa.Column("external_id", sa.String, nullable=False),
            sa.Column("title", sa.String, nullable=False),
            sa.Column("company", sa.String, nullable=False),
            sa.Column("url", sa.String, nullable=False),
            sa.Column("location", sa.String),
            sa.Column("published_on", sa.Date),
            sa.Column("salary_min", sa.Numeric(12, 2)),
            sa.Column("salary_max", sa.Numeric(12, 2)),
            sa.Column("currency", sa.String, nullable=False),
            sa.Column("description", sa.Text, nullable=False),
            sa.Column("category", sa.String, nullable=False, index=True),
            sa.Column("tags", sa.JSON, nullable=False),
            sa.Column("languages", sa.JSON, nullable=False),
            sa.Column("experience_years", sa.Integer),
            sa.Column("seniority", sa.String),
            sa.Column("work_mode", sa.String),
            sa.Column("employment_type", sa.String),
            sa.Column("higher_education", sa.Boolean, nullable=False),
            sa.Column("duplicate_of", sa.String, index=True),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, index=True),
        )

    if "scrape_runs" not in existing:
        op.create_table(
            "scrape_runs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String, nullable=False),
            sa.Column("found", sa.Integer, nullable=False),
            sa.Column("new", sa.Integer, nullable=False),
            sa.Column("duplicates", sa.Integer, nullable=False),
            sa.Column("error", sa.Text),
        )


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("vacancies")
