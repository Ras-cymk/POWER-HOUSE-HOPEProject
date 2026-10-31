-- S1-DBA-02 (4/4): keep Supabase's automatic public API away from the HOPE tables.
-- The app connects server-side as the database owner, which bypasses RLS and these revokes.
-- Views run with their owner's rights, so RLS alone would NOT protect the *_active views: revoke them too.
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['employee','department','job','jobhistory','customer',
                             'sales','salesdetail','product','payment','pricehist','audit_log']
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t);
            IF t <> 'audit_log' THEN
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t || '_active');
            END IF;
        END IF;
    END LOOP;
END;
$$;

-- Future tables created by this role are not handed to the public API automatically.
-- Every later migration that creates a table should still end with ENABLE ROW LEVEL SECURITY.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
    END IF;
END;
$$;
