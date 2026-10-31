-- S1-DBA-03 (1/2): app_user (role, blocked flag), role, module, rights catalogue, user_permission (with soft delete).
-- Structure only. No data is loaded here: roles, modules and the 36 rights belong to S1-DBA-05.
-- Needs S1-DBA-02 applied first (file 2/2 reuses its stamp and hard-delete functions).
-- Same conventions as the HOPE tables: lowercase names, is_deleted (soft delete) and stamp on every table.

-- Roles (guide 1.2): superadmin, admin, user
CREATE TABLE role (
    role_code    VARCHAR(12)  NOT NULL PRIMARY KEY,
    role_name    VARCHAR(30)  NOT NULL,
    description  VARCHAR(100),
    is_deleted   BOOLEAN      NOT NULL DEFAULT FALSE,
    stamp        VARCHAR(120)
);

-- Modules shown in the sidebar and in the Rights dialog (guide 3.8)
CREATE TABLE module (
    module_code  VARCHAR(12)  NOT NULL PRIMARY KEY,
    module_name  VARCHAR(30)  NOT NULL,
    sort_order   SMALLINT     NOT NULL DEFAULT 0,
    is_deleted   BOOLEAN      NOT NULL DEFAULT FALSE,
    stamp        VARCHAR(120)
);

-- Rights catalogue: one row per checkbox in the Rights dialog (the 36 rows are loaded in S1-DBA-05)
CREATE TABLE permission (
    perm_code    VARCHAR(30)  NOT NULL PRIMARY KEY,      -- e.g. 'customers.add'
    module_code  VARCHAR(12)  NOT NULL REFERENCES module,
    perm_name    VARCHAR(40)  NOT NULL,                  -- e.g. 'Add Customer'
    sort_order   SMALLINT     NOT NULL DEFAULT 0,
    is_deleted   BOOLEAN      NOT NULL DEFAULT FALSE,
    stamp        VARCHAR(120)
);

-- Accounts that can sign in
CREATE TABLE app_user (
    user_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           VARCHAR(100) NOT NULL,
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NOT NULL,
    password_hash   VARCHAR(255),                        -- bcrypt/Argon2 hash only; NULL until the user sets a password
    role_code       VARCHAR(12)  NOT NULL DEFAULT 'user' REFERENCES role,
    account_status  VARCHAR(10)  NOT NULL DEFAULT 'pending'   -- S1-DEV-02: new users start pending; S1-DEV-06 approves them
                    CONSTRAINT account_status_ck CHECK (account_status IN ('pending','active')),
    is_blocked      BOOLEAN      NOT NULL DEFAULT FALSE, -- a blocked account cannot sign in (S1-DEV-03)
    is_deleted      BOOLEAN      NOT NULL DEFAULT FALSE,
    stamp           VARCHAR(120)
);
CREATE UNIQUE INDEX app_user_email_uq ON app_user (lower(email));

-- Which actions are allowed for a user (the ticked boxes). Unticking = soft delete, re-ticking = restore.
CREATE TABLE user_permission (
    user_id      BIGINT      NOT NULL REFERENCES app_user,
    perm_code    VARCHAR(30) NOT NULL REFERENCES permission,
    is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
    stamp        VARCHAR(120),
    PRIMARY KEY (user_id, perm_code)
);
