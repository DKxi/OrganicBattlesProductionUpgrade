"""Add stable question identity constraints and composite indexes

Revision ID: 0004_stable_question_identity_constraints
Revises: 0003_content_releases
Create Date: 2026-09-12 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_stable_question_identity_constraints"
down_revision: Union[str, None] = "0003_content_releases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. OB_questions stable ordering constraint and indexes
    with op.batch_alter_table("OB_questions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ob_questions_order",
            ["track_id", "release_id", "chapter", "order_index"],
        )
        batch_op.create_index(
            "ix_ob_questions_track_ch_order",
            ["track_id", "chapter", "order_index"],
        )
        batch_op.create_index(
            "ix_ob_questions_track_release_ch_order",
            ["track_id", "release_id", "chapter", "order_index"],
        )
        batch_op.create_index(
            "ix_ob_questions_track_ch_boss_order",
            ["track_id", "chapter", "boss_slug", "order_index"],
        )

    # 2. OB_bosses ordering constraint
    with op.batch_alter_table("OB_bosses") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ob_bosses_track_ch_order",
            ["track_id", "chapter", "order_index"],
        )
        batch_op.create_index(
            "ix_ob_bosses_track_ch_order",
            ["track_id", "chapter", "order_index"],
        )

    # 3. OB_boss_question_assignments constraint
    with op.batch_alter_table("OB_boss_question_assignments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ob_bqa_boss_question_release",
            ["boss_id", "question_id", "release_id"],
        )
        batch_op.create_index(
            "ix_ob_bqa_boss_order",
            ["boss_id", "order_index"],
        )
        batch_op.create_index(
            "ix_ob_bqa_track_release",
            ["track_id", "release_id"],
        )

    # 4. OB_player_question_progress constraint
    with op.batch_alter_table("OB_player_question_progress") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ob_pqp_user_question",
            ["user_id", "question_id"],
        )
        batch_op.create_index(
            "ix_ob_pqp_user_review",
            ["user_id", "next_review_at"],
        )
        batch_op.create_index(
            "ix_ob_pqp_user_track_mastery",
            ["user_id", "track_id", "mastery_score"],
        )


def downgrade() -> None:
    with op.batch_alter_table("OB_player_question_progress") as batch_op:
        batch_op.drop_index("ix_ob_pqp_user_track_mastery")
        batch_op.drop_index("ix_ob_pqp_user_review")
        batch_op.drop_constraint("uq_ob_pqp_user_question", type_="unique")

    with op.batch_alter_table("OB_boss_question_assignments") as batch_op:
        batch_op.drop_index("ix_ob_bqa_track_release")
        batch_op.drop_index("ix_ob_bqa_boss_order")
        batch_op.drop_constraint("uq_ob_bqa_boss_question_release", type_="unique")

    with op.batch_alter_table("OB_bosses") as batch_op:
        batch_op.drop_index("ix_ob_bosses_track_ch_order")
        batch_op.drop_constraint("uq_ob_bosses_track_ch_order", type_="unique")

    with op.batch_alter_table("OB_questions") as batch_op:
        batch_op.drop_index("ix_ob_questions_track_ch_boss_order")
        batch_op.drop_index("ix_ob_questions_track_release_ch_order")
        batch_op.drop_index("ix_ob_questions_track_ch_order")
        batch_op.drop_constraint("uq_ob_questions_order", type_="unique")
