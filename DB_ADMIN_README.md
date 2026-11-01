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

## ADDENDUM: Sample code for the login and rights tables (S1-DBA-03)

This section shows how to add and read values in the **auth tables**. It is for Developers building register, login, reset password and the rights dialog.


### The tables

| Table | What a row is | Key |
|---|---|---|
| `role` | A role: `superadmin`, `admin`, `user` (already loaded) | `role_code` |
| `module` | A module: `customer`, `product`, `hr`, `sales`, `reports` (already loaded) | `module_code` |
| `permission` | One checkbox in the Rights dialog, e.g. `customers.add` (the 36 rights are loaded in S1-DBA-05) | `perm_code` |
| `app_user` | An account that can sign in | `user_id` (automatic) |
| `user_module` | A module switched **on** for a user | `user_id` + `module_code` |
| `user_permission` | An action **ticked** for a user | `user_id` + `perm_code` |

### Where to run these examples

Open the Supabase dashboard → **SQL Editor**, and wrap your experiments like this:

```sql
begin;
-- your test statements here
rollback;   -- undoes everything, so no test rows are left behind
```

Why: **rows can never be hard-deleted** in this database (the database refuses `DELETE` and `TRUNCATE`). A test row you commit stays forever, so test inside `begin ... rollback`. Changing the *structure* (tables, columns) is still only done through migration files.

### 1. Look at the fixed data

```sql
select * from role;     -- 3 rows
select * from module;   -- 5 rows
```

### 2. Register a new user

This is what the Register screen does. New accounts are `user` and `pending` by default.

```sql
insert into app_user (email, first_name, last_name, password_hash)
values ('abcef12345@gmail.com', 'John', 'Doe', '<bcrypt-or-argon2-hash-from-your-code>')
returning user_id, email, role_code, account_status;
```

- **Never put a plain-text password here.** Hash it in the app code first (bcrypt or Argon2).
- For a quick test row you may leave `password_hash` out. It stays empty until the user sets a password.
- The same email in any capital letters counts as a duplicate, so `A@x.com` and `a@x.com` collide.
- Do not fill in `is_deleted` or `stamp`. The database does it for you.

### 3. Log in (look up an account)

```sql
select user_id, password_hash, role_code, account_status, is_blocked
from app_user
where lower(email) = lower('abcef12345@gmail.com')
  and not is_deleted;
```

Compare the password against `password_hash` **in your code**. Refuse the login if `is_blocked` is true or `account_status` is not `active`.

### 4. Activate, promote, block

```sql
-- Activate a pending account
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

### 5. Switch a module on for a user

```sql
insert into user_module (user_id, module_code)
select user_id, 'customer' from app_user
where lower(email) = lower('abcef12345@gmail.com')
on conflict (user_id, module_code) do update set is_deleted = false;
```

The `on conflict` part means: if the row was switched off before (soft-deleted), switch it back on instead of failing.

### 6. Tick (grant) a right

The `permission` table must contain the right first. S1-DBA-05 loads all 36. Until then, for a **test only** (inside `begin ... rollback`):

```sql
insert into permission (perm_code, module_code, perm_name, sort_order)
values ('customers.add', 'customer', 'Add Customer', 1)
on conflict (perm_code) do nothing;
```

Then grant it to a user:

```sql
insert into user_permission (user_id, perm_code)
select user_id, 'customers.add' from app_user
where lower(email) = lower('abcef12345@gmail.com')
on conflict (user_id, perm_code) do update set is_deleted = false;
```

### 7. Untick (revoke) a right

This is a **soft delete**: the row stays, and the stamp and audit log record who removed it.

```sql
update user_permission set is_deleted = true
where perm_code = 'customers.add'
  and user_id = (select user_id from app_user where lower(email) = lower('abcef12345@gmail.com'));
```

Ticking it again (step 6) restores it.

### 8. Read what a user may do

```sql
-- Modules switched on (builds the sidebar)
select m.module_code, m.module_name
from user_module um
join module m on m.module_code = um.module_code
where um.user_id = 1 and not um.is_deleted
order by m.sort_order;

-- Actions ticked (decides which buttons to show and which requests to allow)
select p.perm_code
from user_permission up
join permission p on p.perm_code = up.perm_code
where up.user_id = 1 and not up.is_deleted;
```

Replace `1` with the real `user_id`. In app code, pass it as a parameter (`$1`), never by pasting text into the query.

### 9. List accounts for the User Management screen

```sql
select user_id, email, first_name, last_name, role_code, account_status, is_blocked, stamp
from app_user_active
order by last_name;
```

`app_user_active` hides deleted accounts and never includes `password_hash`.

### Common errors

| Error says | Cause |
|---|---|
| duplicate key ... `app_user_email_uq` | That email is already registered (capitals do not matter). |
| violates foreign key ... `role` / `permission` / `module` | The role, right or module code does not exist. Check the spelling against the tables above. |
| violates check constraint `account_status_ck` | `account_status` must be exactly `pending` or `active`. |
| the database refuses a delete | Hard deletes are blocked on purpose. Set `is_deleted = true` instead. |
| `permission denied` or empty results from the Supabase API | These tables are closed to Supabase's public API on purpose. Always go through the app's server connection (`DATABASE_URL`). |

### Rules for everyone

- Passwords and reset tokens are stored **only as hashes**, and the database keeps them out of the audit log.
- Never add real people's data to these tables in a migration file or in the repo.
- Permanent starting data (the 36 rights, the first superadmin accounts) belongs in the S1-DBA-05 migration, not typed by hand.
- Rights are checked on the **server** for every request. Hiding a button is only a courtesy.

## END OF ADDENDUM
