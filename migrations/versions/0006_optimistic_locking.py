"""Enforce optimistic locking version and updated_at on game sessions

Revision ID: 0006_optimistic_locking
Revises: 0005_game_session_active_question_identity
Create Date: 2026-09-12 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_optimistic_locking"
down_revision: Union[str, None] = "0005_game_session_active_question_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure version column and index exist on OB_game_sessions
    with op.batch_alter_table("OB_game_sessions") as batch_op:
        batch_op.create_index(
            "ix_ob_game_sessions_user_version",
            ["user_id", "version"],
        )


def downgrade() -> None:
    with op.batch_alter_table("OB_game_sessions") as batch_op:
        batch_op.drop_index("ix_ob_game_sessions_user_version")
