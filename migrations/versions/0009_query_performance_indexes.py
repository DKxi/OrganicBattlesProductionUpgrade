"""Add performance indexes for questions and boss question assignments

Revision ID: 0009_query_performance_indexes
Revises: 0008_least_privilege_roles_and_rls
Create Date: 2026-09-13 05:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0009_query_performance_indexes"
down_revision: Union[str, None] = "0008_least_privilege_roles_and_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    
    # 1. Indexes on OB_questions
    q_indexes = [idx["name"] for idx in insp.get_indexes("OB_questions")]
    if "idx_ob_questions_track_id" not in q_indexes:
        op.create_index("idx_ob_questions_track_id", "OB_questions", ["track_id"])
    if "idx_ob_questions_track_id_id" not in q_indexes:
        op.create_index("idx_ob_questions_track_id_id", "OB_questions", ["track_id", "id"])

    # 2. Indexes on OB_boss_question_assignments
    bqa_indexes = [idx["name"] for idx in insp.get_indexes("OB_boss_question_assignments")]
    if "idx_ob_bqa_question_id" not in bqa_indexes:
        op.create_index("idx_ob_bqa_question_id", "OB_boss_question_assignments", ["question_id"])
    if "idx_ob_bqa_boss_order" not in bqa_indexes:
        op.create_index("idx_ob_bqa_boss_order", "OB_boss_question_assignments", ["boss_id", "order_index"])
    if "idx_ob_bqa_boss_question" not in bqa_indexes:
        op.create_index("idx_ob_bqa_boss_question", "OB_boss_question_assignments", ["boss_id", "question_id"])
    if "idx_ob_bqa_track_release" not in bqa_indexes:
        op.create_index("idx_ob_bqa_track_release", "OB_boss_question_assignments", ["track_id", "release_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    bqa_indexes = [idx["name"] for idx in insp.get_indexes("OB_boss_question_assignments")]
    for idx_name in ["idx_ob_bqa_track_release", "idx_ob_bqa_boss_question", "idx_ob_bqa_boss_order", "idx_ob_bqa_question_id"]:
        if idx_name in bqa_indexes:
            op.drop_index(idx_name, table_name="OB_boss_question_assignments")

    q_indexes = [idx["name"] for idx in insp.get_indexes("OB_questions")]
    for idx_name in ["idx_ob_questions_track_id_id", "idx_ob_questions_track_id"]:
        if idx_name in q_indexes:
            op.drop_index(idx_name, table_name="OB_questions")
