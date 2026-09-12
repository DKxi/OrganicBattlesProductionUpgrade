"""Add trigram search extension, GIN indexes, and search B-tree indexes

Revision ID: 0007_search_indexes
Revises: 0006_optimistic_locking
Create Date: 2026-09-12 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007_search_indexes"
down_revision: Union[str, None] = "0006_optimistic_locking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Trigram extension and GIN indexes on PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.create_index(
            "ix_ob_questions_prompt_trgm",
            "OB_questions",
            ["prompt"],
            postgresql_using="gin",
            postgresql_ops={"prompt": "gin_trgm_ops"},
        )
        op.create_index(
            "ix_ob_questions_topic_trgm",
            "OB_questions",
            ["topic"],
            postgresql_using="gin",
            postgresql_ops={"topic": "gin_trgm_ops"},
        )
    else:
        # On SQLite / other engines, create standard B-tree indexes for fast prompt/topic prefix matching
        op.create_index("ix_ob_questions_prompt", "OB_questions", ["prompt"])
        op.create_index("ix_ob_questions_topic", "OB_questions", ["topic"])

    # 2. User search indexes
    op.create_index("ix_ob_users_username", "OB_users", ["username"])
    op.create_index("ix_ob_users_email", "OB_users", ["email"])

    # 3. Answer attempts search & telemetry indexes
    op.create_index("ix_ob_attempts_user_time", "OB_answer_attempts", ["user_id", "created_at"])
    op.create_index("ix_ob_attempts_track_time", "OB_answer_attempts", ["track_id", "created_at"])
    op.create_index("ix_ob_attempts_boss_time", "OB_answer_attempts", ["boss_slug", "created_at"])
    op.create_index("ix_ob_attempts_question_correct", "OB_answer_attempts", ["question_id", "is_correct"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_index("ix_ob_attempts_question_correct", table_name="OB_answer_attempts")
    op.drop_index("ix_ob_attempts_boss_time", table_name="OB_answer_attempts")
    op.drop_index("ix_ob_attempts_track_time", table_name="OB_answer_attempts")
    op.drop_index("ix_ob_attempts_user_time", table_name="OB_answer_attempts")

    op.drop_index("ix_ob_users_email", table_name="OB_users")
    op.drop_index("ix_ob_users_username", table_name="OB_users")

    if is_postgres:
        op.drop_index("ix_ob_questions_topic_trgm", table_name="OB_questions")
        op.drop_index("ix_ob_questions_prompt_trgm", table_name="OB_questions")
    else:
        op.drop_index("ix_ob_questions_topic", table_name="OB_questions")
        op.drop_index("ix_ob_questions_prompt", table_name="OB_questions")
