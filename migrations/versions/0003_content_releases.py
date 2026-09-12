"""Add content releases table and release_id columns

Revision ID: 0003_content_releases
Revises: 0002_jsonb_conversion
Create Date: 2026-09-12 17:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_content_releases"
down_revision: Union[str, None] = "0002_jsonb_conversion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create OB_content_releases
    op.create_table(
        "OB_content_releases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("track_id", sa.String(), sa.ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.Integer(), nullable=True),
    )
    op.create_index("ix_ob_content_releases_track_ver", "OB_content_releases", ["track_id", "version"])
    op.create_index("ix_ob_content_releases_track_status", "OB_content_releases", ["track_id", "status"])

    # 2. Add release_id to OB_questions
    with op.batch_alter_table("OB_questions") as batch_op:
        batch_op.add_column(sa.Column("release_id", sa.String(), nullable=True))
        batch_op.create_foreign_key("fk_ob_questions_release", "OB_content_releases", ["release_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_ob_questions_release_id", ["release_id"])

    # 3. Add release_id to OB_boss_question_assignments
    with op.batch_alter_table("OB_boss_question_assignments") as batch_op:
        batch_op.add_column(sa.Column("release_id", sa.String(), nullable=True))
        batch_op.create_foreign_key("fk_ob_bqa_release", "OB_content_releases", ["release_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_ob_bqa_release_id", ["release_id"])

    # 4. Add release_id to OB_answer_attempts
    with op.batch_alter_table("OB_answer_attempts") as batch_op:
        batch_op.add_column(sa.Column("release_id", sa.String(), nullable=True))
        batch_op.create_index("ix_ob_attempts_release_id", ["release_id"])


def downgrade() -> None:
    with op.batch_alter_table("OB_answer_attempts") as batch_op:
        batch_op.drop_index("ix_ob_attempts_release_id")
        batch_op.drop_column("release_id")

    with op.batch_alter_table("OB_boss_question_assignments") as batch_op:
        batch_op.drop_index("ix_ob_bqa_release_id")
        batch_op.drop_constraint("fk_ob_bqa_release", type_="foreignkey")
        batch_op.drop_column("release_id")

    with op.batch_alter_table("OB_questions") as batch_op:
        batch_op.drop_index("ix_ob_questions_release_id")
        batch_op.drop_constraint("fk_ob_questions_release", type_="foreignkey")
        batch_op.drop_column("release_id")

    op.drop_index("ix_ob_content_releases_track_status", table_name="OB_content_releases")
    op.drop_index("ix_ob_content_releases_track_ver", table_name="OB_content_releases")
    op.drop_table("OB_content_releases")
