import os
import warnings
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import config


def create_app(env=None):
    """Application Factory — crea e configura l'istanza Flask."""
    app = Flask(__name__)

    # Configurazione ambiente
    env = env or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[env])

    # Crea la cartella instance/ solo per SQLite (sviluppo locale)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    # ─── SQLAlchemy ───────────────────────────────────────────
    from app.models import db
    db.init_app(app)

    # ─── Flask-Login ──────────────────────────────────────────
    login_manager = LoginManager()
    login_manager.login_view    = "auth.login"
    login_manager.login_message = "Accedi per continuare."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ─── Context processor — inietta user_modules in tutti i template ─
    @app.context_processor
    def inject_user_permissions():
        from flask_login import current_user
        if current_user.is_authenticated:
            return {
                "user_modules": current_user.modules if not current_user.is_admin
                                else ["comportamento", "performance", "trend"],
                "current_user_is_admin": current_user.is_admin,
            }
        return {"user_modules": [], "current_user_is_admin": False}

    # ─── Registrazione Blueprints ─────────────────────────────
    from app.routes.auth       import auth_bp
    from app.routes.admin      import admin_bp
    from app.routes.dashboard  import dashboard_bp
    from app.routes.modulo1    import modulo1_bp
    from app.routes.modulo2    import modulo2_bp
    from app.routes.trend      import trend_bp
    from app.routes.api        import api_bp
    from app.routes.ai_assistant import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,   url_prefix="/admin")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(modulo1_bp, url_prefix="/modulo1")
    app.register_blueprint(modulo2_bp, url_prefix="/modulo2")
    app.register_blueprint(trend_bp,   url_prefix="/trend")
    app.register_blueprint(api_bp,     url_prefix="/api")
    app.register_blueprint(ai_bp,      url_prefix="/ai")

    # ─── Inizializza DB + crea admin di default ───────────────
    with app.app_context():
        db.create_all()
        _migrate_db(db)          # aggiunge colonne nuove su tabelle esistenti
        _create_default_admin(app, db)

    # ─── Error handlers ──────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Pagina non trovata"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Errore interno del server"}, 500

    return app


def _migrate_db(db):
    """Aggiunge colonne mancanti alle tabelle esistenti. Sicuro da rieseguire ad ogni avvio."""
    from sqlalchemy import text

    dialect = db.engine.dialect.name  # 'postgresql' o 'sqlite'

    if dialect == "postgresql":
        migrations = [
            "ALTER TABLE mcm_users ADD COLUMN IF NOT EXISTS agents TEXT NOT NULL DEFAULT '[]'",
        ]
        with db.engine.connect() as conn:
            for stmt in migrations:
                conn.execute(text(stmt))
            conn.commit()
    else:
        # SQLite: ADD COLUMN IF NOT EXISTS non garantito su versioni vecchie
        migrations = [
            "ALTER TABLE mcm_users ADD COLUMN agents TEXT NOT NULL DEFAULT '[]'",
        ]
        with db.engine.connect() as conn:
            for stmt in migrations:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception:
                    pass  # colonna già presente


def _create_default_admin(app, db):
    """Crea l'utente admin di default se il DB è vuoto."""
    from app.models import User
    if User.query.first() is not None:
        return  # utenti già presenti

    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]

    admin = User()
    admin.username = username
    admin.set_password(password)
    admin.is_admin   = True
    admin._is_active = True
    admin.modules    = ["comportamento", "performance", "trend"]
    admin.targets    = []
    admin.aziende    = []
    db.session.add(admin)
    db.session.commit()

    if password == "changeme":
        warnings.warn(
            f"[MCM] Admin creato con password di default '{password}'. "
            "Cambiala subito dal pannello Admin!",
            stacklevel=2,
        )
    else:
        print(f"[MCM] Admin '{username}' creato.")
