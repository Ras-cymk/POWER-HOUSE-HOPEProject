-- S1-DBA-05 (2/2): one superadmin account per team member.
--
-- THE TEAM LIST BELOW IS PROVISIONAL. Check every name and email before you merge: once this file is
-- merged and applied it cannot be edited (a mistake needs a new migration). Add or remove rows to match the team.
-- If a REPLACE_... placeholder is ever left in a row, this file stops with an error and nothing is applied.
--
-- NO PASSWORDS HERE. password_hash stays empty. Each member sets a first password through a one-time
-- link that the DB Admin issues from their own computer (python db/issue_set_password_links.py).
-- Needs the reference data from file 1/2 (the 'superadmin' role).
-- Emails are stored in lower case. If someone already registered with the same email,
-- that account is promoted to an active superadmin.

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT * FROM (VALUES
            ('Nathaniel', 'Ong', 'natho01@proton.me'),
            ('Reinz', 'Dumalag', 'kujoisgoblin@gmail.com'),
            ('Mark', 'Despi', 'davinci99@outlook.com'),
            ('Michael', 'Sibulo', 'testificate67@gmail.com'),
            ('Russ', 'Vestil', 'McFlyMarty@yahoo.com')
        ) AS t(first_name, last_name, email)
    LOOP
        IF r.first_name ILIKE '%REPLACE%' OR r.last_name ILIKE '%REPLACE%' OR r.email ILIKE '%REPLACE%' THEN
            RAISE EXCEPTION 'Fill in the real team list in this file first (placeholder found: %).', r.email;
        END IF;

        INSERT INTO app_user (email, first_name, last_name, role_code, account_status)
        VALUES (lower(trim(r.email)), trim(r.first_name), trim(r.last_name), 'superadmin', 'active')
        ON CONFLICT (lower(email)) DO UPDATE
            SET role_code = 'superadmin', account_status = 'active', is_blocked = FALSE, is_deleted = FALSE;
    END LOOP;
END;
$$;
