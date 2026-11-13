import hashlib
from functools import wraps

import bcrypt
from flask import g, jsonify, make_response, redirect, request, session, url_for

from app.db import get_connection

MIN_PASSWORD_LENGTH = 8
# bcrypt only uses the first 72 bytes of a password, and newer versions of the
# library refuse longer input, so the limit is counted in bytes.
MAX_PASSWORD_BYTES = 72

# Checked when an email is unknown or has no password yet, so those logins take
# as long as a wrong password and the response time doesn't reveal which emails exist.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode("ascii")


# ---- passwords and tokens ----------------------------------------------------

def hash_password(password):
    """bcrypt hash string (60 characters), safe to store in app_user.password_hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def password_too_long(password):
    return len(password.encode("utf-8")) > MAX_PASSWORD_BYTES


def verify_password(stored_hash, password):
    """True only if the password matches. An account with no hash never matches."""
    try:
        matches = bcrypt.checkpw(
            password.encode("utf-8"), (stored_hash or _DUMMY_HASH).encode("ascii")
        )
    except ValueError:  # malformed stored hash, or input bcrypt refuses
        return False
    return matches and stored_hash is not None


def hash_token(token):
    """SHA-256 of a one-time token as 64 hex characters.

    This is what password_reset_token.token_hash stores. The raw token only
    ever exists in the emailed link.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_new_password(password, confirm):
    """Return an error message for a bad new password, or None if it is fine."""
    if not isinstance(password, str) or not password:
        return "Enter a password."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if "\x00" in password:
        return "Password contains an invalid character."
    if password_too_long(password):
        return (
            f"Password is too long. Use {MAX_PASSWORD_BYTES} characters or fewer "
            "(accented letters and symbols can count as more than one)."
        )
    if password != confirm:
        return "Passwords do not match."
    return None


# ---- session -----------------------------------------------------------------

def start_session(user_id):
    session.clear()  # drop anything left over from an earlier login
    session["user_id"] = user_id
    session.permanent = True


def end_session():
    session.clear()


def load_user(user_id):
    """The user if this account may still sign in, otherwise None.

    Checked on every request, so blocking or deleting an account also ends
    sessions that are already open.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, email, first_name, last_name, role_code
                     FROM app_user
                    WHERE user_id = %s
                      AND NOT is_deleted
                      AND NOT is_blocked
                      AND account_status = 'active'""",
                (user_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "user_id": row[0],
        "email": row[1],
        "first_name": row[2],
        "last_name": row[3],
        "role_code": row[4],
    }


def current_user():
    """The signed-in user for this request, or None. Looked up once per request."""
    if "user" not in g:
        user_id = session.get("user_id")
        g.user = load_user(user_id) if user_id is not None else None
        if g.user is None and user_id is not None:
            session.clear()  # blocked, deleted or no longer active
    return g.user


def login_required(view):
    """Protect a page or API route. DEV-08 can build rights checks on top of this."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            if request.path.startswith("/api/"):
                return jsonify(ok=False, error="Please sign in."), 401
            return redirect(url_for("main.landing", signin=1))
        response = make_response(view(*args, **kwargs))
        # Stops the back button from showing a protected page after logout
        response.headers["Cache-Control"] = "no-store"
        return response

    return wrapped