#!/usr/bin/env python3
"""Issue one-time set-password links for accounts that do not have a password yet (S1-DBA-05).

Usage:
    python db/issue_set_password_links.py                      # every active superadmin without a password
    python db/issue_set_password_links.py --email a@b.com      # one account only
    python db/issue_set_password_links.py --role all           # any role (admin, user, superadmin)
    python db/issue_set_password_links.py --days 3             # link lifetime in days (default 7)

How it works
  1. For each account, a random token is made on THIS computer.
  2. Only the SHA-256 hash of the token is saved in password_reset_token (purpose 'set_password').
  3. The full link is printed in this terminal and saved nowhere.
     Send each link privately to its owner (never to the repo or a group chat).
  4. Running it again for an account cancels its older unused links and issues a new one.

Settings (in .env):  DATABASE_URL (required), APP_BASE_URL (default http://localhost:3000),
                     SET_PASSWORD_PATH (default /set-password; must match the Developers' page).
"""
import argparse
import hashlib
import os
import secrets
import sys

import psycopg2
from dotenv import load_dotenv


def make_token():
    token = secrets.token_hex(32)                                   # same format as Node: randomBytes(32).toString('hex')
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()  # same as Node: createHash('sha256').update(token).digest('hex')
    return token, token_hash


def main():
    parser = argparse.ArgumentParser(description="Issue one-time set-password links.")
    parser.add_argument("--email", help="only this account")
    parser.add_argument("--role", default="superadmin", help="role to include: superadmin (default), admin, user or all")
    parser.add_argument("--days", type=int, default=7, help="days the link stays valid (1 to 30, default 7)")
    args = parser.parse_args()
    if not 1 <= args.days <= 30:
        sys.exit("--days must be between 1 and 30.")

    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is missing. Copy .env.example to .env and fill it in.")
    base = os.environ.get("APP_BASE_URL", "http://localhost:3000").rstrip("/")
    path = os.environ.get("SET_PASSWORD_PATH", "/set-password")
    if not path.startswith("/"):
        path = "/" + path

    role = None if args.role == "all" else args.role
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    try:
        cur.execute(
            """select user_id, email from app_user
                where password_hash is null
                  and account_status = 'active' and not is_blocked and not is_deleted
                  and (%s::text is null or role_code = %s)
                  and (%s::text is null or lower(email) = lower(%s))
                order by user_id""",
            (role, role, args.email, args.email),
        )
        users = cur.fetchall()
        if not users:
            print("No matching accounts without a password. Nothing to do.")
            conn.rollback()
            return

        issued = []
        for user_id, email in users:
            # cancel older unused set-password links for this account
            cur.execute(
                """update password_reset_token set is_used = true, used_at = now()
                    where user_id = %s and purpose = 'set_password' and not is_used and not is_deleted""",
                (user_id,),
            )
            token, token_hash = make_token()
            cur.execute(
                """insert into password_reset_token (user_id, token_hash, purpose, expires_at)
                   values (%s, %s, 'set_password', now() + make_interval(days => %s))""",
                (user_id, token_hash, args.days),
            )
            issued.append((email, f"{base}{path}?token={token}"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\nOne-time set-password links (valid {args.days} day(s), usable once):\n")
    for email, link in issued:
        print(f"  {email}\n  {link}\n")
    print("These links are NOT saved anywhere. Send each one privately to its owner.")
    print("Do not paste them into the repo, a file in the repo, or a group chat.")


if __name__ == "__main__":
    main()
