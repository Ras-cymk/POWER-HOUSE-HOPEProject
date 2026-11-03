import re

import psycopg2
from flask import Blueprint, current_app, jsonify, request

from app.db import get_connection


auth_bp = Blueprint("auth", __name__, url_prefix="/api")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Limits match the app_user column sizes
MAX_NAME = 50
MAX_EMAIL = 100


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


@auth_bp.post("/register")
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
