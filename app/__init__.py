from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .admin import bp as admin_bp
from .extensions import db
from .public import bp as public_bp
from .seed import ensure_seed_data


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    database_path = os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "site.db"))
    upload_root = os.environ.get("UPLOAD_ROOT", os.path.join(app.instance_path, "uploads"))
    database_dir = os.path.dirname(database_path)
    sqlalchemy_db_path = Path(database_path).resolve().as_posix()

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "synthetic-frontier-secret"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{sqlalchemy_db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DATABASE_PATH=database_path,
        UPLOAD_ROOT=upload_root,
    )

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    os.makedirs(app.instance_path, exist_ok=True)
    if database_dir:
        os.makedirs(database_dir, exist_ok=True)
    os.makedirs(upload_root, exist_ok=True)
    os.makedirs(os.path.join(upload_root, "images"), exist_ok=True)
    os.makedirs(os.path.join(upload_root, "files"), exist_ok=True)

    db.init_app(app)

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        with app.app_context():
            ensure_seed_data()
        print("Database initialized.")

    with app.app_context():
        ensure_seed_data()

    return app
