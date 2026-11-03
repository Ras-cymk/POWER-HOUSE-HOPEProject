from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
