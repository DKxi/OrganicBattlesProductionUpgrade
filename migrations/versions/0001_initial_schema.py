"""Initial schema setup for Organic Battles

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-12 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. OB_users
    op.create_table(
        "OB_users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("verified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_source", sa.String(), nullable=True),
        sa.Column("avatar_json", sa.String(), nullable=True),
        sa.Column("progress_json", sa.String(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 2. OB_verification_codes
    op.create_table(
        "OB_verification_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 3. OB_auth_sessions
    op.create_table(
        "OB_auth_sessions",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 4. OB_game_sessions
    op.create_table(
        "OB_game_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("content_source", sa.String(), nullable=True),
        sa.Column("chapter", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("boss_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("player_hp", sa.Integer(), nullable=False, server_default="150"),
        sa.Column("player_max_hp", sa.Integer(), nullable=False, server_default="150"),
        sa.Column("boss_hp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_question_json", sa.String(), nullable=True),
        sa.Column("active_spell", sa.String(), nullable=True),
        sa.Column("turn_id", sa.String(), nullable=True),
        sa.Column("cooldowns_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("log_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("completed_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("rewards_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("question_cursors_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 5. OB_curricula
    op.create_table(
        "OB_curricula",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chapters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bosses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 6. OB_tracks
    op.create_table(
        "OB_tracks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("curriculum_id", sa.String(), sa.ForeignKey("OB_curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("data_folder", sa.String(), nullable=False),
        sa.Column("boss_folder", sa.String(), nullable=True),
        sa.Column("questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chapters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accent", sa.String(), nullable=False, server_default="amber"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 7. OB_questions
    op.create_table(
        "OB_questions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("track_id", sa.String(), sa.ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_id", sa.String(), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("chapter_title", sa.String(), nullable=False),
        sa.Column("boss_name", sa.String(), nullable=False),
        sa.Column("boss_slug", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=True),
        sa.Column("question_type", sa.String(), nullable=False, server_default="Multiple Choice"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("correct_option", sa.String(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("spells_json", sa.JSON(), nullable=False),
        sa.Column("health_json", sa.JSON(), nullable=False),
        sa.Column("images_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 8. OB_bosses
    op.create_table(
        "OB_bosses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("track_id", sa.String(), sa.ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("image_file", sa.String(), nullable=False),
        sa.Column("health", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("element", sa.String(), nullable=True),
        sa.Column("strategy_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 9. OB_boss_question_assignments
    op.create_table(
        "OB_boss_question_assignments",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("boss_id", sa.String(), sa.ForeignKey("OB_bosses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(), sa.ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 10. OB_player_question_progress
    op.create_table(
        "OB_player_question_progress",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(), sa.ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.Integer(), nullable=True),
        sa.Column("next_review_at", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 11. OB_answer_attempts
    op.create_table(
        "OB_answer_attempts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("OB_game_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(), nullable=False),
        sa.Column("boss_slug", sa.String(), nullable=False),
        sa.Column("spell_id", sa.String(), nullable=True),
        sa.Column("selected_option", sa.String(), nullable=False),
        sa.Column("is_correct", sa.Integer(), nullable=False),
        sa.Column("damage_dealt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("damage_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("time_taken_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 12. OB_admin_users
    op.create_table(
        "OB_admin_users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 13. OB_admin_sessions
    op.create_table(
        "OB_admin_sessions",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("admin_user_id", sa.String(), sa.ForeignKey("OB_admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.Integer(), nullable=False, server_default="0"),
    )

    # 14. OB_admin_audit_logs
    op.create_table(
        "OB_admin_audit_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("admin_user_id", sa.String(), sa.ForeignKey("OB_admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admin_username", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("OB_admin_audit_logs")
    op.drop_table("OB_admin_sessions")
    op.drop_table("OB_admin_users")
    op.drop_table("OB_answer_attempts")
    op.drop_table("OB_player_question_progress")
    op.drop_table("OB_boss_question_assignments")
    op.drop_table("OB_bosses")
    op.drop_table("OB_questions")
    op.drop_table("OB_tracks")
    op.drop_table("OB_curricula")
    op.drop_table("OB_game_sessions")
    op.drop_table("OB_auth_sessions")
    op.drop_table("OB_verification_codes")
    op.drop_table("OB_users")
