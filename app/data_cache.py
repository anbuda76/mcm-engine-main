"""
app/data_cache.py
─────────────────
Cache in-memory per DataFrame pandas.
- Thread-safe
- TTL configurabile (CACHE_TTL_HOURS, default 8h)
- Metadati: loaded_at, n. righe, scadenza
"""

import sys
import os
import threading
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.loader.load_raw import load_data

_cache = {}
_lock  = threading.Lock()


def _ttl_hours() -> int:
    """Legge CACHE_TTL_HOURS dalla configurazione Flask (se disponibile) o da env."""
    try:
        from flask import current_app
        return int(current_app.config.get("CACHE_TTL_HOURS", 8))
    except RuntimeError:
        return int(os.environ.get("CACHE_TTL_HOURS", 8))


def _is_expired() -> bool:
    loaded_at = _cache.get("loaded_at")
    if loaded_at is None:
        return True
    return datetime.now() - loaded_at > timedelta(hours=_ttl_hours())


def get_data() -> dict:
    """
    Ritorna dict con df_beh, df_perf, columns.
    Ricarica automaticamente se la cache è scaduta (TTL).
    """
    with _lock:
        if "data" not in _cache or _is_expired():
            _cache["data"]      = load_data()
            _cache["loaded_at"] = datetime.now()
        return _cache["data"]


def invalidate() -> None:
    """Svuota la cache — forzando il reload al prossimo get_data()."""
    with _lock:
        _cache.clear()


def get_cache_info() -> dict:
    """
    Ritorna metadati sulla cache corrente.
    Utile per la dashboard di amministrazione.
    """
    with _lock:
        loaded_at = _cache.get("loaded_at")
        data      = _cache.get("data")
        ttl_h     = _ttl_hours()

        if loaded_at and data:
            expires_at  = loaded_at + timedelta(hours=ttl_h)
            remaining   = expires_at - datetime.now()
            remaining_m = max(0, int(remaining.total_seconds() / 60))
            n_beh  = len(data["df_beh"])  if data.get("df_beh")  is not None else 0
            n_perf = len(data["df_perf"]) if data.get("df_perf") is not None else 0
        else:
            expires_at  = None
            remaining_m = 0
            n_beh       = 0
            n_perf      = 0

        return {
            "loaded":      loaded_at is not None,
            "loaded_at":   loaded_at.strftime("%d/%m/%Y %H:%M") if loaded_at else None,
            "expires_at":  expires_at.strftime("%d/%m/%Y %H:%M") if expires_at else None,
            "remaining_m": remaining_m,
            "n_beh":       n_beh,
            "n_perf":      n_perf,
            "ttl_hours":   ttl_h,
        }


def get_specializzazioni() -> list:
    """Lista unica di specializzazioni disponibili nel dataset."""
    data = get_data()
    col  = data["columns"].get("col_target")
    if not col or col not in data["df_beh"].columns:
        return []
    vals = data["df_beh"][col].dropna().unique().tolist()
    return sorted([str(v) for v in vals])


def get_aree_terapeutiche() -> dict:
    """
    Ritorna struttura gerarchica:
    { "Area canonica": ["Patologia A", "Patologia B", ...], ... }
    Aree ordinate per frequenza (desc), patologie ordinate alfabeticamente.
    Usato dal filtro Area Terapeutica di Modulo 1.
    """
    import re
    from src.behavior.mappe.mappa_patologie import normalizza_q7a, normalizza_q7b

    data    = get_data()
    df_beh  = data["df_beh"]

    # Trova colonne Q7a e Q7b_*
    q7a_col  = next((c for c in df_beh.columns if c.startswith("Q7a")), None)
    # Q7b_1 = patologia primaria: usata per costruire la gerarchia area → patologie
    # (lista pulita, senza contaminazione da patologie secondarie/terziarie)
    q7b1_col = next((c for c in df_beh.columns if re.match(r"Q7b_1(\s|$)", c)), None)

    if not q7a_col or not q7b1_col:
        return {}

    # --- Costruisce conteggi per ogni (area_norm, patologia_norm) ---
    from collections import Counter
    counts: dict[str, Counter] = {}

    ESCLUDI = {"altro", "specificare la patologia", "nan", "none", ""}
    for _, row in df_beh[[q7a_col, q7b1_col]].iterrows():
        area = normalizza_q7a(row[q7a_col])
        if not area:
            continue
        if area not in counts:
            counts[area] = Counter()
        pat = normalizza_q7b(row[q7b1_col])
        if pat and pat.lower() not in ESCLUDI:
            # Deduplicazione case-insensitive: normalizza a title per il contatore
            counts[area][pat.title()] += 1

    # --- Filtra: min MIN_COUNT occorrenze, max TOP_N per area ---
    MIN_COUNT = 3
    TOP_N     = 40
    result: dict[str, list] = {}
    for area, ctr in counts.items():
        top = [p for p, n in ctr.most_common(TOP_N) if n >= MIN_COUNT]
        if top:
            result[area] = sorted(top)

    # Ordina secondo le 13 aree canoniche ATC (ordine fisso)
    from src.behavior.mappe.mappa_patologie import AREE_CANONICHE
    return {
        area: result[area]
        for area in AREE_CANONICHE
        if area in result and result[area]
    }


def get_aziende() -> list:
    """Lista unica di aziende disponibili nel dataset Performance."""
    data   = get_data()
    col_az = data["columns"].get("col_azienda")
    if not col_az or col_az not in data["df_perf"].columns:
        return []
    return sorted(data["df_perf"][col_az].dropna().unique().tolist())
