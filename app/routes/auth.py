import re

import psycopg2
from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    url_for,
)

from app.db import get_connection
from app.security import (
    check_new_password,
    end_session,
    hash_password,
    hash_token,
    password_too_long,
    start_session,
    verify_password,
)


auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Limits match the app_user column sizes
MAX_NAME = 50
MAX_EMAIL = 100

LOGIN_ERROR = "Invalid email or password."
LINK_ERROR = "This link is invalid or has expired."


# ---- database helpers --------------------------------------------------------

def create_pending_user(first_name, last_name, email):
    """Insert a new app_user. Returns False if the email is already registered."""
    conn = get_connection()
    try:
        # "with conn" commits on success and rolls back on error
        with conn, conn.cursor() as cur:
            # role_code and account_status are left out on purpose: the column
            # defaults make every new user a 'user' with status 'pending', and
            # the client can never choose them.
            cur.execute(
                """INSERT INTO app_user (email, first_name, last_name)
                   VALUES (%s, %s, %s)
                   ON CONFLICT DO NOTHING
                   RETURNING user_id""",
                (email, first_name, last_name),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def find_login_user(email):
    """The account for this email (soft-deleted ones are ignored), or None."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, password_hash, account_status, is_blocked
                     FROM app_user
                    WHERE lower(email) = %s AND NOT is_deleted""",
                (email,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "user_id": row[0],
        "password_hash": row[1],
        "account_status": row[2],
        "is_blocked": row[3],
    }


def token_is_usable(token_hash):
    """True if a set-password token exists, is unused and has not expired."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT 1
                     FROM password_reset_token t
                     JOIN app_user u ON u.user_id = t.user_id
                    WHERE t.token_hash = %s
                      AND t.purpose = 'set_password'
                      AND NOT t.is_used
                      AND NOT t.is_deleted
                      AND t.expires_at > now()
                      AND NOT u.is_deleted""",
                (token_hash,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def use_set_password_token(token_hash, password_hash):
    """Burn the one-time token and save the new password in one transaction.

    Returns False if the token cannot be used. The UPDATE ... WHERE NOT is_used
    makes the token single-use even if the link is opened twice at once.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE password_reset_token
                      SET is_used = TRUE, used_at = now()
                    WHERE token_hash = %s
                      AND purpose = 'set_password'
                      AND NOT is_used
                      AND NOT is_deleted
                      AND expires_at > now()
                RETURNING user_id""",
                (token_hash,),
            )
            row = cur.fetchone()
            if row is None:
                return False
            cur.execute(
                """UPDATE app_user
                      SET password_hash = %s
                    WHERE user_id = %s AND NOT is_deleted""",
                (password_hash, row[0]),
            )
            if cur.rowcount != 1:
                conn.rollback()  # the account is gone, so keep the token unused
                return False
            return True
    finally:
        conn.close()


# ---- register ----------------------------------------------------------------

def clean_registration(data):
    """Validate the request body. Returns ((first, last, email), None) or (None, error)."""
    first = str(data.get("first_name", "")).strip()
    last = str(data.get("last_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()

    if not first or not last or not email:
        return None, "First name, last name and email are required."
    if len(first) > MAX_NAME or len(last) > MAX_NAME:
        return None, f"Names must be {MAX_NAME} characters or fewer."
    if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
        return None, "Please enter a valid email address."
    return (first, last, email), None


@auth_bp.post("/api/register")
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    values, error = clean_registration(data)
    if error:
        return jsonify(ok=False, error=error), 400

    try:
        created = create_pending_user(*values)
    except psycopg2.Error:
        # Full details go to the server log, not to the browser
        current_app.logger.exception("Registration failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    if not created:
        return jsonify(ok=False, error="An account with this email already exists."), 409
    return jsonify(ok=True), 201


# ---- login and logout --------------------------------------------------------

@auth_bp.post("/api/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not email or not isinstance(password, str) or not password:
        return jsonify(ok=False, error="Email and password are required."), 400
    if password_too_long(password):
        return jsonify(ok=False, error=LOGIN_ERROR), 401

    try:
        user = find_login_user(email)
    except psycopg2.Error:
        current_app.logger.exception("Login lookup failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    # Unknown email, no password yet and wrong password all get the same answer
    stored_hash = user["password_hash"] if user else None
    if not verify_password(stored_hash, password):
        return jsonify(ok=False, error=LOGIN_ERROR), 401

    # The password is right, so it is now safe to say why the account can't sign in
    if user["is_blocked"]:
        return jsonify(ok=False, error="This account is blocked. Contact an administrator."), 403
    if user["account_status"] != "active":
        return jsonify(ok=False, error="This account is still waiting for admin approval."), 403

    start_session(user["user_id"])
    return jsonify(ok=True, redirect=url_for("main.home"))


@auth_bp.post("/api/logout")
def logout():
    end_session()
    return jsonify(ok=True)


# ---- set password (first login) ----------------------------------------------

@auth_bp.get("/set-password")
def set_password_page():
    token = request.args.get("token", "")
    try:
        valid = bool(token) and token_is_usable(hash_token(token))
    except psycopg2.Error:
        current_app.logger.exception("Token check failed")
        valid = False

    response = make_response(render_template("set_password.html", token=token, valid=valid))
    # The token is in the URL, so keep it out of caches and Referer headers
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@auth_bp.post("/api/set-password")
def set_password():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    token = data.get("token")
    if not isinstance(token, str) or not token:
        return jsonify(ok=False, error=LINK_ERROR), 400

    error = check_new_password(data.get("password"), data.get("confirm_password"))
    if error:
        return jsonify(ok=False, error=error), 400

    try:
        done = use_set_password_token(hash_token(token), hash_password(data["password"]))
    except psycopg2.Error:
        current_app.logger.exception("Set password failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    if not done:
        return jsonify(ok=False, error=LINK_ERROR), 400
    return jsonify(ok=True, redirect=url_for("main.landing", signin=1))