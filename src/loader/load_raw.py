import os
import pandas as pd
from src.loader.detect_columns import detect_columns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _postgres_url() -> str | None:
    """Restituisce la DATABASE_URL PostgreSQL normalizzata, o None se è SQLite/assente."""
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        return url
    return None


def _load_from_db(db_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Legge df_beh e df_perf dalle tabelle Supabase via SQL diretto."""
    import logging
    from sqlalchemy import create_engine, text

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args={"sslmode": "require", "connect_timeout": 30},
    )
    try:
        with engine.connect() as conn:
            df_beh  = pd.read_sql(text("SELECT * FROM comportamento_hcp"),   conn)
            df_perf = pd.read_sql(text("SELECT * FROM performance_channel"), conn)
        logging.info(
            "[MCM] DB loaded — comportamento_hcp: %d rows, performance_channel: %d rows",
            len(df_beh), len(df_perf),
        )
    except Exception:
        logging.exception("[MCM] Errore caricamento dati da Supabase")
        raise
    finally:
        engine.dispose()
    return df_beh, df_perf


def _load_from_excel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Legge df_beh e df_perf dai file Excel in data_raw/."""
    raw_folder = os.environ.get(
        "DATA_RAW_PATH",
        os.path.join(PROJECT_ROOT, "data_raw"),
    )
    raw_folder = os.path.abspath(raw_folder)

    if not os.path.exists(raw_folder):
        raise FileNotFoundError(f"Cartella data_raw non trovata: {raw_folder}")

    files     = os.listdir(raw_folder)
    file_beh  = next((f for f in files if "Comportamento" in f), None)
    file_perf = next((f for f in files if "Performance"   in f), None)

    if not file_beh or not file_perf:
        raise FileNotFoundError(
            f"File Excel non trovati in: {raw_folder}\n"
            "Attesi: *Comportamento*.xlsx e *Performance*.xlsx"
        )

    df_beh  = pd.read_excel(os.path.join(raw_folder, file_beh))
    df_perf = pd.read_excel(os.path.join(raw_folder, file_perf))
    return df_beh, df_perf


def load_data() -> dict:
    """
    Carica i dati da PostgreSQL (produzione) o da file Excel (sviluppo locale).
    La scelta avviene automaticamente in base a DATABASE_URL.
    """
    db_url = _postgres_url()
    if db_url:
        df_beh, df_perf = _load_from_db(db_url)
    else:
        df_beh, df_perf = _load_from_excel()

    columns = detect_columns(df_beh, df_perf)
    return {"df_beh": df_beh, "df_perf": df_perf, "columns": columns}
