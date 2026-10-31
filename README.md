# POWER-HOUSE-HOPEProject
Information Management HOPE Project, Sprint 1 to 4 workspace.

## MESSAGE/INSTRUCTIONS FROM DB ADMIN

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

```
hope-erp/
├── supabase/
│   └── migrations/        # numbered SQL files, applied in order
├── db/
│   └── migrate.py         # the migration runner
├── .env.example           # template (committed)
├── .env                   # your real secrets (NOT committed)
├── .gitignore
├── requirements.txt
└── README.md
```


## 11. Who to ask


Database password, Supabase access, migration problems - DB Admin 
GitHub access, branch rules, pull request templates - Scrum Master 
Anything else - Post it in the GC 

---


## END OF MESSAGE 
