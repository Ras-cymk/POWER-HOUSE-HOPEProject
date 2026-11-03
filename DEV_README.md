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

2. Install the packages.

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Create your `.env` file and set `DATABASE_URL` (see README.md for the database setup).

   ```bash
   cp .env.example .env
   ```

   Never commit `.env`.

4. Apply the database migrations.

   ```bash
   python db/migrate.py up
   ```

   `python db/migrate.py status` lists which migrations are applied and which are pending.

### Start the app

```bash
flask --app app run --debug
```

Open http://127.0.0.1:5000. Stop the server with Ctrl+C. Debug mode reloads the app when you save a file.

To check that the routes loaded:

```bash
flask --app app routes
```

## Register API

`POST /api/register` creates a new account. New users get the role `user` and the status `pending`. An admin has to approve them before they can sign in (S1-DEV-06). The request cannot set the role or status.

Request body (JSON):

```json
{ "first_name": "Ana", "last_name": "Cruz", "email": "ana@company.com" }
```

| Status | Response | When |
|---|---|---|
| 201 | `{"ok": true}` | Account created as pending |
| 400 | `{"ok": false, "error": "..."}` | Missing field, name over 50 characters, or invalid email |
| 409 | `{"ok": false, "error": "..."}` | Email already registered (case is ignored) |
| 500 | `{"ok": false, "error": "..."}` | Database or server error (details are in the Flask log) |

Names are limited to 50 characters and the email to 100. The email is stored in lowercase.

Try it from the terminal:

```bash
curl -i -X POST http://127.0.0.1:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"User","email":"test_user@example.com"}'
```

Registration only works once the `user` role exists in the `role` table (seed data, S1-DBA-05). Database rows cannot be hard-deleted, so use obvious `test_` emails when testing.

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'psycopg2'` (or `dotenv`) | The virtual environment is not active, or the packages are not installed. Activate `.venv`, then run `python -m pip install -r requirements.txt`. |
| `DATABASE_URL is missing` | There is no `.env` file. Copy `.env.example` to `.env` and fill it in. |
| `404 Not Found` on `/api/register` | The auth blueprint is not loaded. `flask --app app routes` should list `auth.register`. Check that `app/__init__.py` registers `auth_bp`. |
| Register form shows "Could not reach the server" | The browser got no JSON reply. Open the page from the Flask address (http://127.0.0.1:5000) and check the Flask terminal for the request and any traceback. |
| Register form shows "Server error" and the log says `Key (role_code)=(user) is not present in table "role"` | The roles have not been seeded yet. Pull the latest code and run `python db/migrate.py up`. |
