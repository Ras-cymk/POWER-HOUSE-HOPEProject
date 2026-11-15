from functools import wraps

from flask import abort, jsonify, request

from app.security import current_user, login_required

# Which roles each role may see, edit and block on the User Management screen.
# An Admin manages Users only, so Admin and Superadmin accounts are hidden from them.
MANAGEABLE_ROLES = {
    "superadmin": ("user", "admin", "superadmin"),
    "admin": ("user",),
}


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
