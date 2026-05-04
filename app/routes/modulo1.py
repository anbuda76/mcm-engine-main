"""
app/routes/modulo1.py
─────────────────────
Blueprint Modulo 1 — Comportamento HCP

Route HTML:
  GET  /modulo1/              → pagina principale (4 tab)

Route API JSON:
  GET  /modulo1/api/meta      → specializzazioni disponibili
  POST /modulo1/api/kpi       → tutti i KPI (body: {target: [...]})
  POST /modulo1/api/mappa     → dati scatter mappa canali
  POST /modulo1/api/ocv       → OCV delta + lift + mix engine

Route file:
  POST /modulo1/export        → download Excel multi-sheet
"""

import sys, os, io, json
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user

# ── path per src/ ────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import re
from app.data_cache import get_data, get_specializzazioni, get_aree_terapeutiche
from src.behavior.mappe.mappa_patologie import AREE_CANONICHE

from src.behavior.kpi_penetrazione      import kpi_penetrazione
from src.behavior.kpi_utilita           import kpi_utilita
from src.behavior.kpi_utilita_fasce     import kpi_utilita_fasce
from src.behavior.kpi_ricordo           import kpi_ricordo_canali
from src.behavior.kpi_ingaggio          import kpi_ingaggio_canali
from src.behavior.kpi_propensione       import kpi_propensione_canali
from src.behavior.kpi_nps_canali        import kpi_nps_canali
from src.behavior.kpi_q2_distribuzione  import kpi_q2_distribuzione
from src.behavior.kpi_ocv_mix           import ocv_delta, ocv_lift_curve, ocv_mix_engine
from src.behavior.mappe.mappa_canali    import crea_mappa_canali
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP

modulo1_bp = Blueprint("modulo1", __name__)

# Soglia minima di HCP per considerare il campione analizzabile
MIN_HCP = 20


# ──────────────────────────────────────────────────────────────
# Helper: filtra df per target selezionato
# ──────────────────────────────────────────────────────────────
def _filtra(df, col_target, targets):
    if not targets or not col_target or col_target not in df.columns:
        return df
    return df[df[col_target].isin(targets)].copy()


def _filtra_q7(df_beh, df_perf, aree: list, patologie: list):
    """
    Filtra df_beh per Area Terapeutica (Q7a) e/o Patologia (Q7b_1/2/3).
    Propaga il filtro su df_perf via Respondent ID.
    Restituisce (df_beh_filtrato, df_perf_filtrato).
    """
    from src.behavior.mappe.mappa_patologie import normalizza_q7a, normalizza_q7b

    if not aree and not patologie:
        return df_beh, df_perf

    q7a_col  = next((c for c in df_beh.columns if c.startswith("Q7a")), None)
    q7b_cols = [c for c in df_beh.columns if re.match(r"Q7b_\d+", c)]

    mask = pd.Series(True, index=df_beh.index)

    # ── Filtro Area Terapeutica ──────────────────────────────
    if aree and q7a_col:
        aree_set = set(aree)
        norm_area = df_beh[q7a_col].apply(normalizza_q7a)
        mask &= norm_area.isin(aree_set)

    # ── Filtro Patologie (almeno una Q7b match) ──────────────
    if patologie and q7b_cols:
        pat_set  = set(patologie)
        pat_mask = pd.Series(False, index=df_beh.index)
        for col in q7b_cols:
            pat_mask |= df_beh[col].apply(normalizza_q7b).isin(pat_set)
        mask &= pat_mask

    df_beh_f = df_beh[mask].copy()

    # ── Propaga su df_perf via Respondent ────────────────────
    df_perf_f = df_perf
    if "Respondent" in df_beh_f.columns and "Respondent" in df_perf.columns:
        resp_ids  = set(df_beh_f["Respondent"])
        df_perf_f = df_perf[df_perf["Respondent"].isin(resp_ids)].copy()

    return df_beh_f, df_perf_f


def _safe_json(df):
    """Converte DataFrame in lista di dict JSON-safe (NaN → None)."""
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _normalizza_df(df):
    """
    Aggiunge colonna 'Canale_std' a qualsiasi DataFrame che ha 'Canale',
    usando CANALI_MAP come fonte di verità unica per tutti i moduli.
    Se Canale_std già esiste (es. kpi_penetrazione la calcola già), non la sovrascrive.
    Poi rinomina 'Canale' con il valore normalizzato per uniformità totale nei grafici.
    """
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    if "Canale_std" not in df.columns:
        df["Canale_std"] = df["Canale"].map(CANALI_MAP)
    # Usa Canale_std come label principale (se disponibile), altrimenti raw
    df["Canale"] = df["Canale_std"].fillna(df["Canale"])
    return df


# ──────────────────────────────────────────────────────────────
# ROUTE HTML
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/")
@login_required
def index():
    specs = current_user.filter_targets(get_specializzazioni())
    return render_template(
        "modulo1/index.html",
        active_page="modulo1",
        specializzazioni=specs,
        aree_terapeutiche=AREE_CANONICHE,   # sempre tutte e 13, ordine ATC fisso
        n_canali=len(set(CANALI_MAP.values())),
    )


# ──────────────────────────────────────────────────────────────
# API: meta
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/api/meta")
@login_required
def api_meta():
    specs = current_user.filter_targets(get_specializzazioni())
    return jsonify({
        "specializzazioni": specs,
        "n_canali": len(set(CANALI_MAP.values())),
        "canali":   sorted(set(CANALI_MAP.values())),
    })


# ──────────────────────────────────────────────────────────────
# API: Aree Terapeutiche + Patologie (per il filtro gerarchico)
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/api/aree")
@login_required
def api_aree():
    """
    GET /modulo1/api/aree
    Ritorna struttura gerarchica { area: [patologie...] }
    Opzionale: ?area=X → solo le patologie dell'area X
    """
    area_filter = request.args.get("area", "").strip()
    aree_dict   = get_aree_terapeutiche()

    if area_filter:
        return jsonify({
            "patologie": sorted(aree_dict.get(area_filter, []))
        })

    return jsonify({
        "aree":   list(aree_dict.keys()),
        "gerarchia": aree_dict,
    })


# ──────────────────────────────────────────────────────────────
# API: KPI principali
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/api/kpi", methods=["POST"])
@login_required
def api_kpi():
    body       = request.get_json(silent=True) or {}
    targets    = body.get("target", [])
    aree       = body.get("area_terapeutica", [])
    patologie  = body.get("patologie", [])

    data    = get_data()
    col_tgt = data["columns"].get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)
    df_beh, df_perf = _filtra_q7(df_beh, df_perf, aree, patologie)
    cols    = data["columns"]

    # ── Campione minimo: avvisa il frontend senza calcolare i KPI ──
    n_beh  = int(len(df_beh))
    n_perf = int(len(df_perf))
    if n_beh < MIN_HCP or n_perf < MIN_HCP:
        return jsonify({
            "insufficient_data": True,
            "n_hcp":  n_beh,
            "n_perf": n_perf,
        })

    try:
        # KPI su df_beh (Comportamento HCP)
        df_pen   = kpi_penetrazione(df_beh, cols["canali_11"])
        df_util  = kpi_utilita(df_beh, cols["canali_utilita"])
        df_fasce = kpi_utilita_fasce(df_beh, cols["canali_utilita"])
        df_q2    = kpi_q2_distribuzione(df_beh, cols["q2_cols"])
        # KPI su df_perf (Performance Channel)
        df_ric   = kpi_ricordo_canali(df_perf, cols["canali_perf"])
        df_ing   = kpi_ingaggio_canali(df_perf, cols["canali_perf"])
        df_prop  = kpi_propensione_canali(df_perf, cols["canali_perf"])
        df_nps   = kpi_nps_canali(df_perf, cols["canali_perf"], cols["col_prop"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # ── Normalizza label canali via CANALI_MAP (fonte unica per tutti i moduli) ──
    df_pen   = _normalizza_df(df_pen)
    df_util  = _normalizza_df(df_util)
    df_fasce = _normalizza_df(df_fasce)
    df_ric   = _normalizza_df(df_ric)
    df_ing   = _normalizza_df(df_ing)
    df_prop  = _normalizza_df(df_prop)
    df_nps   = _normalizza_df(df_nps)

    return jsonify({
        "n_hcp":         int(len(df_beh)),
        "penetrazione":  _safe_json(df_pen),
        "utilita":       _safe_json(df_util),
        "utilita_fasce": _safe_json(df_fasce),
        "ricordo":       _safe_json(df_ric),
        "ingaggio":      _safe_json(df_ing),
        "propensione":   _safe_json(df_prop),
        "nps":           _safe_json(df_nps),
        "q2":            _safe_json(df_q2),
        "media_ingaggio": round(float(df_ing.attrs.get("media_ingaggio", 0)), 1),
    })


# ──────────────────────────────────────────────────────────────
# API: Mappa canali (scatter)
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/api/mappa", methods=["POST"])
@login_required
def api_mappa():
    body      = request.get_json(silent=True) or {}
    targets   = body.get("target", [])
    aree      = body.get("area_terapeutica", [])
    patologie = body.get("patologie", [])

    data    = get_data()
    col_tgt = data["columns"].get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)
    df_beh, df_perf = _filtra_q7(df_beh, df_perf, aree, patologie)
    cols    = data["columns"]

    try:
        # Passiamo i DF originali (con Canale raw) a crea_mappa_canali
        # che gestisce internamente la normalizzazione via Canale_std
        df_pen  = kpi_penetrazione(df_beh, cols["canali_11"])
        df_util = kpi_utilita(df_beh, cols["canali_utilita"])
        df_ing  = kpi_ingaggio_canali(df_perf, cols["canali_perf"])
        df_prop = kpi_propensione_canali(df_perf, cols["canali_perf"])
        df_mappa = crea_mappa_canali(df_pen, df_util, df_ing, df_prop)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"mappa": _safe_json(df_mappa)})


# ──────────────────────────────────────────────────────────────
# Helper: normalizza le label dei canali nel Channel Mix string
# ──────────────────────────────────────────────────────────────
def _normalizza_mix_str(mix_str: str) -> str:
    """Converte 'Q9_1 Opuscoli + Q9_17 Webinar' → 'Opuscoli via posta + Webinar'."""
    parts = str(mix_str).split(" + ")
    return " + ".join(CANALI_MAP.get(p.strip(), p.strip()) for p in parts)


# ──────────────────────────────────────────────────────────────
# API: OCV (delta + mix engine)
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/api/ocv", methods=["POST"])
@login_required
def api_ocv():
    body      = request.get_json(silent=True) or {}
    targets   = body.get("target", [])
    aree      = body.get("area_terapeutica", [])
    patologie = body.get("patologie", [])

    data    = get_data()
    col_tgt = data["columns"].get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)
    _,      df_perf = _filtra_q7(df_beh, df_perf, aree, patologie)
    cols    = data["columns"]

    channel_cols = cols.get("canali_perf", [])
    recall_col   = cols.get("col_ricordo")

    if not channel_cols or not recall_col:
        return jsonify({"error": "Colonne OCV non trovate"}), 400

    try:
        delta  = ocv_delta(df_perf, channel_cols, recall_col)
        df_mix = ocv_mix_engine(df_perf, channel_cols, recall_col)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Normalizza le label dei canali nel Channel Mix (Q9_xx → nomi leggibili)
    if not df_mix.empty:
        df_mix["Channel Mix"] = df_mix["Channel Mix"].apply(_normalizza_mix_str)

    # Totale HCP nell'analisi (base per calcolo Recall Assoluto del Mix)
    n_hcp_total = int(len(df_perf))

    # Aggiungi Recall Assoluto: penetrazione_mix × recall_mix / 100
    # = (N HCP esposti al mix / totale HCP) × Recall Mix%
    if not df_mix.empty and n_hcp_total > 0:
        df_mix["Recall Assoluto (%)"] = (
            df_mix["N HCP"] / n_hcp_total * df_mix["Recall Mix (%)"]
        ).round(1)
    elif not df_mix.empty:
        df_mix["Recall Assoluto (%)"] = 0.0

    # Top 10 per OCV % (già ordinato desc dall'engine)
    top10_ocv = df_mix.head(10) if not df_mix.empty else df_mix

    # Top 10 per Frequenza (N HCP più esposti)
    top10_freq = (
        df_mix.sort_values("N HCP", ascending=False).head(10)
        if not df_mix.empty else df_mix
    )

    # Top 10 per Impatto Reale (Recall Assoluto% desc) — base universo totale HCP
    top10_impatto = (
        df_mix.sort_values("Recall Assoluto (%)", ascending=False).head(10)
        if not df_mix.empty else df_mix
    )

    best = {}
    best_impatto = {}
    if not df_mix.empty:
        row = df_mix.iloc[0]
        best = {
            "mix":    str(row.get("Channel Mix", "")),
            "ocv":    round(float(row.get("OCV (%)", 0)), 1),
            "recall": round(float(row.get("Recall Mix (%)", 0)), 1),
            "action": str(row.get("Business Action", "")),
        }
        row_i = df_mix.sort_values("Recall Assoluto (%)", ascending=False).iloc[0]
        best_impatto = {
            "mix":           str(row_i.get("Channel Mix", "")),
            "recall_ass":    round(float(row_i.get("Recall Assoluto (%)", 0)), 1),
            "recall":        round(float(row_i.get("Recall Mix (%)", 0)), 1),
            "pen_mix":       round(float(row_i.get("N HCP", 0)) / n_hcp_total * 100, 1)
                             if n_hcp_total > 0 else 0,
            "n_hcp":         int(row_i.get("N HCP", 0)),
            "action":        str(row_i.get("Business Action", "")),
        }

    return jsonify({
        "delta":          delta,
        "mix":            _safe_json(top10_ocv),
        "top10_freq":     _safe_json(top10_freq),
        "top10_impatto":  _safe_json(top10_impatto),
        "best":           best,
        "best_impatto":   best_impatto,
        "n_hcp_total":    n_hcp_total,
    })


# ──────────────────────────────────────────────────────────────
# EXPORT PDF report (GET con ?target=A&target=B)
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/export/pdf", methods=["GET", "POST"])
@login_required
def export_pdf():
    """
    Genera e scarica il report PDF Comportamento HCP (4 pagine, dark theme).
    Supporta GET (?target=X&target=Y&area=X&patologia=X) e POST (JSON body).
    """
    if request.method == "GET":
        targets   = request.args.getlist("target")
        aree      = request.args.getlist("area")
        patologie = request.args.getlist("patologia")
    else:
        body      = request.get_json(silent=True) or {}
        targets   = body.get("target", [])
        aree      = body.get("area_terapeutica", [])
        patologie = body.get("patologie", [])

    try:
        from app.reports.report_comportamento import genera_report
        buf = genera_report(targets, aree=aree, patologie=patologie)
    except Exception as e:
        return jsonify({"error": f"Errore generazione PDF: {e}"}), 500

    # Costruisce filename che riflette i filtri attivi
    parts = []
    if targets:
        parts.append("_".join(targets)[:40])
    if aree:
        parts.append("_".join(a.replace(" ", "-") for a in aree)[:30])
    if patologie:
        parts.append(f"{len(patologie)}pat")
    label    = "_".join(parts) if parts else "tutti"
    filename = f"MCM_Report_Comportamento_{label}.pdf"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# ──────────────────────────────────────────────────────────────
# EXPORT Excel multi-sheet  (GET con ?target=A&target=B)
# ──────────────────────────────────────────────────────────────
@modulo1_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_excel():
    # Supporta sia GET (?target=X&target=Y) sia POST (JSON body)
    if request.method == "GET":
        targets = request.args.getlist("target")
    else:
        body    = request.get_json(silent=True) or {}
        targets = body.get("target", [])

    data    = get_data()
    col_tgt = data["columns"].get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)
    cols    = data["columns"]

    try:
        df_pen   = kpi_penetrazione(df_beh, cols["canali_11"])
        df_util  = kpi_utilita(df_beh, cols["canali_utilita"])
        df_fasce = kpi_utilita_fasce(df_beh, cols["canali_utilita"])
        df_q2    = kpi_q2_distribuzione(df_beh, cols["q2_cols"])
        df_ric   = kpi_ricordo_canali(df_perf, cols["canali_perf"])
        df_ing   = kpi_ingaggio_canali(df_perf, cols["canali_perf"])
        df_prop  = kpi_propensione_canali(df_perf, cols["canali_perf"])
        df_nps   = kpi_nps_canali(df_perf, cols["canali_perf"], cols["col_prop"])
        df_mix   = ocv_mix_engine(df_perf, cols["canali_perf"], cols["col_ricordo"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Normalizza label per l'Excel — nomi uniformi in tutti i sheet
    def _clean(df):
        df = _normalizza_df(df)
        return df.drop(columns=["Canale_std"], errors="ignore")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        _clean(df_pen).to_excel(writer,   sheet_name="Penetrazione",     index=False)
        _clean(df_util).to_excel(writer,  sheet_name="Utilita",          index=False)
        _clean(df_fasce).to_excel(writer, sheet_name="Utilita Fasce",    index=False)
        df_q2.to_excel(writer,            sheet_name="Q2 Distribuzione", index=False)
        _clean(df_ric).to_excel(writer,   sheet_name="Ricordo",          index=False)
        _clean(df_ing).to_excel(writer,   sheet_name="Ingaggio",         index=False)
        _clean(df_prop).to_excel(writer,  sheet_name="Propensione",      index=False)
        _clean(df_nps).to_excel(writer,   sheet_name="NPS",              index=False)
        df_mix.to_excel(writer,           sheet_name="OCV Mix",          index=False)
    buf.seek(0)

    label    = "_".join(targets) if targets else "tutti"
    filename = f"MCM_Comportamento_{label}.xlsx"
    return send_file(
        buf, as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
