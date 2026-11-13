from datetime import timedelta

from flask import Flask


def create_app():
    app = Flask(__name__)

    # Needed to sign the session cookie. Only the web app needs it, so it is
    # checked here and not in config.py (scripts that just use the database
    # don't have to set it).
    from app.config import SECRET_KEY
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is missing. Add it to your .env file. Make one with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    app.config.update(
        SECRET_KEY=SECRET_KEY,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Set SESSION_COOKIE_SECURE=True once the site is served over HTTPS
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.password_reset import reset_bp
    app.register_blueprint(reset_bp)

    from app.routes.users import users_bp
    app.register_blueprint(users_bp)

    return app
