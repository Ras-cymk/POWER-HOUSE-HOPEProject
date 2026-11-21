from flask import Blueprint, abort, jsonify, render_template

from app.navigation import ROLE_NAMES, build_nav, module_access
from app.security import current_user, login_required


modules_bp = Blueprint("modules", __name__)


@modules_bp.get("/modules/<module_code>")
@login_required
def module_page(module_code):
    """Placeholder for a module's screens, which are built in later sprints.

    The access check is real: without a right in the module the server answers
    403, whatever the menu shows.
    """
    user = current_user()
    modules = module_access(user)
    module = next((m for m in modules if m["module_code"] == module_code), None)
    if module is None:
        abort(404)
    if not module["accessible"]:
        abort(403)
    return render_template(
        "module.html",
        user=user,
        module=module,
        nav=build_nav(user, modules),
        role_name=ROLE_NAMES.get(user["role_code"], user["role_code"]),
    )


@modules_bp.get("/api/me/rights")
@login_required
def api_my_rights():
    """What the signed-in person may do, for screens and tests that need to adapt."""
    user = current_user()
    modules = module_access(user)
    return jsonify(
        ok=True,
        role_code=user["role_code"],
        all_rights=user["role_code"] == "superadmin",
        rights=[r["perm_code"] for m in modules for r in m["rights"] if r["granted"]],
        modules=[
            {"module_code": m["module_code"], "module_name": m["module_name"], "held": m["held"], "total": m["total"]}
            for m in modules
        ],
    )
