## 1. What you need first

| Tool | Check it works | Download |
|---|---|---|
| Git | `git --version` | https://git-scm.com |
| Python 3.10 or newer | `python --version` | https://www.python.org |
| A GitHub account with access to this repo | You accepted the collaborator invite | https://github.com |
| A code editor (VS Code recommended) | | https://code.visualstudio.com |

You also need the **database password** from the DB Admin (see step 5). It is never posted in the repo or in group chats.


## 2. Get the code

Message the SCRUM Master for details.

## 3. Create your Python environment

A virtual environment keeps this project's packages separate from the rest of your computer.

**Windows (Git Bash or PowerShell)**
```bash
python -m venv .venv
.venv\Scripts\activate
```


You should now see `(.venv)` at the start of your terminal line. Then install the packages:

```bash
pip install -r requirements.txt
```

You must activate the environment (the `activate` line) every time you open a new terminal.


## 4. Create your `.env` file

The `.env` file holds your private connection string. It lives only on your computer and is **never** committed to GitHub (it is listed in `.gitignore`).

1. Copy the template:
   - Windows PowerShell: `copy .env.example .env`
2. Open `.env` in your editor. It contains one line:
   ```
   DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres
   ```
3. Replace the placeholders with the real values (ask the DB Admin for the full string, or see step 5).

**Rules for this line**
- No spaces around `=` and no quotes around the value.
- Do not keep the square brackets from Supabase's template (`[YOUR-PASSWORD]` is replaced entirely by the password).
- Make sure the file is named exactly `.env` (not `.env.txt`).


## 5. Where to get the connection string

The DB Admin owns the Supabase project. Ask them for the **Session pooler** connection string and the database password through a private channel (a password manager or a private message).

For the DB Admin: in the Supabase dashboard click **Connect**, choose **Session pooler**, and copy the string. Use the *Session pooler*, **not** *Direct connection*. The direct connection only works over IPv6, which many home and school networks do not support, and it fails with confusing timeout errors.


## 6. Check your connection and apply the migrations

```bash
python db/migrate.py status
```

This lists every migration file as `applied` or `PENDING` and changes nothing. If you see the list, your connection works.

To apply everything that is pending:

```bash
python db/migrate.py
```

Run it again any time after you `git pull`. It is safe to run repeatedly: files that were already applied are skipped.

**What the script does**
1. Reads `DATABASE_URL` from your `.env`.
2. Finds the files in `supabase/migrations/` and sorts them by name.
3. Checks which ones the database has already recorded as done.
4. Runs each new file in order. Each file runs as a single all-or-nothing transaction, so a failed file leaves nothing half-applied.
5. Records every applied file in `supabase_migrations.schema_migrations`.


## 7. How to change the database

All database changes go through a migration file and a pull request. **Do not change tables by hand in the Supabase dashboard.**

1. Make sure you are up to date:
   ```bash
   git checkout main
   git pull
   python db/migrate.py
   ```
2. Create a branch named after your task:
   ```bash
   git checkout -b s1-dba-02-base-tables
   ```
3. Add a new file in `supabase/migrations/` named:
   ```
   YYYYMMDDHHMMSS_what_it_does.sql
   ```
   - The timestamp uses **24-hour time**, with no dashes, colons or spaces.
   - Example: `20261029153000_create_app_user.sql` means 29 Oct 2026, 3:30:00 PM.
   - The number must be **larger** than every existing file, so it runs last.
   - Use lowercase letters, numbers and underscores in the description.
4. Write your SQL in the file, then test it:
   ```bash
   python db/migrate.py
   ```
5. Commit, push and open a pull request:
   ```bash
   git add .
   git commit -m "S1-DBA-02: create base tables"
   git push -u origin s1-dba-02-base-tables
   ```
   Then open the pull request on GitHub, add the PR link to the sprint task sheet, and ask a teammate to review.

Golden rules

- **Never edit a migration file after it has been merged.** The database already recorded it as done and will not run it again. Fix mistakes by adding a **new** migration.
- **Never reuse a timestamp** or add a file with an older timestamp than existing ones.
- **No passwords, tokens or real personal data** in any file in the repo.
- **One task = one pull request.**


## 8. Never commit secrets

- `.env` must never appear in `git status`. Check before every commit.
- If a password was committed or pushed by mistake: tell the DB Admin immediately. The password must be reset in Supabase (Project Settings → Database → Reset database password) even if you delete the file afterward, because it stays in Git history.


## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `DATABASE_URL is missing` | `.env` does not exist, is misnamed (`.env.txt`), or is not in the repo's top folder. |
| Connection **timeout** or "network is unreachable" | You are using the Direct connection string. Switch to the **Session pooler** string. |
| `password authentication failed` | Wrong password, brackets left in, special characters not encoded, or a stale `.env` after a password reset. |
| `could not translate host name` | Typo in the host part, or no internet connection. |
| `Bad file name(s)` | A migration is not named `YYYYMMDDHHMMSS_description.sql` (14 digits, then `_`, then lowercase text). |
| `FAILED on <file>` | There is an error in that SQL file. Nothing from it was applied. Fix the file (if it is not yet merged) and run again. |
| `ModuleNotFoundError: psycopg2` or `dotenv` | The virtual environment is not active, or you skipped `pip install -r requirements.txt`. |
| `python` is not recognized | Python is not installed or not on your PATH. On Mac/Linux try `python3`. |
| `.env` shows up in `git status` | `.gitignore` is missing the `.env` line. Add it, then run `git rm --cached .env`. |


## 10. Project layout


TBA



## 11. Who to ask


Database password, Supabase access, migration problems - DB Admin 
GitHub access, branch rules, pull request templates - Scrum Master 
Anything else - Post it in the GC 

---


## END OF MESSAGE 


---

## ADDENDA (one per task ID)

Each addendum below belongs to **one task** and can be read on its own. New tasks add a new addendum at the bottom.

| Addendum | Task | Migration file(s) | What it covers |
|---|---|---|---|
| [0](#addendum-0-how-to-run-the-examples-all-tasks) | All tasks | n/a | How to run the sample SQL safely |
| [S1-DBA-03](#addendum-s1-dba-03-login-and-rights-tables) | S1-DBA-03 | `20261101000100_auth_rights_tables.sql`, `20261101000200_auth_rights_soft_delete_and_lock_down.sql` | `app_user`, `role`, `module`, `permission`, `user_permission` |
| [S1-DBA-04](#addendum-s1-dba-04-password-reset-token-table) | S1-DBA-04 | `20261102000100_password_reset_token.sql` | `password_reset_token` |

---

## ADDENDUM 0: How to run the examples (all tasks)

The task addenda below use the three ways described here. Read this once.

### Get ready (once, and after every `git pull`)

```bash
git checkout main
git pull
python db/migrate.py status
```

Each task addendum lists the migration files it needs. If a file shows `PENDING`, run `python db/migrate.py`. If it is not listed at all, the DB Admin has not merged it yet.

### Three ways to run an example

**Way 1: Supabase SQL Editor (best for trying things out)**

1. Ask the DB Admin to add you to the Supabase project, then open the dashboard → **SQL Editor** → **New query**.
2. Paste the example **inside `begin;` and `rollback;`** (see the box below).
3. Click **Run**. The result appears in the table at the bottom.

**Way 2: From your own app code (what you will do for real)**

Your Express server already connects with `DATABASE_URL` (S1-DEV-01). Run the same SQL through the connection pool, and pass values as parameters (`$1`, `$2`), never by joining text into the query:

```js
const { rows } = await pool.query(
  'select user_id, email, role_code, account_status from app_user_active where lower(email) = lower($1)',
  ['abcef12345@gmail.com']
);
console.log(rows);
```

**Way 3: Through your own API route**

If your route exists (for example the register route from S1-DEV-02):
```bash
curl -i -X POST http://localhost:3000/api/register -H "Content-Type: application/json" \
  -d '{"firstName":"John","lastName":"Doe","email":"abcef12345@gmail.com"}'
```
Then look at the result with Way 1 (`select * from app_user_active;`).

> **Always test inside a transaction that you roll back.**
> ```sql
> begin;
> -- your test statements here
> rollback;   -- undoes everything, so no test rows are left behind
> ```
> Rows can **never be hard-deleted** in this database (the database refuses `DELETE` and `TRUNCATE`). A test row you commit stays forever, and its email stays taken. If you ran something without `rollback` by mistake, soft-delete it: `update app_user set is_deleted = true where email = '...';`
>
> Changing the *structure* (tables, columns) is still only done through migration files, never in the SQL Editor.

## END OF ADDENDUM 0

---

## ADDENDUM S1-DBA-03: Login and rights tables

**Task:** Migration: `app_user` (role, blocked flag), `role`, `module`, rights catalogue, `user_permission` (with soft delete).
**For:** Developers building register, login and the rights dialog.

### Before you start

`python db/migrate.py status` must show these as `applied`:
- `20261101000100_auth_rights_tables.sql`
- `20261101000200_auth_rights_soft_delete_and_lock_down.sql`

### The tables

| Table | What a row is | Key | Filled by |
|---|---|---|---|
| `role` | A role: `superadmin`, `admin`, `user` | `role_code` | S1-DBA-05 (empty until then) |
| `module` | A module: `customer`, `product`, `hr`, `sales`, `reports` | `module_code` | S1-DBA-05 (empty until then) |
| `permission` | One checkbox in the Rights dialog, e.g. `customers.add` | `perm_code` | S1-DBA-05 (the 36 rights) |
| `app_user` | An account that can sign in | `user_id` (automatic) | The Register screen |
| `user_permission` | An action **ticked** for a user | `user_id` + `perm_code` | The Rights dialog |

Until S1-DBA-05 is merged, `role`, `module` and `permission` are empty, and registering fails because `app_user.role_code` points to the `user` role. Use the test setup below.

### 0. Test setup (only until S1-DBA-05 is merged)

Put this at the top of your `begin; ... rollback;` block:

```sql
insert into role (role_code, role_name) values ('user', 'User') on conflict (role_code) do nothing;
insert into role (role_code, role_name) values ('admin', 'Admin') on conflict (role_code) do nothing;
insert into module (module_code, module_name, sort_order) values ('customer', 'Customer Management', 1) on conflict (module_code) do nothing;
insert into permission (perm_code, module_code, perm_name, sort_order)
values ('customers.add', 'customer', 'Add Customer', 1) on conflict (perm_code) do nothing;
```

Once S1-DBA-05 is merged these rows exist for real, and you can delete this block from your test.

### 1. Register a new user

This is what the Register screen does. New accounts are `user` and `pending` by default.

```sql
insert into app_user (email, first_name, last_name, password_hash)
values ('abcef12345@gmail.com', 'John', 'Doe', '<bcrypt-or-argon2-hash-from-your-code>')
returning user_id, email, role_code, account_status;
```

- **Never put a plain-text password here.** Hash it in the app code first (bcrypt or Argon2).
- The Register form has no password field, so a real registration leaves `password_hash` out. It stays empty until the user sets a password.
- The same email in any capital letters counts as a duplicate, so `A@x.com` and `a@x.com` collide.
- Do not fill in `is_deleted` or `stamp`. The database does it for you.

### 2. Log in (look up an account)

```sql
select user_id, password_hash, role_code, account_status, is_blocked
from app_user
where lower(email) = lower('abcef12345@gmail.com')
  and not is_deleted;
```

Compare the password against `password_hash` **in your code**. Refuse the login if `is_blocked` is true or `account_status` is not `active`.

### 3. Activate, promote, block

```sql
-- Approve a pending account
update app_user set account_status = 'active'
where lower(email) = lower('abcef12345@gmail.com');

-- Promote to admin (only an existing admin or superadmin may do this)
update app_user set role_code = 'admin'
where lower(email) = lower('abcef12345@gmail.com');

-- Block, then unblock
update app_user set is_blocked = true
where lower(email) = lower('abcef12345@gmail.com');

update app_user set is_blocked = false
where lower(email) = lower('abcef12345@gmail.com');
```

### 4. Tick (grant) a right

The right must already exist in `permission` (see step 0 for testing).

```sql
insert into user_permission (user_id, perm_code)
select user_id, 'customers.add' from app_user
where lower(email) = lower('abcef12345@gmail.com')
on conflict (user_id, perm_code) do update set is_deleted = false;
```

The `on conflict` part means: if the right was unticked before (soft-deleted), tick it again instead of failing.

### 5. Untick (revoke) a right

This is a **soft delete**: the row stays, and the stamp records who removed it.

```sql
update user_permission set is_deleted = true
where perm_code = 'customers.add'
  and user_id = (select user_id from app_user where lower(email) = lower('abcef12345@gmail.com'));
```

Ticking it again (step 4) restores it.

### 6. Read what a user may do

```sql
select p.perm_code
from user_permission up
join permission p on p.perm_code = up.perm_code
where up.user_id = 1 and not up.is_deleted;
```

Replace `1` with the real `user_id`. In app code, pass it as a parameter (`$1`), never by pasting text into the query.

### 7. List accounts for the User Management screen

```sql
select user_id, email, first_name, last_name, role_code, account_status, is_blocked, stamp
from app_user_active
order by last_name;
```

`app_user_active` hides deleted accounts and never includes `password_hash`.

### Common errors (S1-DBA-03)

| Error says | Cause |
|---|---|
| duplicate key ... `app_user_email_uq` | That email is already registered (capitals do not matter). |
| violates foreign key ... `role` / `permission` / `module` | The role, right or module code does not exist yet. Check the spelling, and whether S1-DBA-05 is merged (or use step 0). |
| violates check constraint `account_status_ck` | `account_status` must be exactly `pending` or `active`. |
| the database refuses a delete | Hard deletes are blocked on purpose. Set `is_deleted = true` instead. |
| `permission denied` or empty results from the Supabase API | These tables are closed to Supabase's public API on purpose. Always go through the app's server connection (`DATABASE_URL`). |

### Rules (S1-DBA-03)

- Passwords are stored **only as hashes**. Audit logging for these tables is added later (S1-DBA-06), and it must keep hashes out of the log.
- Never add real people's data to these tables in a migration file or in the repo.
- Permanent starting data (roles, modules, the 36 rights, the first superadmin accounts) belongs in the S1-DBA-05 migration, not typed by hand.
- Rights are checked on the **server** for every request. Hiding a button is only a courtesy.

## END OF ADDENDUM S1-DBA-03

---

## ADDENDUM S1-DBA-04: Password reset token table

**Task:** Migration: password reset token table (hashed, expiry, used flag).
**For:** Developers building reset password (S1-DEV-04) and the set-password link for a first login.

### Before you start

- Complete the S1-DBA-03 addendum prerequisites first. This table points to `app_user`.
- `python db/migrate.py status` must show `20261102000100_password_reset_token.sql` as `applied`.

### The table

`password_reset_token`: one row per emailed link.

| Column | Meaning |
|---|---|
| `token_id` | Automatic number |
| `user_id` | The account the link belongs to |
| `token_hash` | **Hash** of the token (SHA-256, 64 hex characters), unique. The real token is never stored. |
| `purpose` | `reset` (forgot password, the default) or `set_password` (first-time link for a new account) |
| `created_at`, `expires_at` | When it was made and when it stops working |
| `is_used`, `used_at` | The used flag: a link works only once |
| `is_deleted`, `stamp` | Filled by the database, like every other table |

### 1. Make a token in your code

The database stores only the **hash**. The real token goes in the emailed link and nowhere else:

```js
const crypto = require('crypto');
const token = crypto.randomBytes(32).toString('hex');                    // goes in the emailed link
const hash  = crypto.createHash('sha256').update(token).digest('hex');   // goes in the database
```

### 2. Store it and use it (test in the SQL Editor)

This block uses a fake hash (`repeat('a', 64)`), the step 0 test setup from the S1-DBA-03 addendum, and a rollback:

```sql
begin;
-- Test setup (only until S1-DBA-05 is merged)
insert into role (role_code, role_name) values ('user', 'User') on conflict (role_code) do nothing;

insert into app_user (email, first_name, last_name)
values ('tokentest@example.com', 'Tok', 'Test');

-- Create a link that lasts 30 minutes
insert into password_reset_token (user_id, token_hash, purpose, expires_at)
select user_id, repeat('a', 64), 'reset', now() + interval '30 minutes'
from app_user where lower(email) = 'tokentest@example.com';

-- Use the link. In one statement, so a link can only work once.
update password_reset_token
set is_used = true, used_at = now()
where token_hash = repeat('a', 64) and purpose = 'reset'
  and not is_used and not is_deleted and expires_at > now()
returning user_id;

-- Use the same link again. This must return NO rows (it was already used).
update password_reset_token
set is_used = true, used_at = now()
where token_hash = repeat('a', 64) and purpose = 'reset'
  and not is_used and not is_deleted and expires_at > now()
returning user_id;
rollback;
```

The result panel shows only the last statement, so seeing **no rows** means the second use was refused, which is correct.

### 3. In your app code

Hash the token from the link, then use the same single statement:

```js
const hash = crypto.createHash('sha256').update(tokenFromLink).digest('hex');
const { rows } = await pool.query(
  `update password_reset_token
      set is_used = true, used_at = now()
    where token_hash = $1 and purpose = 'reset'
      and not is_used and not is_deleted and expires_at > now()
    returning user_id`,
  [hash]
);
if (rows.length === 0) { /* invalid, expired or already used */ }
```

### Common errors (S1-DBA-04)

| Error says | Cause |
|---|---|
| duplicate key ... `password_reset_token_hash_uq` | That token hash already exists. Tokens must be random. |
| violates foreign key ... `user_id` | The user does not exist. |
| violates check constraint `token_purpose_ck` | `purpose` must be exactly `reset` or `set_password`. |
| violates check constraint `token_expiry_ck` or `token_used_ck` | The expiry must be in the future, and a used token needs `used_at` set. |
| the database refuses a delete | Hard deletes are blocked on purpose. Mark the token used instead. |

### Rules (S1-DBA-04)

- Your code decides how long a link lasts. Agree on the times with the team (for example 30 minutes for a reset).
- No row returned means the link is invalid, expired or already used. Show the same generic message for all three.
- When you issue a new link, invalidate the user's older unused links.
- **Never log or print a token or its hash.** Audit logging (S1-DBA-06) must also keep `token_hash` out of the log.

## END OF ADDENDUM S1-DBA-04

## Self notes: 
Find users who are pending
```sql
select user_id, email, first_name, last_name, role_code, account_status, is_blocked, stamp
from app_user
where account_status = 'pending' and not is_deleted
order by user_id;
```

Activate an account
```sql
update app_user
set account_status = 'active'
where lower(email) = lower('someone@example.com')
  and account_status = 'pending'
  and not is_deleted
returning user_id, email, role_code, account_status;
```

Check to confirm
```sql
select email, role_code, account_status, is_blocked, password_hash is null as no_password
from app_user_active
where lower(email) = lower('someone@example.com');
```
