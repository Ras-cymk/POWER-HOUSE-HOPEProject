from flask import Blueprint, render_template

from app.security import current_user, login_required


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    return render_template("landing.html")


@main_bp.route("/home")
@login_required
def home():
    # Placeholder so you can see that sign-in works. S1-DEV-08 builds the real main page.
    return render_template("home.html", user=current_user())