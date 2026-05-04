import os

_BASE = os.path.dirname(os.path.dirname(__file__))


def _resolve_db_url(url: str) -> str:
    """Supabase/Railway restituiscono 'postgres://', SQLAlchemy richiede 'postgresql://'."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY      = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", 8))

    _data_raw = os.environ.get("DATA_RAW_PATH", os.path.join(_BASE, "data_raw"))
    DATA_RAW_PATH = os.path.abspath(_data_raw)
    UPLOAD_FOLDER = DATA_RAW_PATH

    SQLALCHEMY_DATABASE_URI = _resolve_db_url(
        os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(_BASE, "instance", "mcm.db"),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # rileva connessioni SSL stantie (fix PgBouncer/Supabase)
        "pool_recycle": 300,     # ricicla connessioni ogni 5 minuti
    }

    # Primo admin — creato automaticamente se il DB è vuoto
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")


class DevelopmentConfig(Config):
    DEBUG   = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG   = False
    TESTING = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
