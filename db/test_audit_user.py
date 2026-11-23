#!/usr/bin/env python3
"""S1-DBA-06 test: does audit_user() record the logged-in user?

Usage:  python db/test_audit_user.py

It changes one customer row inside a transaction and reads the audit_log row and the stamp, then rolls
EVERYTHING back, so nothing is left in the database. It needs DATABASE_URL in .env and the S1-DBA-06
migration applied. Exit code 0 = all checks passed, 1 = something failed.
"""
import os
import sys

import psycopg2
from dotenv import load_dotenv

NAME = "jdoe@gmail.com"


def main():
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is missing. Copy .env.example to .env and fill it in.")

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    passed = []

    def check(label, ok, detail=""):
        passed.append(ok)
        print(("PASS  " if ok else "FAIL  ") + label + (f"   [{detail}]" if detail else ""))

    cur.execute("select count(*) from audit_log")
    rows_before = cur.fetchone()[0]
    cur.execute("select custno from customer where not is_deleted order by custno limit 1")
    row = cur.fetchone()
    if not row:
        conn.rollback()
        sys.exit("No customer rows to test with. Apply the S1-DBA-02 migrations first.")
    custno = row[0]
    cur.execute("select session_user")
    db_login = cur.fetchone()[0]

    def change_customer():
        """Flip payterm (COD <-> 30D) and return (action, action_by, stamp) from the newest audit row."""
        cur.execute("update customer set payterm = case payterm when 'COD' then '30D' else 'COD' end "
                    "where custno = %s", (custno,))
        cur.execute("select action, action_by from audit_log order by audit_id desc limit 1")
        action, action_by = cur.fetchone()
        cur.execute("select stamp from customer where custno = %s", (custno,))
        return action, action_by, cur.fetchone()[0]

    try:
        # 1. a named user is recorded
        cur.execute("select set_config('app.username', %s, true)", (NAME,))
        action, by, stamp = change_customer()
        check("named user goes into audit_log", action == "EDIT" and by == NAME, f"action_by={by}")
        check("named user goes into the stamp", stamp.startswith(f"EDIT {NAME} "), stamp)

        # 2. no name set: falls back to the database login
        cur.execute("select set_config('app.username', '', true)")
        _, by, stamp = change_customer()
        check("no name set: database login is used", by == db_login, f"action_by={by}")

        # 3. a very long name is cut, and the write does not fail
        cur.execute("select set_config('app.username', %s, true)", ("x" * 200,))
        _, by, stamp = change_customer()
        check("200-character name is cut to 80, write succeeds", len(by) == 80 and len(stamp) <= 120,
              f"action_by length={len(by)}, stamp length={len(stamp)}")
    except Exception as e:
        passed.append(False)
        print(f"FAIL  the test hit a database error: {e}")
    finally:
        conn.rollback()

    # 4. the name is gone after the rollback (it is transaction-local), and nothing was left behind
    cur.execute("select current_setting('app.username', true)")
    leftover = cur.fetchone()[0]
    check("name does not leak into the next transaction", leftover in (None, ""), f"value={leftover!r}")
    cur.execute("select count(*) from audit_log")
    check("test left no rows behind", cur.fetchone()[0] == rows_before)
    conn.rollback()
    conn.close()

    print("\nAll checks passed." if all(passed) else "\nSome checks FAILED.")
    sys.exit(0 if all(passed) else 1)


if __name__ == "__main__":
    main()
