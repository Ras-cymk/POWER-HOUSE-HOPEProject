-- S1-DBA-04: password reset token table (hashed, expiry, used flag).
-- Needs S1-DBA-03 (app_user) and S1-DBA-02 (trg_set_stamp, trg_block_hard_delete) applied first.
-- Structure only. No data is loaded here.
--
-- How the app uses it (S1-DEV-04, and the one-time set-password link of S1-DBA-05):
--   1. Make a random token in app code and put it in the emailed link.
--   2. Store only its SHA-256 hash here (token_hash). The token itself is never stored.
--   3. When the link is opened, hash the token again and look the hash up.
-- The database cannot tell what the token is, so a leaked copy of this table cannot be used to reset anyone's password.

CREATE TABLE password_reset_token (
    token_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT       NOT NULL REFERENCES app_user,
    token_hash  VARCHAR(64)  NOT NULL,                       -- SHA-256 as 64 hex characters
    purpose     VARCHAR(12)  NOT NULL DEFAULT 'reset'
                CONSTRAINT token_purpose_ck CHECK (purpose IN ('reset','set_password')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL,                       -- set by the app, e.g. now() + interval '30 minutes'
    is_used     BOOLEAN      NOT NULL DEFAULT FALSE,         -- the used flag: a token works only once
    used_at     TIMESTAMPTZ,
    is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    stamp       VARCHAR(120),
    CONSTRAINT token_expiry_ck CHECK (expires_at > created_at),
    CONSTRAINT token_used_ck   CHECK ((is_used AND used_at IS NOT NULL) OR (NOT is_used AND used_at IS NULL))
);

CREATE UNIQUE INDEX password_reset_token_hash_uq ON password_reset_token (token_hash);
CREATE INDEX password_reset_token_user_ix ON password_reset_token (user_id);

-- Same protection as the other tables: stamp, no hard deletes.
CREATE TRIGGER password_reset_token_biu_stamp BEFORE INSERT OR UPDATE ON password_reset_token
    FOR EACH ROW EXECUTE FUNCTION trg_set_stamp();
CREATE TRIGGER password_reset_token_bd_block BEFORE DELETE ON password_reset_token
    FOR EACH ROW EXECUTE FUNCTION trg_block_hard_delete();
CREATE TRIGGER password_reset_token_bt_block BEFORE TRUNCATE ON password_reset_token
    FOR EACH STATEMENT EXECUTE FUNCTION trg_block_hard_delete();

-- Keep Supabase's automatic public API away from this table.
ALTER TABLE password_reset_token ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE public.password_reset_token FROM anon, authenticated;
    END IF;
END;
$$;
