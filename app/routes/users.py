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
NOT_FOUND_MESSAGE = "User not found."

# What the database helpers below report when an action cannot go ahead
OK = "ok"
NOT_FOUND = "not_found"
LAST_SUPERADMIN = "last_superadmin"  # blocking would leave no active superadmin
PROTECTED = "protected"  # a superadmin account: its role cannot be changed here
NOT_ACTIVE = "not_active"  # only an active account can be made an admin
ALREADY_APPROVED = "already_approved"


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
                    ORDER BY (account_status <> 'pending'), lower(last_name), lower(first_name), user_id""",
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


def leaves_no_superadmin(active_superadmin_ids, user_id):
    """True if taking this account out of the active superadmins would leave none."""
    return user_id in active_superadmin_ids and not (set(active_superadmin_ids) - {user_id})


def set_blocked(user_id, blocked, roles):
    """Block or unblock. Returns OK, NOT_FOUND (no such user among the roles the
    caller may manage) or LAST_SUPERADMIN (the system must keep one active superadmin)."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT role_code FROM app_user
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)""",
                (user_id, list(roles)),
            )
            row = cur.fetchone()
            if row is None:
                return NOT_FOUND
            if blocked and row[0] == "superadmin":
                # Lock every active superadmin first. If two superadmins block each
                # other at the same moment, the second one waits and then sees that
                # it would be the last one left.
                cur.execute(
                    """SELECT user_id FROM app_user
                        WHERE role_code = 'superadmin' AND account_status = 'active'
                          AND NOT is_blocked AND NOT is_deleted
                          FOR UPDATE"""
                )
                if leaves_no_superadmin({r[0] for r in cur.fetchall()}, user_id):
                    return LAST_SUPERADMIN
            cur.execute(
                """UPDATE app_user
                      SET is_blocked = %s
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)""",
                (blocked, user_id, list(roles)),
            )
            return OK if cur.rowcount == 1 else NOT_FOUND
    finally:
        conn.close()


def approve_user(user_id, token_hash):
    """Make a pending account active. If it has no password yet, also store a
    one-time set-password token, in the same transaction.

    Returns None if there is no such user. Otherwise a dict with "result"
    (OK or ALREADY_APPROVED) and, when approved, "email", "first_name" and
    "needs_link" (True when a token was stored).
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE app_user
                      SET account_status = 'active'
                    WHERE user_id = %s AND NOT is_deleted AND account_status = 'pending'
                RETURNING email, first_name, password_hash IS NULL""",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute("SELECT 1 FROM app_user WHERE user_id = %s AND NOT is_deleted", (user_id,))
                return {"result": ALREADY_APPROVED} if cur.fetchone() else None
            email, first_name, needs_link = row
            if needs_link:
                cur.execute(
                    """INSERT INTO password_reset_token (user_id, token_hash, purpose, expires_at)
                       VALUES (%s, %s, 'set_password', now() + make_interval(days => %s))""",
                    (user_id, token_hash, SET_PASSWORD_DAYS),
                )
            return {"result": OK, "email": email, "first_name": first_name, "needs_link": needs_link}
    finally:
        conn.close()


def set_role(user_id, new_role):
    """Make an account an 'admin' or a plain 'user'. Superadmin accounts are
    never changed here. Returns OK, NOT_FOUND, PROTECTED or NOT_ACTIVE."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT role_code, account_status FROM app_user
                    WHERE user_id = %s AND NOT is_deleted
                      FOR UPDATE""",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return NOT_FOUND
            role, status = row
            if role == "superadmin":
                return PROTECTED
            if new_role == "admin" and status != "active":
                return NOT_ACTIVE
            cur.execute(
                """UPDATE app_user
                      SET role_code = %s
                    WHERE user_id = %s AND NOT is_deleted AND role_code IN ('user', 'admin')""",
                (new_role, user_id),
            )
            return OK if cur.rowcount == 1 else NOT_FOUND
    finally:
        conn.close()


# ---- helpers -----------------------------------------------------------------

def clean_names(data):
    first = str(data.get("first_name", "")).strip()
    last = str(data.get("last_name", "")).strip()
    if not first or not last:
        return None, None, "First name and last name are required."
    if len(first) > MAX_NAME or len(last) > MAX_NAME:
        return None, None, f"Names must be {MAX_NAME} characters or fewer."
    return first, last, None


def set_password_link(token):
    # The host comes from .env and never from the request, so a forged Host
    # header cannot point an emailed link at another site.
    base = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base}{url_for('auth.set_password_page')}?token={token}"


def welcome_email_body(first_name, link):
    return (
        f"Hello {first_name},\n\n"
        "An administrator created an account for you on Hope, Inc. ERP.\n\n"
        f"Open this link to choose your password. It works once and expires in {SET_PASSWORD_DAYS} days:\n\n"
        f"{link}\n\n"
        "If you were not expecting this, you can ignore this email.\n"
    )


def approval_email_body(first_name, link):
    return (
        f"Hello {first_name},\n\n"
        "Your Hope, Inc. ERP account has been approved.\n\n"
        f"Open this link to choose your password. It works once and expires in {SET_PASSWORD_DAYS} days:\n\n"
        f"{link}\n\n"
        "If you did not register for this account, ignore this email.\n"
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

    # Only visible to those who can see superadmins. Marks the one superadmin
    # who must not be blocked, because nobody else could sign in to fix things.
    active_superadmins = [
        u["user_id"]
        for u in users
        if u["role_code"] == "superadmin" and u["account_status"] == "active" and not u["is_blocked"]
    ]
    last_superadmin = active_superadmins[0] if len(active_superadmins) == 1 else None
    for user in users:
        user["is_self"] = user["user_id"] == me["user_id"]
        user["is_last_superadmin"] = user["user_id"] == last_superadmin
    return jsonify(ok=True, users=users, viewer_role=me["role_code"])


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
    # plain 'user' and active. Making admins is a superadmin action, below.
    token = secrets.token_hex(32)
    try:
        user_id = create_user_with_link(first, last, email, hash_token(token))
    except psycopg2.Error:
        current_app.logger.exception("Adding a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if user_id is None:
        return jsonify(ok=False, error="An account with this email already exists."), 409

    send_email_async(email, "Your Hope, Inc. ERP account", welcome_email_body(first, set_password_link(token)))

    user = {
        "user_id": user_id,
        "first_name": first,
        "last_name": last,
        "email": email,
        "role_code": "user",
        "account_status": "active",
        "is_blocked": False,
        "is_self": False,
        "is_last_superadmin": False,
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
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404
    return jsonify(ok=True)


def change_blocked(user_id, blocked):
    me = current_user()
    if blocked and user_id == me["user_id"]:
        return jsonify(ok=False, error="You cannot block your own account."), 400
    try:
        result = set_blocked(user_id, blocked, manageable_roles(me["role_code"]))
    except psycopg2.Error:
        current_app.logger.exception("Blocking or unblocking a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if result == NOT_FOUND:
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404
    if result == LAST_SUPERADMIN:
        return jsonify(ok=False, error="You cannot block the last active superadmin."), 400
    return jsonify(ok=True)


@users_bp.post("/api/users/<int:user_id>/block")
@roles_required(*ADMIN_ROLES)
def api_block_user(user_id):
    return change_blocked(user_id, True)


@users_bp.post("/api/users/<int:user_id>/unblock")
@roles_required(*ADMIN_ROLES)
def api_unblock_user(user_id):
    return change_blocked(user_id, False)


# ---- superadmin only: approve pending users and choose admins ------------------

@users_bp.post("/api/users/<int:user_id>/approve")
@roles_required("superadmin")
def api_approve_user(user_id):
    token = secrets.token_hex(32)
    try:
        outcome = approve_user(user_id, hash_token(token))
    except psycopg2.Error:
        current_app.logger.exception("Approving a user failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if outcome is None:
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404
    if outcome["result"] == ALREADY_APPROVED:
        return jsonify(ok=False, error="This account is already approved."), 400

    # A registered person has no password yet. The emailed link is how they get
    # one, and opening it also proves the address really is theirs.
    if outcome["needs_link"]:
        send_email_async(
            outcome["email"],
            "Your Hope, Inc. ERP account was approved",
            approval_email_body(outcome["first_name"], set_password_link(token)),
        )
    return jsonify(
        ok=True,
        link_sent=outcome["needs_link"],
        email=outcome["email"],
        email_configured=bool(os.getenv("SMTP_HOST")),
    )


@users_bp.post("/api/users/<int:user_id>/role")
@roles_required("superadmin")
def api_set_role(user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    # Only these two roles can be chosen here. Superadmins come from the database seed.
    new_role = data.get("role_code")
    if new_role not in ("admin", "user"):
        return jsonify(ok=False, error="The role must be admin or user."), 400
    if user_id == current_user()["user_id"]:
        return jsonify(ok=False, error="You cannot change your own role."), 400

    try:
        result = set_role(user_id, new_role)
    except psycopg2.Error:
        current_app.logger.exception("Changing a role failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if result == NOT_FOUND:
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404
    if result == PROTECTED:
        return jsonify(ok=False, error="Superadmin accounts cannot be changed here."), 400
    if result == NOT_ACTIVE:
        return jsonify(ok=False, error="Approve this account before making it an admin."), 400
    return jsonify(ok=True)
