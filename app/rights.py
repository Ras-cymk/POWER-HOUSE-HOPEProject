from psycopg2.extras import Json, execute_values

from app.db import get_connection

# What save_rights reports when it cannot go ahead
OK = "ok"
NOT_FOUND = "not_found"
UNKNOWN_RIGHT = "unknown_right"


def load_catalogue():
    """The rights catalogue grouped by module, in screen order."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT m.module_code, m.module_name, p.perm_code, p.perm_name
                     FROM module m
                     JOIN permission p ON p.module_code = m.module_code
                    WHERE NOT m.is_deleted AND NOT p.is_deleted
                    ORDER BY m.sort_order, m.module_code, p.sort_order, p.perm_code"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    modules, by_code = [], {}
    for module_code, module_name, perm_code, perm_name in rows:
        if module_code not in by_code:
            by_code[module_code] = {"module_code": module_code, "module_name": module_name, "rights": []}
            modules.append(by_code[module_code])
        by_code[module_code]["rights"].append({"perm_code": perm_code, "perm_name": perm_name})
    return modules


def load_user_rights(user_id, roles):
    """The person and the rights they hold now, or None if there is no such
    person among the roles the caller may set rights for."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, first_name, last_name, role_code
                     FROM app_user
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)""",
                (user_id, list(roles)),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT perm_code FROM user_permission WHERE user_id = %s AND NOT is_deleted",
                (user_id,),
            )
            granted = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()
    return {
        "user": {"user_id": row[0], "first_name": row[1], "last_name": row[2], "role_code": row[3]},
        "granted": granted,
    }


def granted_codes(user_id):
    """The codes of the rights this person holds now."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT perm_code FROM user_permission WHERE user_id = %s AND NOT is_deleted",
                (user_id,),
            )
            return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def plan_changes(current, wanted):
    """Work out what has to change.

    current maps perm_code to is_deleted for the rows that already exist, and
    wanted is the set of codes that should be granted. Returns three sorted
    lists: rights to add (no row yet), to restore (row was soft-deleted) and
    to delete (row is active but no longer wanted).
    """
    to_add = sorted(code for code in wanted if code not in current)
    to_restore = sorted(code for code in wanted if current.get(code) is True)
    to_delete = sorted(code for code, deleted in current.items() if not deleted and code not in wanted)
    return to_add, to_restore, to_delete


def save_rights(user_id, wanted, roles, actor_name):
    """Make the person's rights exactly the codes in wanted, and log every change.

    Everything is one transaction: the rights and their audit_log entries are saved
    together or not at all. Unticking is a soft delete and re-ticking a restore, as
    for every other table. Returns {"result": NOT_FOUND}, {"result": UNKNOWN_RIGHT,
    "code": ...} or {"result": OK, "granted": n, "revoked": n}.
    """
    wanted = set(wanted)
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            # Lock the person first, so two people saving at once take turns
            cur.execute(
                """SELECT 1 FROM app_user
                    WHERE user_id = %s AND NOT is_deleted AND role_code = ANY(%s)
                      FOR UPDATE""",
                (user_id, list(roles)),
            )
            if cur.fetchone() is None:
                return {"result": NOT_FOUND}

            # Tell the database who is acting. audit_user() reads this setting for
            # the stamp column and for audit_log.action_by.
            cur.execute("SELECT set_config('app.username', %s, true)", (actor_name,))

            cur.execute("SELECT perm_code FROM permission WHERE NOT is_deleted")
            unknown = wanted - {r[0] for r in cur.fetchall()}
            if unknown:
                return {"result": UNKNOWN_RIGHT, "code": sorted(unknown)[0]}

            cur.execute(
                """SELECT perm_code, is_deleted, to_jsonb(user_permission)
                     FROM user_permission
                    WHERE user_id = %s
                      FOR UPDATE""",
                (user_id,),
            )
            existing = {code: (deleted, row) for code, deleted, row in cur.fetchall()}
            to_add, to_restore, to_delete = plan_changes(
                {code: deleted for code, (deleted, _row) in existing.items()}, wanted
            )

            if to_add:
                cur.execute(
                    "INSERT INTO user_permission (user_id, perm_code) SELECT %s, unnest(%s::text[])",
                    (user_id, to_add),
                )
            if to_restore:
                cur.execute(
                    "UPDATE user_permission SET is_deleted = FALSE WHERE user_id = %s AND perm_code = ANY(%s)",
                    (user_id, to_restore),
                )
            if to_delete:
                cur.execute(
                    "UPDATE user_permission SET is_deleted = TRUE WHERE user_id = %s AND perm_code = ANY(%s)",
                    (user_id, to_delete),
                )

            changed = to_add + to_restore + to_delete
            if changed:
                cur.execute(
                    """SELECT perm_code, to_jsonb(user_permission)
                         FROM user_permission
                        WHERE user_id = %s AND perm_code = ANY(%s)""",
                    (user_id, changed),
                )
                new_rows = dict(cur.fetchall())
                entries = (
                    [("ADD", None, code) for code in to_add]
                    + [("RESTORE", existing[code][1], code) for code in to_restore]
                    + [("DELETE", existing[code][1], code) for code in to_delete]
                )
                audit_rows = [
                    (action, f"{user_id}|{code}", Json(old) if old is not None else None, Json(new_rows[code]))
                    for action, old, code in entries
                ]
                execute_values(
                    cur,
                    """INSERT INTO audit_log (table_name, action, record_key, old_values, new_values, action_by)
                       VALUES %s""",
                    audit_rows,
                    template="('user_permission', %s, %s, %s, %s, audit_user())",
                )
            return {"result": OK, "granted": len(to_add) + len(to_restore), "revoked": len(to_delete)}
    finally:
        conn.close()
