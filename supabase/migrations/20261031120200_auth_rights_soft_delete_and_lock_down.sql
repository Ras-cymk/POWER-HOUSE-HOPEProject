-- S1-DBA-03 (2/2): soft-delete protection and *_active views for the new tables, then lock down the public API.
-- Uses trg_set_stamp() and trg_block_hard_delete() from S1-DBA-02.
-- Audit logging (audit_log) for these tables is NOT attached here: that belongs to S1-DBA-06 / S1-DEV-07.

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT unnest(ARRAY['role','module','permission','app_user','user_permission']) AS tbl
    LOOP
        EXECUTE format('CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %I
                        FOR EACH ROW EXECUTE FUNCTION trg_set_stamp()',
                       r.tbl || '_biu_stamp', r.tbl);
        EXECUTE format('CREATE TRIGGER %I BEFORE DELETE ON %I
                        FOR EACH ROW EXECUTE FUNCTION trg_block_hard_delete()',
                       r.tbl || '_bd_block', r.tbl);
        EXECUTE format('CREATE TRIGGER %I BEFORE TRUNCATE ON %I
                        FOR EACH STATEMENT EXECUTE FUNCTION trg_block_hard_delete()',
                       r.tbl || '_bt_block', r.tbl);

        IF r.tbl <> 'app_user' THEN
            EXECUTE format('CREATE VIEW %I AS SELECT * FROM %I WHERE NOT is_deleted',
                           r.tbl || '_active', r.tbl);
        END IF;
    END LOOP;
END;
$$;

-- app_user_active leaves out password_hash on purpose. Login reads the app_user table directly.
CREATE VIEW app_user_active AS
    SELECT user_id, email, first_name, last_name, role_code, account_status, is_blocked, is_deleted, stamp
      FROM app_user
     WHERE NOT is_deleted;

-- Keep Supabase's automatic public API away from these tables (same approach as the HOPE tables).
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['role','module','permission','app_user','user_permission'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t);
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t || '_active');
        END IF;
    END LOOP;
END;
$$;
