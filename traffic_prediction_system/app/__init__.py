from flask import Flask, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path
from werkzeug.security import generate_password_hash
from sqlalchemy import text, inspect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"

def _migrate_schema():
    """Small SQLite-safe additive migration for installations created by V1."""
    from .models import TrafficRecord, Prediction
    insp=inspect(db.engine)
    additions={
        "traffic_record":[("latitude","FLOAT"),("longitude","FLOAT"),("visibility","FLOAT"),("humidity","FLOAT"),("wind_speed","FLOAT")],
        "prediction":[("explanation","TEXT")]
    }
    for table,cols in additions.items():
        existing={c["name"] for c in insp.get_columns(table)} if insp.has_table(table) else set()
        for col,typ in cols:
            if col not in existing:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
    db.session.commit()

def _csrf_token():
    import secrets
    token=session.get("_csrf")
    if not token:
        token=secrets.token_urlsafe(32); session["_csrf"]=token
    return token

def create_app():
    app=Flask(__name__,instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True,exist_ok=True)
    import os
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY","change-this-secret-key-before-deployment"),
        SQLALCHEMY_DATABASE_URI="sqlite:///"+str(Path(app.instance_path)/"traffic.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=2*1024*1024)
    db.init_app(app); login_manager.init_app(app)

    @app.context_processor
    def inject_csrf():
        return {"csrf_token":_csrf_token}

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Keep raw tracebacks out of normal user responses.
        app.logger.exception("Unhandled application error")
        if request.path.startswith("/api/"):
            return jsonify({"error":"An unexpected server error occurred. Please try again."}),500
        return "An unexpected server error occurred. Please try again.",500

    @app.before_request
    def csrf_protect():
        if request.method=="POST" and request.endpoint not in {"auth.login","auth.register"}:
            supplied=request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
            if not supplied or supplied != session.get("_csrf"):
                if request.path.startswith("/api/"):
                    return jsonify({"error":"CSRF validation failed"}),400
                return "CSRF validation failed",400

    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    app.register_blueprint(auth_bp); app.register_blueprint(main_bp); app.register_blueprint(admin_bp)

    from .models import User
    with app.app_context():
        db.create_all()
        _migrate_schema()
        if not User.query.filter_by(email="admin@traffic.local").first():
            db.session.add(User(name="System Administrator",email="admin@traffic.local",
                password_hash=generate_password_hash("Admin@12345"),role="admin"))
            db.session.commit()
    return app
