## Running the app

Run everything from the project root.

### First-time setup

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/Scripts/activate     # Git Bash on Windows
   # source .venv/bin/activate       # macOS / Linux
   # .venv\Scripts\Activate.ps1      # PowerShell
   ```

   Your prompt should now start with `(.venv)`.

2. Install the packages. Run this again after every `git pull` that changes `requirements.txt`.

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Create your `.env` file from the example and set `DATABASE_URL` (see README.md for the database setup).

   ```bash
   cp .env.example .env
   ```

4. Add a `SECRET_KEY` to `.env`. Flask uses it to sign the login cookie, and the app will not start without it. This adds a fresh one without printing it:

   ```bash
   printf '\nSECRET_KEY=%s\n' "$(python -c "import secrets; print(secrets.token_hex(32))")" >> .env
   ```

   Each person uses their own key. Never commit `.env`.

5. Check that `.env` also has these two lines (they come from `.env.example`). If your `.env` is older than the S1-DBA-05 changes, add them. Without `APP_BASE_URL`, the set-password script builds links to port 3000, which is the wrong port.

   ```
   APP_BASE_URL=http://127.0.0.1:5000
   SET_PASSWORD_PATH=/set-password
   ```

6. Apply the database migrations.

   ```bash
   python db/migrate.py up
   ```

   `python db/migrate.py status` lists which migrations are applied and which are pending.

### Start the app

```bash
flask --app app run --debug
```

Open http://127.0.0.1:5000. Stop the server with Ctrl+C. Debug mode reloads the app when you save a file.

## How accounts work

1. **Register.** Anyone can register on the landing page. New accounts get the role `user` and the status `pending`, and cannot sign in yet.
2. **Approval.** An admin approves the account (S1-DEV-06, not built yet). Accounts also have an `is_blocked` flag, and a blocked account cannot sign in.
3. **First password.** New accounts have no password. An administrator issues a one-time set-password link, and the person opens it and chooses a password. The link works once and expires after 7 days by default. Passwords are stored only as bcrypt hashes.
4. **Sign in.** Use the Sign in button on the landing page. After signing in you land on `/home`. The session lasts 8 hours or until you log out.

A signed-in person who gets blocked is signed out on their next click.

### Issuing a set-password link

```bash
python db/issue_set_password_links.py --email person@example.com
```

- **Always pass `--email`.** Without it, the script reissues links for every matching account and cancels the links that were already sent.
- It only works for accounts that are `active`, not blocked, and have no password yet. It looks at superadmins by default. Add `--role all` for admins and users.
- The link is printed once and saved nowhere. Send it privately to its owner. Never paste it into the repo or a group chat.

## Quick manual test

1. Get a link for an active account (see above). To use a freshly registered account, approve it first with the helper below.
2. Open the link and set a password. You should land on the landing page with the Sign in box open.
3. Sign in with a wrong password. It should say "Invalid email or password."
4. Sign in with the right one. You should reach `/home` with "Welcome" and your first name.
5. Click Log out, then press the browser's Back button. `/home` must not appear.
6. Open the same link again. It should say "This link has expired."
7. Block the account with the helper below, then reload `/home` while signed in. You should be sent back to the landing page, and signing in should say the account is blocked. Unblock it afterwards.

### Test helpers (until the admin screens exist)

Change the email and the value, then run:

```bash
# approve an account (use 'pending' to put it back)
python -c "from app.db import get_connection as g; c=g(); k=c.cursor(); k.execute('update app_user set account_status = %s where lower(email) = lower(%s)', ('active', 'test_a@example.com')); print(k.rowcount, 'row changed'); c.commit(); c.close()"

# block (True) or unblock (False) an account
python -c "from app.db import get_connection as g; c=g(); k=c.cursor(); k.execute('update app_user set is_blocked = %s where lower(email) = lower(%s)', (True, 'test_a@example.com')); print(k.rowcount, 'row changed'); c.commit(); c.close()"
```

Rows cannot be hard-deleted, so use obvious `test_` emails and keep test accounts to a minimum.

## API

All endpoints take and return JSON. Every response has `"ok": true` or `"ok": false` with an `"error"` message.

| Endpoint | Body | Success | Errors |
|---|---|---|---|
| `POST /api/register` | `first_name`, `last_name`, `email` | 201 | 400 invalid input, 409 email already registered |
| `POST /api/login` | `email`, `password` | 200 with `redirect` | 400 missing fields, 401 wrong email or password, 403 blocked or not yet approved |
| `POST /api/logout` | none | 200 | none |
| `POST /api/set-password` | `token`, `password`, `confirm_password` | 200 with `redirect` | 400 bad password, passwords differ, or link invalid, used or expired |

Any endpoint can also return 500 for a database or server error. The details are in the Flask log.

Wrong email, wrong password and an account with no password yet all give the same 401 message on purpose. A blocked or pending account is only named as such after the correct password is entered.

Passwords must be at least 8 characters and at most 72 bytes (bcrypt ignores anything longer; accented letters and symbols can take more than one byte). Names are limited to 50 characters and the email to 100. The email is stored in lowercase.

## For developers

| File | What it does |
|---|---|
| `app/routes/auth.py` | register, login, logout and set-password routes, and their database queries |
| `app/security.py` | bcrypt hashing, token hashing, the session, `current_user()` and `@login_required` |
| `app/templates/set_password.html` | the page the one-time link opens |
| `app/templates/home.html` | placeholder page after sign-in, replaced by S1-DEV-08 |

To protect a page, add `@login_required` under the route. Signed-out visitors are sent to the landing page, and `/api/` routes return 401 JSON.

```python
from app.security import current_user, login_required

@main_bp.route("/example")
@login_required
def example():
    user = current_user()  # dict with user_id, email, first_name, last_name, role_code
    ...
```

Not built yet: forgot password (S1-DEV-04), admin approval and user management screens, rights checks, and sending email.

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'psycopg2'` or `'bcrypt'` | The virtual environment is not active, or the packages are not installed. Activate `.venv`, then run `python -m pip install -r requirements.txt`. |
| `DATABASE_URL is missing` | There is no `.env` file. Copy `.env.example` to `.env` and fill it in. |
| `SECRET_KEY is missing` | Add `SECRET_KEY=...` to `.env` (setup step 4). |
| `404 Not Found` on `/api/login` or `/api/register` | The auth blueprint is not loaded. `flask --app app routes` should list `auth.login`, `auth.logout`, `auth.register`, `auth.set_password` and `auth.set_password_page`. |
| A form shows "Could not reach the server" | The browser got no JSON reply. Open the page from the Flask address (http://127.0.0.1:5000) and check the Flask terminal for the request and any traceback. |
| Register shows "Server error" and the log mentions `role_code` | The roles are not seeded. Pull the latest code and run `python db/migrate.py up`. |
| The script says "No matching accounts without a password" | The account must be `active`, not blocked, have no password yet, and match the role filter. Use `--role all` for non-superadmins. |
| The link starts with `http://localhost:3000` | `APP_BASE_URL` is missing from `.env` (setup step 5). |
| "This link has expired" on `/set-password` | The link was already used, has expired, or was copied incompletely. Issue a new one. |
| Sign in says "Invalid email or password" for a new account | The account has no password yet. Use the set-password link. |
