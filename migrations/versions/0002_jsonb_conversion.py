"""Enforce and convert JSON columns to JSONB on PostgreSQL

Revision ID: 0002_jsonb_conversion
Revises: 0001_initial_schema
Create Date: 2026-09-12 17:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_jsonb_conversion"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Convert text or generic json columns to PostgreSQL JSONB
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "options_json" TYPE JSONB USING "options_json"::jsonb;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "spells_json" TYPE JSONB USING "spells_json"::jsonb;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "health_json" TYPE JSONB USING "health_json"::jsonb;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "images_json" TYPE JSONB USING "images_json"::jsonb;')
        op.execute('ALTER TABLE "OB_bosses" ALTER COLUMN "strategy_json" TYPE JSONB USING "strategy_json"::jsonb;')
        op.execute('ALTER TABLE "OB_admin_audit_logs" ALTER COLUMN "details_json" TYPE JSONB USING "details_json"::jsonb;')


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "options_json" TYPE JSON USING "options_json"::json;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "spells_json" TYPE JSON USING "spells_json"::json;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "health_json" TYPE JSON USING "health_json"::json;')
        op.execute('ALTER TABLE "OB_questions" ALTER COLUMN "images_json" TYPE JSON USING "images_json"::json;')
        op.execute('ALTER TABLE "OB_bosses" ALTER COLUMN "strategy_json" TYPE JSON USING "strategy_json"::json;')
        op.execute('ALTER TABLE "OB_admin_audit_logs" ALTER COLUMN "details_json" TYPE JSON USING "details_json"::json;')
