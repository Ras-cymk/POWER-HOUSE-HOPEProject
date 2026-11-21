from flask import Blueprint, render_template

from app.navigation import ROLE_NAMES, build_nav, module_access
from app.security import current_user, login_required


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    return render_template("landing.html")


@main_bp.route("/home")
@login_required
def home():
    user = current_user()
    return render_template(
        "home.html",
        user=user,
        role_name=ROLE_NAMES.get(user["role_code"], user["role_code"]),
        nav=build_nav(user, module_access(user)),
    )
