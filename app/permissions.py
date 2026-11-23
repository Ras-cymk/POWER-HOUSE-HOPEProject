from functools import wraps

from flask import abort, jsonify, request

from app.rights import granted_codes
from app.security import current_user, login_required

# Which roles each role may see, edit and block on the User Management screen.
# An Admin manages Users only, so Admin and Superadmin accounts are hidden from them.
MANAGEABLE_ROLES = {
    "superadmin": ("user", "admin", "superadmin"),
    "admin": ("user",),
}


# Whose rights each role may set in the Rights dialog. Superadmins hold every right,
# so they have no dialog, and nobody can change a superadmin's rights.
RIGHTS_TARGET_ROLES = {
    "superadmin": ("user", "admin"),
    "admin": ("user",),
}


def rights_target_roles(role_code):
    """Roles whose rights this role may set. Empty for roles with no access."""
    return RIGHTS_TARGET_ROLES.get(role_code, ())


def manageable_roles(role_code):
    """Roles this role may manage. Empty for roles with no access."""
    return MANAGEABLE_ROLES.get(role_code, ())


def roles_required(*roles):
    """Allow only these roles, on top of being signed in.

    This runs on the server, so hiding a button is never the only protection.
    """

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user()["role_code"] not in roles:
                if request.path.startswith("/api/"):
                    return jsonify(ok=False, error="You do not have access to this."), 403
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def has_right(perm_code):
    """True if the signed-in person may do this action. Superadmins hold every right."""
    user = current_user()
    if user is None:
        return False
    if user["role_code"] == "superadmin":
        return True
    return perm_code in granted_codes(user["user_id"])


def right_required(perm_code):
    """Allow only people who hold this right, on top of being signed in.

    Like roles_required, this runs on the server. Pages and buttons should also
    follow the rights, but hiding a button is never the only protection.
    """

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not has_right(perm_code):
                if request.path.startswith("/api/"):
                    return jsonify(ok=False, error="You do not have this right."), 403
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
