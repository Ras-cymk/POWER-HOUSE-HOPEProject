-- S1-DBA-06: audit_user() records the logged-in user in audit_log (and in every stamp).
--
-- How it works: the application runs  select set_config('app.username', '<who>', true)  at the start of each
-- transaction that writes data. audit_user() (already in S1-DBA-02) uses that name, and falls back to the
-- database login when nothing is set (seeds, migrations, SQL Editor work).
--
-- This migration makes that safe for real names such as emails:
--   1. audit_user() cuts the name to 80 characters, so a long name can never make a write fail.
--   2. audit_log.action_by is widened from 50 to 100 characters.
--   3. stamp on the 10 HOPE tables is widened from 60 to 120 characters.
--      PostgreSQL will not change a column that a view uses, so each <table>_active view is dropped and
--      recreated around the change (same definition), and the public-API revoke is repeated for it.
-- Does NOT attach audit logging to the login tables (app_user, user_permission, ...): that is a later task.

-- 1. The name used by every stamp and audit row
CREATE OR REPLACE FUNCTION audit_user() RETURNS TEXT
LANGUAGE sql STABLE AS $$
    SELECT left(COALESCE(NULLIF(current_setting('app.username', true), ''),
                         session_user::text), 80);
$$;

-- 2. Wider action_by (widening a varchar does not rewrite the table, and audit_log has no views)
ALTER TABLE audit_log ALTER COLUMN action_by TYPE VARCHAR(100);

-- 3. Wider stamp on the 10 HOPE tables
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['employee','department','job','jobhistory','customer',
                             'sales','salesdetail','product','payment','pricehist']
    LOOP
        EXECUTE format('DROP VIEW %I', t || '_active');
        EXECUTE format('ALTER TABLE %I ALTER COLUMN stamp TYPE VARCHAR(120)', t);
        EXECUTE format('CREATE VIEW %I AS SELECT * FROM %I WHERE NOT is_deleted', t || '_active', t);
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t || '_active');
        END IF;
    END LOOP;
END;
$$;
