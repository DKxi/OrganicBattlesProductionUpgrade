"""Enable Row Level Security (RLS) on player tables and define role policies

Revision ID: 0008_least_privilege_roles_and_rls
Revises: 0007_search_indexes
Create Date: 2026-09-12 17:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0008_least_privilege_roles_and_rls"
down_revision: Union[str, None] = "0007_search_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Enable and force Row Level Security on player data tables
        op.execute("""
        DO $$
        BEGIN
            -- 1. Enable and force RLS on player tables
            ALTER TABLE IF EXISTS public."OB_game_sessions" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_game_sessions" FORCE ROW LEVEL SECURITY;

            ALTER TABLE IF EXISTS public."OB_users" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_users" FORCE ROW LEVEL SECURITY;

            ALTER TABLE IF EXISTS public."OB_auth_sessions" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_auth_sessions" FORCE ROW LEVEL SECURITY;

            ALTER TABLE IF EXISTS public."OB_player_question_progress" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_player_question_progress" FORCE ROW LEVEL SECURITY;

            ALTER TABLE IF EXISTS public."OB_answer_attempts" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_answer_attempts" FORCE ROW LEVEL SECURITY;

            ALTER TABLE IF EXISTS public."OB_verification_codes" ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_verification_codes" FORCE ROW LEVEL SECURITY;

            -- 2. Create RLS policies if ob_player_api and ob_admin_api roles exist
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_player_api') THEN
                DROP POLICY IF EXISTS player_select_own_game_session ON public."OB_game_sessions";
                CREATE POLICY player_select_own_game_session ON public."OB_game_sessions"
                    FOR SELECT TO ob_player_api
                    USING (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_insert_own_game_session ON public."OB_game_sessions";
                CREATE POLICY player_insert_own_game_session ON public."OB_game_sessions"
                    FOR INSERT TO ob_player_api
                    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_update_own_game_session ON public."OB_game_sessions";
                CREATE POLICY player_update_own_game_session ON public."OB_game_sessions"
                    FOR UPDATE TO ob_player_api
                    USING (user_id::text = current_setting('app.current_user_id', true))
                    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_select_progress ON public."OB_player_question_progress";
                CREATE POLICY player_select_progress ON public."OB_player_question_progress"
                    FOR SELECT TO ob_player_api
                    USING (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_insert_progress ON public."OB_player_question_progress";
                CREATE POLICY player_insert_progress ON public."OB_player_question_progress"
                    FOR INSERT TO ob_player_api
                    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_update_progress ON public."OB_player_question_progress";
                CREATE POLICY player_update_progress ON public."OB_player_question_progress"
                    FOR UPDATE TO ob_player_api
                    USING (user_id::text = current_setting('app.current_user_id', true))
                    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_select_attempts ON public."OB_answer_attempts";
                CREATE POLICY player_select_attempts ON public."OB_answer_attempts"
                    FOR SELECT TO ob_player_api
                    USING (user_id::text = current_setting('app.current_user_id', true));

                DROP POLICY IF EXISTS player_insert_attempts ON public."OB_answer_attempts";
                CREATE POLICY player_insert_attempts ON public."OB_answer_attempts"
                    FOR INSERT TO ob_player_api
                    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_admin_api') THEN
                DROP POLICY IF EXISTS admin_manage_game_sessions ON public."OB_game_sessions";
                CREATE POLICY admin_manage_game_sessions ON public."OB_game_sessions"
                    FOR ALL TO ob_admin_api
                    USING (true) WITH CHECK (true);

                DROP POLICY IF EXISTS admin_manage_progress ON public."OB_player_question_progress";
                CREATE POLICY admin_manage_progress ON public."OB_player_question_progress"
                    FOR ALL TO ob_admin_api
                    USING (true) WITH CHECK (true);

                DROP POLICY IF EXISTS admin_manage_attempts ON public."OB_answer_attempts";
                CREATE POLICY admin_manage_attempts ON public."OB_answer_attempts"
                    FOR ALL TO ob_admin_api
                    USING (true) WITH CHECK (true);
            END IF;
        END $$;
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
        DO $$
        BEGIN
            ALTER TABLE IF EXISTS public."OB_game_sessions" DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_users" DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_auth_sessions" DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_player_question_progress" DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_answer_attempts" DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS public."OB_verification_codes" DISABLE ROW LEVEL SECURITY;
        END $$;
        """)
