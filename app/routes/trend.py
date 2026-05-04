"""
app/routes/trend.py
───────────────────
Blueprint Modulo 3 — Trend Temporali

Route HTML:
  GET  /trend/              → pagina principale (2 tab)

Route API JSON:
  GET  /trend/api/meta      → aziende, anni disponibili, prodotti
  POST /trend/api/kpi       → KPI trend per azienda/prodotto per anno

Route file:
  GET  /trend/export        → download Excel multi-sheet con trend
"""

import sys, os, io, json
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.data_cache import get_data, get_specializzazioni
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP
from src.performance.trend_engine import trend_engine, compute_kpi_for_period
from src.performance.export_trend_xls import export_trend_xlsx

trend_bp = Blueprint("trend", __name__)

# Colonna anno nel DataFrame
COL_ANNO = "Anno"

# Soglia minima HCP per l'analisi (coerente con Modulo 1 e 2)
MIN_HCP = 20


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _filtra(df, col, vals):
    if not vals or not col or col not in df.columns:
        return df
    return df[df[col].isin(vals)].copy()


def _safe_json(obj):
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="records", force_ascii=False))
    if isinstance(obj, dict):
        return {k: (None if (isinstance(v, float) and v != v) else v)
                for k, v in obj.items()}
    return obj


def _norm_canale(df):
    """Applica CANALI_MAP alla colonna Canale."""
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _get_aziende(df_perf, col_az):
    if not col_az or col_az not in df_perf.columns:
        return []
    return df_perf[col_az].value_counts().index.tolist()


def _get_prodotti(df_perf, col_prod, azienda=None, col_az=None):
    if not col_prod or col_prod not in df_perf.columns:
        return []
    if azienda and col_az and col_az in df_perf.columns:
        df = df_perf[df_perf[col_az] == azienda]
    else:
        df = df_perf
    return sorted(df[col_prod].dropna().unique().tolist())


def _get_anni(df_perf):
    if COL_ANNO not in df_perf.columns:
        return []
    return sorted(df_perf[COL_ANNO].dropna().unique().tolist())


def _extrapolate_missing_quarters(kpi_quarterly):
    """
    Riempie i quarter mancanti in due modi:
      - Gap INTERNI (es. Q2 mancante tra Q1 e Q3):
          interpolazione lineare tra i valori adiacenti reali.
          Si applica a TUTTI gli anni.
      - Gap FUTURI (quarter dopo l'ultimo reale, solo per l'anno più recente):
          regressione lineare (estrapolazione) sui quarter reali disponibili.
    Tutti i periodi generati vengono marcati con 'estimated': True.
    Richiede almeno 2 quarter reali per poter stimare.
    """
    import numpy as np

    metrics = ["pen_media", "ric_media", "ing_media", "prop_media", "nps"]
    clamps  = {
        "pen_media":  (0.0, 100.0),
        "ric_media":  (0.0, 100.0),
        "ing_media":  (0.0, 100.0),
        "prop_media": (0.0, 10.0),
        "nps":        (-100.0, 100.0),
    }

    # Parsa solo i periodi REALI (non già stimati) → {anno: {q_num: periodo_str}}
    present = {}
    for periodo, info in kpi_quarterly.items():
        if info.get("estimated"):
            continue
        parts = periodo.split("_")
        if len(parts) < 2 or not parts[1].startswith("Q"):
            continue
        anno = parts[0]
        try:
            q_num = int(parts[1][1:])
        except ValueError:
            continue
        present.setdefault(anno, {})[q_num] = periodo

    if not present:
        return kpi_quarterly

    result      = dict(kpi_quarterly)
    last_anno   = sorted(present.keys())[-1]

    for anno, anno_qs in present.items():
        valid_qs = sorted(
            q for q in anno_qs
            if kpi_quarterly[anno_qs[q]].get("valid")
        )
        if len(valid_qs) < 2:
            continue

        min_q, max_q = min(valid_qs), max(valid_qs)
        xs = np.array(valid_qs, dtype=float)

        # ── Gap interni: Q tra min_q e max_q che non hanno dato reale ──
        interior = [q for q in range(min_q + 1, max_q) if q not in valid_qs]

        # ── Gap futuri: solo per l'anno più recente ──────────────────
        future = (
            [q for q in range(max_q + 1, 5) if q not in valid_qs]
            if anno == last_anno else []
        )

        for q_miss in interior + future:
            periodo_est = f"{anno}_Q{q_miss}"
            if periodo_est in result:          # non sovrascrivere dati reali
                continue

            estimates = {}
            for metric in metrics:
                ys = np.array(
                    [kpi_quarterly[anno_qs[q]].get(metric) or 0.0 for q in valid_qs],
                    dtype=float,
                )
                if q_miss in range(min_q, max_q + 1):
                    # Interpolazione lineare tra i punti reali adiacenti
                    pred = float(np.interp(q_miss, xs, ys))
                else:
                    # Estrapolazione lineare (regressione) oltre l'ultimo reale
                    coeffs = np.polyfit(xs, ys, 1)
                    pred   = float(coeffs[0] * q_miss + coeffs[1])

                lo, hi = clamps[metric]
                estimates[metric] = round(float(max(lo, min(hi, pred))), 2)

            # Tipo di stima: 'interpolated' per i gap interni, 'extrapolated' per i futuri
            est_type = "interpolated" if q_miss <= max_q else "extrapolated"
            result[periodo_est] = {
                "valid":       True,
                "estimated":   True,
                "est_type":    est_type,
                "n_hcp":       0,
                "pen_canali":  [],
                "ric_canali":  [],
                **estimates,
            }

    return result


def _serialize_kpi_periodo(kpi_per_periodo):
    """
    Converte il dict KPI_per_periodo in struttura JSON-serializzabile.
    pen/ric/ing sono DataFrame → records; prop/nps sono dict.
    """
    out = {}
    for anno, info in kpi_per_periodo.items():
        if not info.get("valid"):
            out[str(anno)] = {"valid": False, "message": info.get("message", "")}
            continue

        pen = info.get("Penetrazione")
        ric = info.get("Ricordo")
        ing = info.get("Ingaggio")
        prop = info.get("Propensione")
        nps  = info.get("NPS")

        # Calcola metriche aggregate per il grafico linea
        pen_media  = round(pen["Penetrazione (%)"].mean(), 2) if pen is not None and not pen.empty else None
        ric_media  = round(ric["Ricorda (%)"].mean(), 2)      if ric is not None and not ric.empty else None
        ing_media  = round(ing["Ingaggio (%)"].mean(), 2)     if ing is not None and not ing.empty else None
        prop_media = prop.get("Media propensione") if isinstance(prop, dict) else None
        nps_val    = nps.get("NPS") if isinstance(nps, dict) else None

        # Per canale: penetrazione per anno
        pen_canali = _safe_json(_norm_canale(pen)) if pen is not None and not pen.empty else []
        ric_canali = _safe_json(_norm_canale(ric)) if ric is not None and not ric.empty else []

        out[str(anno)] = {
            "valid": True,
            "n_hcp": len(pen) if pen is not None and not pen.empty else 0,
            "pen_media":  pen_media,
            "ric_media":  ric_media,
            "ing_media":  ing_media,
            "prop_media": prop_media,
            "nps":        nps_val,
            "pen_canali": pen_canali,
            "ric_canali": ric_canali,
        }
    return out


# ──────────────────────────────────────────────────────────────
# ROUTE HTML
# ──────────────────────────────────────────────────────────────

@trend_bp.route("/")
@login_required
def index():
    data   = get_data()
    cols   = data["columns"]
    df_prf = data["df_perf"]

    aziende = current_user.filter_aziende(_get_aziende(df_prf, cols.get("col_azienda")))
    anni    = _get_anni(df_prf)
    specs   = current_user.filter_targets(get_specializzazioni())

    return render_template(
        "trend/index.html",
        active_page="trend",
        aziende=aziende,
        anni=anni,
        specializzazioni=specs,
        n_canali=len(set(CANALI_MAP.values())),
    )


# ──────────────────────────────────────────────────────────────
# API: meta
# ──────────────────────────────────────────────────────────────

@trend_bp.route("/api/meta")
@login_required
def api_meta():
    data   = get_data()
    cols   = data["columns"]
    df_prf = data["df_perf"]
    azienda = request.args.get("azienda", "")

    prodotti = _get_prodotti(df_prf, cols.get("col_prodotto"), azienda, cols.get("col_azienda"))
    return jsonify({
        "aziende":   current_user.filter_aziende(_get_aziende(df_prf, cols.get("col_azienda"))),
        "anni":      _get_anni(df_prf),
        "prodotti":  prodotti,
        "specializzazioni": current_user.filter_targets(get_specializzazioni()),
        "canali":    sorted(set(CANALI_MAP.values())),
    })


# ──────────────────────────────────────────────────────────────
# API: KPI Trend
# ──────────────────────────────────────────────────────────────

@trend_bp.route("/api/kpi", methods=["POST"])
@login_required
def api_kpi():
    body    = request.get_json(silent=True) or {}
    azienda = body.get("azienda", "").strip()
    prodotti = body.get("prodotti", [])    # lista prodotti selezionati (opzionale)
    targets  = body.get("target", [])

    if not azienda:
        return jsonify({"error": "Seleziona un'azienda"}), 400

    data   = get_data()
    cols   = data["columns"]
    df_prf = _filtra(data["df_perf"], cols.get("col_target"), targets)

    anni   = _get_anni(df_prf)
    if not anni:
        return jsonify({"error": "Nessun dato temporale disponibile"}), 400

    col_az   = cols.get("col_azienda")
    col_prod = cols.get("col_prodotto")

    # Il trend_engine si aspetta un df con colonna 'Periodo'
    df_trend = df_prf.copy()
    df_trend["Periodo"] = df_trend[COL_ANNO].astype(str)

    # Check campione minimo per l'azienda selezionata (coerente con Modulo 1 e 2)
    if col_az and col_az in df_trend.columns:
        n_az = int((df_trend[col_az] == azienda).sum())
        if n_az < MIN_HCP:
            return jsonify({
                "insufficient_data": True,
                "n_hcp_az": n_az,
                "azienda":  azienda,
            })

    periodi  = sorted(df_trend["Periodo"].dropna().unique().tolist())

    try:
        result = trend_engine(
            df_perf=df_trend,
            columns={**cols, "col_azienda": col_az},
            azienda_focus=azienda,
            periodi=periodi,
            prodotti=prodotti if prodotti else None,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Serializza
    azienda_data = _serialize_kpi_periodo(result["Azienda"]["KPI_per_periodo"])
    prodotti_data = {
        prod: _serialize_kpi_periodo(res["KPI_per_periodo"])
        for prod, res in result["Prodotti"].items()
    }

    return jsonify({
        "azienda":  azienda,
        "anni":     periodi,
        "kpi":      azienda_data,
        "prodotti": prodotti_data,
    })


# ──────────────────────────────────────────────────────────────
# API: KPI per Quarter (con estrapolazione tendenza)
# ──────────────────────────────────────────────────────────────

@trend_bp.route("/api/kpi_quarter", methods=["POST"])
@login_required
def api_kpi_quarter():
    body     = request.get_json(silent=True) or {}
    azienda  = body.get("azienda", "").strip()
    prodotti = body.get("prodotti", [])
    targets  = body.get("target", [])

    if not azienda:
        return jsonify({"error": "Seleziona un'azienda"}), 400

    data   = get_data()
    cols   = data["columns"]
    df_prf = _filtra(data["df_perf"], cols.get("col_target"), targets)

    # Deriva Quarter da Mese se mancante
    if "Quarter" not in df_prf.columns:
        if "Mese" not in df_prf.columns:
            return jsonify({"error": "Colonna Quarter/Mese non disponibile nel dataset"}), 400
        def _assign_q(m):
            if m in [1, 2, 3]:  return "Q1"
            if m in [4, 5, 6]:  return "Q2"
            if m in [7, 8, 9]:  return "Q3"
            return "Q4"
        df_prf = df_prf.copy()
        df_prf["Quarter"] = df_prf["Mese"].apply(_assign_q)

    col_az = cols.get("col_azienda")

    # Check campione minimo (coerente con /api/kpi)
    if col_az and col_az in df_prf.columns:
        n_az = int((df_prf[col_az] == azienda).sum())
        if n_az < MIN_HCP:
            return jsonify({
                "insufficient_data": True,
                "n_hcp_az": n_az,
                "azienda": azienda,
            })

    # Crea Periodo = "2024_Q1", "2024_Q2" ecc.
    df_trend = df_prf.copy()
    df_trend["Periodo"] = (
        df_trend[COL_ANNO].astype(str) + "_" +
        df_trend["Quarter"].astype(str)
    )

    periodi = sorted(df_trend["Periodo"].dropna().unique().tolist())

    try:
        result = trend_engine(
            df_perf=df_trend,
            columns={**cols, "col_azienda": col_az},
            azienda_focus=azienda,
            periodi=periodi,
            prodotti=prodotti if prodotti else None,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Serializza KPI + estrapolazione quarter mancanti
    azienda_kpi = _serialize_kpi_periodo(result["Azienda"]["KPI_per_periodo"])
    azienda_kpi = _extrapolate_missing_quarters(azienda_kpi)

    prodotti_data = {}
    for prod, res in result["Prodotti"].items():
        prod_kpi = _serialize_kpi_periodo(res["KPI_per_periodo"])
        prod_kpi = _extrapolate_missing_quarters(prod_kpi)
        prodotti_data[prod] = prod_kpi

    all_periodi = sorted(azienda_kpi.keys())

    return jsonify({
        "azienda":  azienda,
        "periodi":  all_periodi,
        "kpi":      azienda_kpi,
        "prodotti": prodotti_data,
    })


# ──────────────────────────────────────────────────────────────
# EXPORT Excel (GET con query params)
# ──────────────────────────────────────────────────────────────

@trend_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_excel():
    if request.method == "GET":
        azienda  = request.args.get("azienda", "")
        prodotti = request.args.getlist("prodotti")
        targets  = request.args.getlist("target")
    else:
        body     = request.get_json(silent=True) or {}
        azienda  = body.get("azienda", "").strip()
        prodotti = body.get("prodotti", [])
        targets  = body.get("target", [])

    if not azienda:
        return jsonify({"error": "Seleziona un'azienda"}), 400

    data   = get_data()
    cols   = data["columns"]
    df_prf = _filtra(data["df_perf"], cols.get("col_target"), targets)

    df_trend = df_prf.copy()
    df_trend["Periodo"] = df_trend[COL_ANNO].astype(str)
    periodi  = sorted(df_trend["Periodo"].dropna().unique().tolist())

    try:
        result = trend_engine(
            df_perf=df_trend,
            columns=cols,
            azienda_focus=azienda,
            periodi=periodi,
            prodotti=prodotti if prodotti else None,
        )
        buf = export_trend_xlsx(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    label    = f"{azienda}_Trend"
    filename = f"MCM_Trend_{label}.xlsx".replace(" ", "_")
    return send_file(
        buf, as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
