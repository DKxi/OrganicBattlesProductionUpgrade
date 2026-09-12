"""Add active question id and release version to game session

Revision ID: 0005_game_session_active_question_identity
Revises: 0004_stable_question_identity_constraints
Create Date: 2026-09-12 17:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_game_session_active_question_identity"
down_revision: Union[str, None] = "0004_stable_question_identity_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("OB_game_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("active_question_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True)
        )
        batch_op.add_column(
            sa.Column("active_question_release_id", sa.String(), nullable=True)
        )
        batch_op.create_index(
            "ix_ob_game_sessions_active_q",
            ["active_question_id", "active_question_release_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("OB_game_sessions") as batch_op:
        batch_op.drop_index("ix_ob_game_sessions_active_q")
        batch_op.drop_column("active_question_release_id")
        batch_op.drop_column("active_question_id")
