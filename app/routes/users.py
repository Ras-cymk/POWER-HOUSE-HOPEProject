import os
import secrets

import psycopg2
from flask import Blueprint, current_app, jsonify, render_template, request, url_for

from app.db import get_connection
from app.mailer import send_email_async
from app.permissions import manageable_roles, roles_required
from app.routes.auth import EMAIL_RE, MAX_EMAIL, MAX_NAME
from app.security import current_user, hash_token


users_bp = Blueprint("users", __name__)

ADMIN_ROLES = ("admin", "superadmin")
SET_PASSWORD_DAYS = 7  # same lifetime as the links made by db/issue_set_password_links.py
NOT_FOUND = "User not found."


# ---- database helpers --------------------------------------------------------
# The roles argument is the list of roles the signed-in person may manage. It is
# part of every query, so an Admin cannot reach a Superadmin even by guessing an id.

def list_users(roles):
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, first_name, last_name, email, role_code, account_status, is_blocked
                     FROM app_user_active
                    WHERE role_code = ANY(%s)
                    ORDER BY lower(last_name), lower(first_name), user_id""",
                (list(roles),),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "user_id": r[0],
            "first_name": r[1],
            "last_name": r[2],
            "email": r[3],
            "role_code": r[4],
            "account_status": r[5],
            "is_blocked": r[6],
        }
        for r in rows
    ]


def create_user_with_link(first_name, last_name, email, token_hash):
    """Create an active user with no password, plus a one-time set-password token.

    Both inserts are one transaction. Returns the new user_id, or None if the
    email is already registered.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO app_user (email, first_name, last_name, role_code, account_status)
                   VALUES (%s, %s, %s, 'user', 'active')
                   ON CONFLICT DO NOTHING
                   RETURNING user_id""",
                (email, first_name, last_name),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                """INSERT INTO password_reset_token (user_id, token_hash, purpose, expires_at)
                   VALUES (%s, %s, 'set_password', now() + make_interval(days => %s))""",
                (row[0], token_hash, SET_PASSWORD_DAYS),
            )
            return row[0]
    finally:
        conn.close()


def update_names(user_id, first_name, last_name, roles):
    """Returns False if there is no such user among the roles the caller may manage."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE app_user
                      SET first_name = %s, last_name = %s
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)""",
                (first_name, last_name, user_id, list(roles)),
            )
            return cur.rowcount == 1
    finally:
        conn.close()


def set_blocked(user_id, blocked, roles):
    """Returns False if there is no such user among the roles the caller may manage."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE app_user
                      SET is_blocked = %s
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)""",
                (blocked, user_id, list(roles)),
            )
            return cur.rowcount == 1
    finally:
        conn.close()


# ---- validation --------------------------------------------------------------

def clean_names(data):
    first = str(data.get("first_name", "")).strip()
    last = str(data.get("last_name", "")).strip()
    if not first or not last:
        return None, None, "First name and last name are required."
    if len(first) > MAX_NAME or len(last) > MAX_NAME:
        return None, None, f"Names must be {MAX_NAME} characters or fewer."
    return first, last, None


def welcome_email_body(first_name, link):
    return (
        f"Hello {first_name},\n\n"
        "An administrator created an account for you on Hope, Inc. ERP.\n\n"
        f"Open this link to choose your password. It works once and expires in {SET_PASSWORD_DAYS} days:\n\n"
        f"{link}\n\n"
        "If you were not expecting this, you can ignore this email.\n"
    )


# ---- page and API ------------------------------------------------------------

@users_bp.get("/users")
@roles_required(*ADMIN_ROLES)
def users_page():
    return render_template("users.html", me=current_user())


@users_bp.get("/api/users")
@roles_required(*ADMIN_ROLES)
def api_list_users():
    me = current_user()
    try:
        users = list_users(manageable_roles(me["role_code"]))
    except psycopg2.Error:
        current_app.logger.exception("Listing users failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    for user in users:
        user["is_self"] = user["user_id"] == me["user_id"]
    return jsonify(ok=True, users=users)


@users_bp.post("/api/users")
@roles_required(*ADMIN_ROLES)
def api_add_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    first, last, error = clean_names(data)
    if error:
        return jsonify(ok=False, error=error), 400
    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify(ok=False, error="Email is required."), 400
    if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
        return jsonify(ok=False, error="Please enter a valid email address."), 400

    # Role and status are never read from the request: a new user is always a
    # plain 'user' and active. Making admins is S1-DEV-06.
    token = secrets.token_hex(32)
    try:
        user_id = create_user_with_link(first, last, email, hash_token(token))
    except psycopg2.Error:
        current_app.logger.exception("Adding a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if user_id is None:
        return jsonify(ok=False, error="An account with this email already exists."), 409

    # The link host comes from .env and never from the request
    base = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    link = f"{base}{url_for('auth.set_password_page')}?token={token}"
    send_email_async(email, "Your Hope, Inc. ERP account", welcome_email_body(first, link))

    user = {
        "user_id": user_id,
        "first_name": first,
        "last_name": last,
        "email": email,
        "role_code": "user",
        "account_status": "active",
        "is_blocked": False,
        "is_self": False,
    }
    return jsonify(ok=True, user=user, email_configured=bool(os.getenv("SMTP_HOST"))), 201


@users_bp.patch("/api/users/<int:user_id>")
@roles_required(*ADMIN_ROLES)
def api_edit_user(user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    # Only the names can be changed here. Anything else in the body is ignored.
    first, last, error = clean_names(data)
    if error:
        return jsonify(ok=False, error=error), 400

    try:
        found = update_names(user_id, first, last, manageable_roles(current_user()["role_code"]))
    except psycopg2.Error:
        current_app.logger.exception("Editing a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if not found:
        return jsonify(ok=False, error=NOT_FOUND), 404
    return jsonify(ok=True)


def change_blocked(user_id, blocked):
    me = current_user()
    if blocked and user_id == me["user_id"]:
        return jsonify(ok=False, error="You cannot block your own account."), 400
    try:
        found = set_blocked(user_id, blocked, manageable_roles(me["role_code"]))
    except psycopg2.Error:
        current_app.logger.exception("Blocking or unblocking a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if not found:
        return jsonify(ok=False, error=NOT_FOUND), 404
    return jsonify(ok=True)


@users_bp.post("/api/users/<int:user_id>/block")
@roles_required(*ADMIN_ROLES)
def api_block_user(user_id):
    return change_blocked(user_id, True)


@users_bp.post("/api/users/<int:user_id>/unblock")
@roles_required(*ADMIN_ROLES)
def api_unblock_user(user_id):
    return change_blocked(user_id, False)
