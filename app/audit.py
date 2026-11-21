MAX_AUDIT_NAME = 32


def audit_name(user):
    """The name the database's audit trail records for this person.

    audit_user() in the database reads the setting app.username. That name ends up
    in audit_log.action_by (50 characters) and in the stamp column of every table.
    The stamp of the HOPE tables is only 60 characters wide and must also hold the
    action word and the time, so the email address is cut to 32 characters.
    """
    name = (user.get("email") or "").strip()[:MAX_AUDIT_NAME]
    return name or f"user-{user['user_id']}"
