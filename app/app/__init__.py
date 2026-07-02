from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    from app.routes.web import bp as web_bp
    from app.routes.api import bp as api_bp
    from app.routes.auth import bp as auth_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")

    return app
