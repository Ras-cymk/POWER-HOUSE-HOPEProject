import psycopg2
from flask import Blueprint, current_app, jsonify, request

from app.audit import audit_name
from app.permissions import rights_target_roles, roles_required
from app.rights import NOT_FOUND, OK, UNKNOWN_RIGHT, load_catalogue, load_user_rights, save_rights
from app.security import current_user


rights_bp = Blueprint("rights", __name__)

ADMIN_ROLES = ("admin", "superadmin")
MAX_RIGHTS = 200  # far more than the catalogue holds, just to refuse absurd requests
NOT_FOUND_MESSAGE = "User not found."


@rights_bp.get("/api/users/<int:user_id>/rights")
@roles_required(*ADMIN_ROLES)
def api_get_rights(user_id):
    roles = rights_target_roles(current_user()["role_code"])
    try:
        found = load_user_rights(user_id, roles)
        modules = load_catalogue() if found else None
    except psycopg2.Error:
        current_app.logger.exception("Loading rights failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500
    if found is None:
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404

    for module in modules:
        for right in module["rights"]:
            right["granted"] = right["perm_code"] in found["granted"]
    return jsonify(ok=True, user=found["user"], modules=modules)


@rights_bp.put("/api/users/<int:user_id>/rights")
@roles_required(*ADMIN_ROLES)
def api_save_rights(user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Invalid request."), 400

    # The full list of rights the person should hold after saving
    rights = data.get("rights")
    if not isinstance(rights, list) or len(rights) > MAX_RIGHTS or not all(isinstance(c, str) for c in rights):
        return jsonify(ok=False, error="The rights must be a list of right codes."), 400

    me = current_user()
    try:
        outcome = save_rights(user_id, rights, rights_target_roles(me["role_code"]), audit_name(me))
    except psycopg2.Error:
        current_app.logger.exception("Saving rights failed")
        return jsonify(ok=False, error="Server error. Please try again."), 500

    if outcome["result"] == NOT_FOUND:
        return jsonify(ok=False, error=NOT_FOUND_MESSAGE), 404
    if outcome["result"] == UNKNOWN_RIGHT:
        return jsonify(ok=False, error="Unknown right: " + outcome["code"][:60]), 400
    assert outcome["result"] == OK
    return jsonify(ok=True, granted=outcome["granted"], revoked=outcome["revoked"])
