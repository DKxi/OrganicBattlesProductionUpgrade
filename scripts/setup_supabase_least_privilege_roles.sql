-- ============================================================================
-- Least-Privilege Supabase Database Identities & Row-Level Security (RLS)
-- Target: Supabase PostgreSQL (run as postgres superuser in SQL Editor or psql)
-- ============================================================================

-- ============================================================================
-- STEP 1: Create Login Roles and Table Owner Role
-- ============================================================================
-- ob_owner: Schema & table owner, NOLOGIN (assumed only by ob_migrator)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_owner') THEN
        CREATE ROLE ob_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_player_api') THEN
        CREATE ROLE ob_player_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 30;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_admin_api') THEN
        CREATE ROLE ob_admin_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 8;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_content_ingest') THEN
        CREATE ROLE ob_content_ingest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 2;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ob_migrator') THEN
        CREATE ROLE ob_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 2;
    END IF;
END $$;

-- Allow migrator and postgres administrator to assume ob_owner during setup and migrations
GRANT ob_owner TO ob_migrator;
GRANT ob_owner TO postgres;
GRANT CREATE ON SCHEMA public TO ob_owner;

-- Note: Set strong, independent passwords interactively or via deployment secrets:
-- \password ob_player_api
-- \password ob_admin_api
-- \password ob_content_ingest
-- \password ob_migrator


-- ============================================================================
-- STEP 2: Remove Inherited / Default Access
-- ============================================================================
REVOKE ALL ON TABLE 
    public."OB_users",
    public."OB_verification_codes",
    public."OB_auth_sessions",
    public."OB_game_sessions",
    public."OB_curricula",
    public."OB_tracks",
    public."OB_content_releases",
    public."OB_questions",
    public."OB_bosses",
    public."OB_boss_question_assignments",
    public."OB_player_question_progress",
    public."OB_answer_attempts",
    public."OB_admin_users",
    public."OB_admin_sessions",
    public."OB_admin_audit_logs"
FROM public, anon, authenticated, ob_player_api, ob_admin_api, ob_content_ingest;

-- Grant database connection and schema usage
GRANT CONNECT ON DATABASE postgres TO ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;
GRANT USAGE ON SCHEMA public TO ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;


-- ============================================================================
-- STEP 3: Grant Player-Route Privileges (ob_player_api)
-- ============================================================================
-- Read-only access to published learning content catalog
GRANT SELECT ON TABLE 
    public."OB_curricula",
    public."OB_tracks",
    public."OB_content_releases",
    public."OB_questions",
    public."OB_bosses",
    public."OB_boss_question_assignments"
TO ob_player_api;

-- Scoped DML on player accounts, verification, sessions, and progress
GRANT SELECT, INSERT, UPDATE ON TABLE public."OB_users" TO ob_player_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public."OB_verification_codes", public."OB_auth_sessions" TO ob_player_api;
GRANT SELECT, INSERT, UPDATE ON TABLE public."OB_game_sessions", public."OB_player_question_progress" TO ob_player_api;
GRANT SELECT, INSERT ON TABLE public."OB_answer_attempts" TO ob_player_api;

-- Sequence access for tables where player routes insert records
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ob_player_api;


-- ============================================================================
-- STEP 4: Grant Admin-Route Privileges (ob_admin_api)
-- ============================================================================
-- Admin reads all application, audit, and content tables
GRANT SELECT ON TABLE 
    public."OB_users",
    public."OB_verification_codes",
    public."OB_auth_sessions",
    public."OB_game_sessions",
    public."OB_curricula",
    public."OB_tracks",
    public."OB_content_releases",
    public."OB_questions",
    public."OB_bosses",
    public."OB_boss_question_assignments",
    public."OB_player_question_progress",
    public."OB_answer_attempts",
    public."OB_admin_users",
    public."OB_admin_sessions",
    public."OB_admin_audit_logs"
TO ob_admin_api;

-- Admin manages users, sessions, curricula, questions, bosses, releases, and audit logs
GRANT INSERT, UPDATE, DELETE ON TABLE 
    public."OB_users",
    public."OB_verification_codes",
    public."OB_auth_sessions",
    public."OB_game_sessions",
    public."OB_curricula",
    public."OB_tracks",
    public."OB_content_releases",
    public."OB_questions",
    public."OB_bosses",
    public."OB_boss_question_assignments",
    public."OB_player_question_progress",
    public."OB_admin_users",
    public."OB_admin_sessions"
TO ob_admin_api;

-- Audit logs are append-only for admin operations
GRANT INSERT ON TABLE public."OB_admin_audit_logs" TO ob_admin_api;

-- Grant sequence access for administrative inserts
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ob_admin_api;


-- ============================================================================
-- STEP 5: Grant Ingestion Privileges (ob_content_ingest) & Transfer Ownership
-- ============================================================================
-- Ingestion manages content catalog and releases only; NO player or admin access
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE 
    public."OB_curricula",
    public."OB_tracks",
    public."OB_content_releases",
    public."OB_questions",
    public."OB_bosses",
    public."OB_boss_question_assignments"
TO ob_content_ingest;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ob_content_ingest;

-- Ensure future sequences automatically grant usage to application roles
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;

-- Transfer table ownership to ob_owner
ALTER TABLE public."OB_users" OWNER TO ob_owner;
ALTER TABLE public."OB_verification_codes" OWNER TO ob_owner;
ALTER TABLE public."OB_auth_sessions" OWNER TO ob_owner;
ALTER TABLE public."OB_game_sessions" OWNER TO ob_owner;
ALTER TABLE public."OB_curricula" OWNER TO ob_owner;
ALTER TABLE public."OB_tracks" OWNER TO ob_owner;
ALTER TABLE public."OB_content_releases" OWNER TO ob_owner;
ALTER TABLE public."OB_questions" OWNER TO ob_owner;
ALTER TABLE public."OB_bosses" OWNER TO ob_owner;
ALTER TABLE public."OB_boss_question_assignments" OWNER TO ob_owner;
ALTER TABLE public."OB_player_question_progress" OWNER TO ob_owner;
ALTER TABLE public."OB_answer_attempts" OWNER TO ob_owner;
ALTER TABLE public."OB_admin_users" OWNER TO ob_owner;
ALTER TABLE public."OB_admin_sessions" OWNER TO ob_owner;
ALTER TABLE public."OB_admin_audit_logs" OWNER TO ob_owner;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version') THEN
        ALTER TABLE public.alembic_version OWNER TO ob_owner;
    END IF;
END $$;


-- ============================================================================
-- STEP 6: Row-Level Security (RLS) for Player-Owned Data
-- ============================================================================

-- 1. OB_game_sessions
ALTER TABLE public."OB_game_sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_game_sessions" FORCE ROW LEVEL SECURITY;

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

DROP POLICY IF EXISTS admin_manage_game_sessions ON public."OB_game_sessions";
CREATE POLICY admin_manage_game_sessions ON public."OB_game_sessions"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);

-- 2. OB_users
ALTER TABLE public."OB_users" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_users" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS player_select_own_user ON public."OB_users";
CREATE POLICY player_select_own_user ON public."OB_users"
    FOR SELECT TO ob_player_api
    USING (
        current_setting('app.current_user_id', true) IS NULL OR
        id::text = current_setting('app.current_user_id', true)
    );

DROP POLICY IF EXISTS player_insert_own_user ON public."OB_users";
CREATE POLICY player_insert_own_user ON public."OB_users"
    FOR INSERT TO ob_player_api
    WITH CHECK (true);

DROP POLICY IF EXISTS player_update_own_user ON public."OB_users";
CREATE POLICY player_update_own_user ON public."OB_users"
    FOR UPDATE TO ob_player_api
    USING (id::text = current_setting('app.current_user_id', true))
    WITH CHECK (id::text = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS admin_manage_users ON public."OB_users";
CREATE POLICY admin_manage_users ON public."OB_users"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);

-- 3. OB_auth_sessions
ALTER TABLE public."OB_auth_sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_auth_sessions" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS player_manage_auth_sessions ON public."OB_auth_sessions";
CREATE POLICY player_manage_auth_sessions ON public."OB_auth_sessions"
    FOR ALL TO ob_player_api
    USING (
        current_setting('app.current_user_id', true) IS NULL OR
        user_id::text = current_setting('app.current_user_id', true)
    )
    WITH CHECK (
        current_setting('app.current_user_id', true) IS NULL OR
        user_id::text = current_setting('app.current_user_id', true)
    );

DROP POLICY IF EXISTS admin_manage_auth_sessions ON public."OB_auth_sessions";
CREATE POLICY admin_manage_auth_sessions ON public."OB_auth_sessions"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);

-- 4. OB_player_question_progress
ALTER TABLE public."OB_player_question_progress" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_player_question_progress" FORCE ROW LEVEL SECURITY;

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

DROP POLICY IF EXISTS admin_manage_progress ON public."OB_player_question_progress";
CREATE POLICY admin_manage_progress ON public."OB_player_question_progress"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);

-- 5. OB_answer_attempts
ALTER TABLE public."OB_answer_attempts" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_answer_attempts" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS player_select_attempts ON public."OB_answer_attempts";
CREATE POLICY player_select_attempts ON public."OB_answer_attempts"
    FOR SELECT TO ob_player_api
    USING (user_id::text = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS player_insert_attempts ON public."OB_answer_attempts";
CREATE POLICY player_insert_attempts ON public."OB_answer_attempts"
    FOR INSERT TO ob_player_api
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS admin_manage_attempts ON public."OB_answer_attempts";
CREATE POLICY admin_manage_attempts ON public."OB_answer_attempts"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);

-- 6. OB_verification_codes
ALTER TABLE public."OB_verification_codes" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."OB_verification_codes" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS player_manage_verification ON public."OB_verification_codes";
CREATE POLICY player_manage_verification ON public."OB_verification_codes"
    FOR ALL TO ob_player_api
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS admin_manage_verification ON public."OB_verification_codes";
CREATE POLICY admin_manage_verification ON public."OB_verification_codes"
    FOR ALL TO ob_admin_api
    USING (true) WITH CHECK (true);
