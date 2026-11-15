import os
import secrets

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
from app.mailer import send_email_async
from app.routes.auth import EMAIL_RE, LINK_ERROR, MAX_EMAIL
from app.security import check_new_password, hash_password, hash_token


reset_bp = Blueprint("reset", __name__)

RESET_TOKEN_MINUTES = 30
RESEND_COOLDOWN_SECONDS = 60  # one reset email per account per minute

# The same answer whether or not the email has an account, so nobody can use
# this form to find out who is registered.
FORGOT_MESSAGE = "If that email has an account, a reset link is on its way. Check your inbox."


# ---- database helpers --------------------------------------------------------

def find_reset_candidate(email):
    """An account that may get a reset link: active, not blocked or deleted, and
    already has a password. Accounts without a password use the set-password link."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, email, first_name
                     FROM app_user
                    WHERE lower(email) = %s
                      AND NOT is_deleted
                      AND NOT is_blocked
                      AND account_status = 'active'
                      AND password_hash IS NOT NULL""",
                (email,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"user_id": row[0], "email": row[1], "first_name": row[2]}


def issue_reset_token(user_id, token_hash):
    """Store a new reset token and cancel the account's older unused ones.

    Returns False, and stores nothing, if a reset link was issued very recently.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM password_reset_token
                    WHERE user_id = %s AND purpose = 'reset'
                      AND created_at > now() - make_interval(secs => %s)""",
                (user_id, RESEND_COOLDOWN_SECONDS),
            )
            if cur.fetchone() is not None:
                return False
            cur.execute(
                """UPDATE password_reset_token
                      SET is_used = TRUE, used_at = now()
                    WHERE user_id = %s AND purpose = 'reset'
                      AND NOT is_used AND NOT is_deleted""",
                (user_id,),
            )
            cur.execute(
                """INSERT INTO password_reset_token (user_id, token_hash, purpose, expires_at)
                   VALUES (%s, %s, 'reset', now() + make_interval(mins => %s))""",
                (user_id, token_hash, RESET_TOKEN_MINUTES),
            )
            return True
    finally:
        conn.close()


def reset_token_is_usable(token_hash):
    """True if a reset token exists, is unused, has not expired, and its account can still sign in."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT 1
                     FROM password_reset_token t
                     JOIN app_user u ON u.user_id = t.user_id
                    WHERE t.token_hash = %s
                      AND t.purpose = 'reset'
                      AND NOT t.is_used
                      AND NOT t.is_deleted
                      AND t.expires_at > now()
                      AND u.account_status = 'active'
                      AND NOT u.is_blocked
                      AND NOT u.is_deleted""",
                (token_hash,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def use_reset_token(token_hash, password_hash):
    """Burn the one-time token and save the new password in one transaction.

    Returns False if the token cannot be used.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE password_reset_token
                      SET is_used = TRUE, used_at = now()
                    WHERE token_hash = %s
                      AND purpose = 'reset'
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
                    WHERE user_id = %s
                      AND account_status = 'active'
                      AND NOT is_blocked
                      AND NOT is_deleted""",
                (password_hash, row[0]),
            )
            if cur.rowcount != 1:
                conn.rollback()  # the account can't sign in any more, so keep the token unused
                return False
            return True
    finally:
        conn.close()


# ---- forgot password: ask for the email --------------------------------------

def reset_email_body(first_name, link):
    return (
        f"Hello {first_name},\n\n"
        "We received a request to reset the password for your Hope, Inc. ERP account.\n\n"
        f"Open this link to choose a new password. It works once and expires in {RESET_TOKEN_MINUTES} minutes:\n\n"
        f"{link}\n\n"
        "If you did not ask for this, ignore this email. Your password will not change.\n"
    )


@reset_bp.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@reset_bp.post("/api/forgot-password")
def forgot_password():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    email = str(data.get("email", "")).strip().lower()
    if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
        return jsonify(ok=False, error="Please enter a valid email address."), 400

    try:
        user = find_reset_candidate(email)
        if user:
            token = secrets.token_hex(32)
            if issue_reset_token(user["user_id"], hash_token(token)):
                # The link host comes from .env and never from the request, so a
                # forged Host header cannot point the emailed link at another site.
                base = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
                link = f"{base}{url_for('reset.reset_password_page')}?token={token}"
                send_email_async(
                    user["email"],
                    "Reset your Hope, Inc. ERP password",
                    reset_email_body(user["first_name"], link),
                )
    except psycopg2.Error:
        current_app.logger.exception("Forgot password failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    return jsonify(ok=True, message=FORGOT_MESSAGE)


# ---- reset password: choose a new one ----------------------------------------

@reset_bp.get("/reset-password")
def reset_password_page():
    token = request.args.get("token", "")
    try:
        valid = bool(token) and reset_token_is_usable(hash_token(token))
    except psycopg2.Error:
        current_app.logger.exception("Reset token check failed")
        valid = False

    response = make_response(render_template("reset_password.html", token=token, valid=valid))
    # The token is in the URL, so keep it out of caches and Referer headers
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@reset_bp.post("/api/reset-password")
def reset_password():
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
        done = use_reset_token(hash_token(token), hash_password(data["password"]))
    except psycopg2.Error:
        current_app.logger.exception("Reset password failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    if not done:
        return jsonify(ok=False, error=LINK_ERROR), 400
    return jsonify(ok=True, redirect=url_for("main.landing", signin=1))
