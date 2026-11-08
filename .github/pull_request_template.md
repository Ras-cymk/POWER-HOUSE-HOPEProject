## What did I change?

Adds sign-in to the app: login and logout with a session, bcrypt password hashing, set-password on first login through the one-time link, and blocked users cannot sign in.

- `app/routes/auth.py`: new `POST /api/login`, `POST /api/logout`, `GET /set-password` and `POST /api/set-password`. Register is unchanged.
- `app/security.py` (new): bcrypt hash and check, SHA-256 token hashing, session helpers, `current_user()` and `@login_required`.
- `app/routes/main.py`, `app/templates/home.html` (new): a placeholder `/home` page behind login, until S1-DEV-08 builds the real main page.
- `app/templates/set_password.html` (new): the page the one-time link opens.
- `app/static/js/landing.js`: the Sign in and set-password forms, the Log out button, and `?signin=1` opens the Sign in box.
- `app/__init__.py`, `app/config.py`, `.env.example`: `SECRET_KEY` and session cookie settings (HttpOnly, SameSite=Lax, 8 hours).
- `DEV_README.md`: how to run the app, how accounts work, the API, a manual test list and troubleshooting.

How it behaves:
- Passwords are stored only as bcrypt hashes (at least 8 characters, at most 72 bytes).
- The first password is set through a one-time link. It uses `password_reset_token` (S1-DBA-04) with purpose `set_password`, only the SHA-256 hash is stored, and each link works once and expires. Links come from `db/issue_set_password_links.py`.
- Wrong email, wrong password and no password yet all show the same message. "Blocked" and "waiting for approval" are only shown after the correct password.
- Only `active`, non-blocked, non-deleted accounts can sign in. This is checked on every request, so blocking someone also ends their open session.
- After logout, the Back button does not show `/home`.

Tested manually against the real database:
- [x] Set a password with a link from the DB Admin's script, then signed in and reached `/home` with my name
- [x] Log out, then Back does not show `/home`
- [x] Blocked my account while signed in: the next page load sent me to the landing page, and signing in showed the blocked message. Unblocked afterwards
- [ ] Wrong password shows "Invalid email or password"
- [ ] Opening the same link again shows "This link has expired"

For reviewers:
- Everyone needs a `SECRET_KEY` line in their `.env` (see `DEV_README.md`), or the app will not start.
- Run `python -m pip install -r requirements.txt` for `bcrypt`.
- No migration, and no new dependency.
- Not included: forgot password (S1-DEV-04), admin approval (S1-DEV-06), sending email, rights checks, and lockout after repeated failed logins.

## Related task (e.g. S1-SM-01)

S1-DEV-03: Login and logout with session handling; password hashing and set-password on first login; blocked users cannot sign in

## Checklist
- [ ] I checked my work
- [ ] I'm ready for review
