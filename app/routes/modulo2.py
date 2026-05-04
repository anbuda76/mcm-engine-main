"""
app/routes/modulo2.py
─────────────────────
Blueprint Modulo 2 — Performance vs Mercato

Route HTML:
  GET  /modulo2/              → pagina principale (3 tab)

Route API JSON:
  GET  /modulo2/api/meta      → aziende + specializzazioni disponibili
  POST /modulo2/api/kpi       → KPI azienda + competitor + mercato
  POST /modulo2/api/compare   → tabellone comparativo aggregato
  POST /modulo2/api/canali    → KPI avanzati per canale (enhanced)

Route file:
  GET  /modulo2/export        → download Excel multi-sheet
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

from src.performance.kpi_penetrazione_azienda    import kpi_penetrazione_azienda
from src.performance.kpi_ricordo_azienda         import kpi_ricordo_azienda
from src.performance.kpi_ingaggio_azienda        import kpi_ingaggio_azienda
from src.performance.kpi_propensione_azienda     import kpi_propensione_azienda
from src.performance.kpi_nps_azienda             import kpi_nps_azienda

from src.performance.kpi_penetrazione_competitor import kpi_penetrazione_competitor
from src.performance.kpi_ricordo_competitor      import kpi_ricordo_competitor
from src.performance.kpi_ingaggio_competitor     import kpi_ingaggio_competitor
from src.performance.kpi_propensione_competitor  import kpi_propensione_competitor
from src.performance.kpi_nps_competitor          import kpi_nps_competitor

from src.performance.mercato.kpi_penetration_mercato import kpi_penetration_mercato
from src.performance.mercato.kpi_ricordo_mercato     import kpi_ricordo_mercato
from src.performance.mercato.kpi_ingaggio_mercato    import kpi_ingaggio_mercato
from src.performance.mercato.kpi_propensione_mercato import kpi_propensione_mercato
from src.performance.mercato.kpi_nps_mercato         import kpi_nps_mercato

from src.performance.compare.compare_all_kpi           import compare_all_kpi
from src.performance.compare.compare_channels_enhanced  import compare_channels_enhanced
from src.performance.market_definition.define_market    import define_market

modulo2_bp = Blueprint("modulo2", __name__)
MAX_COMPETITOR = 10
MIN_HCP = 20   # Soglia minima HCP azienda per analisi significativa
MAX_COMPETITOR_VS = 5  # Max competitor per la vista Focus vs Competitor

# Canali fissi per la vista Focus vs Competitor (label normalizzate via CANALI_MAP)
TARGET_CANALI_VS = [
    "ISF Faccia a Faccia",
    "ISF Webcall",
    "Email da ISF",
    "E-mail Aziendali",
]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _filtra(df, col_target, targets):
    if not targets or not col_target or col_target not in df.columns:
        return df
    return df[df[col_target].isin(targets)].copy()


def _filtra_az(df, col_az, azienda):
    if not azienda or not col_az or col_az not in df.columns:
        return df
    return df[df[col_az] == azienda].copy()


def _safe_json(obj):
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="records", force_ascii=False))
    if isinstance(obj, dict):
        # NaN → None per JSON
        return {k: (None if (isinstance(v, float) and v != v) else v)
                for k, v in obj.items()}
    return obj


def _norm_canale(df):
    """Applica CANALI_MAP alla colonna Canale — fonte di verità unica."""
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _get_aziende(df_perf, col_az):
    if not col_az or col_az not in df_perf.columns:
        return []
    return df_perf[col_az].value_counts().index.tolist()


def _dict_to_df(d):
    """Converte dict KPI (propensione/nps azienda) in DataFrame 1 riga."""
    if isinstance(d, dict):
        return pd.DataFrame([d])
    return d if isinstance(d, pd.DataFrame) else pd.DataFrame()


# ──────────────────────────────────────────────────────────────
# Calcola tutti i KPI in un colpo (riusato da api_kpi e export)
# ──────────────────────────────────────────────────────────────
def _add_ingaggio_totale(df):
    """
    compare_all_kpi cerca 'Ingaggio totale (%)' ma kpi_ingaggio_* produce 'Ingaggio (%)'.
    Aggiunge la colonna alias mantenendo quella originale.
    Applicato DOPO _norm_canale, PRIMA di passare a compare_all_kpi.
    """
    if df is None or df.empty:
        return df
    if "Ingaggio (%)" in df.columns and "Ingaggio totale (%)" not in df.columns:
        df = df.copy()
        df["Ingaggio totale (%)"] = df["Ingaggio (%)"]
    return df


def _calc_all(df_perf_filt, df_az, df_market, competitors, cols):
    canali_perf  = cols.get("canali_perf", [])
    col_ricordo  = cols.get("col_ricordo")
    col_ingaggio = cols.get("col_ingaggio")
    col_prop     = cols.get("col_prop")

    # ── Azienda (raw) — per compare_channels_enhanced che usa colonne raw ──
    pen_az_raw  = kpi_penetrazione_azienda(df_az, canali_perf)
    ric_az_raw  = kpi_ricordo_azienda(df_az, col_ricordo, canali_perf)
    ing_az_raw  = kpi_ingaggio_azienda(df_az, col_ingaggio, canali_perf)

    # ── Normalizzati per KPI pubblici + compare_all_kpi ──
    pen_az  = _norm_canale(pen_az_raw)
    ric_az  = _norm_canale(ric_az_raw)
    ing_az  = _add_ingaggio_totale(_norm_canale(ing_az_raw))
    prop_az = kpi_propensione_azienda(df_az, col_prop)
    nps_az  = kpi_nps_azienda(df_az, col_prop)

    # ── Competitor ──
    if competitors:
        pen_comp_raw  = kpi_penetrazione_competitor(df_perf_filt, competitors, canali_perf)
        ric_comp_raw  = kpi_ricordo_competitor(df_perf_filt, competitors, col_ricordo, canali_perf)
        ing_comp_raw  = kpi_ingaggio_competitor(df_perf_filt, competitors, col_ingaggio, canali_perf)

        pen_comp  = _norm_canale(pen_comp_raw)
        ric_comp  = _norm_canale(ric_comp_raw)
        ing_comp  = _add_ingaggio_totale(_norm_canale(ing_comp_raw))
        prop_comp = kpi_propensione_competitor(df_perf_filt, competitors, col_prop)
        nps_comp  = kpi_nps_competitor(df_perf_filt, competitors, col_prop)
    else:
        pen_comp_raw = ric_comp_raw = ing_comp_raw = pd.DataFrame()
        pen_comp = ric_comp = ing_comp = prop_comp = nps_comp = pd.DataFrame()

    # ── Mercato ──
    pen_merc_raw  = kpi_penetration_mercato(df_market, canali_perf)
    ric_merc_raw  = kpi_ricordo_mercato(df_market, col_ricordo, canali_perf)
    ing_merc_raw  = kpi_ingaggio_mercato(df_market, col_ingaggio, canali_perf)

    pen_merc  = _norm_canale(pen_merc_raw)
    ric_merc  = _norm_canale(ric_merc_raw)
    ing_merc  = _add_ingaggio_totale(_norm_canale(ing_merc_raw))
    prop_merc = kpi_propensione_mercato(df_market, col_prop)
    nps_merc  = kpi_nps_mercato(df_market, col_prop)

    return dict(
        # Normalizzati (per KPI pubblici + compare_all_kpi)
        pen_az=pen_az,   ric_az=ric_az,   ing_az=ing_az,   prop_az=prop_az,   nps_az=nps_az,
        pen_comp=pen_comp, ric_comp=ric_comp, ing_comp=ing_comp, prop_comp=prop_comp, nps_comp=nps_comp,
        pen_merc=pen_merc, ric_merc=ric_merc, ing_merc=ing_merc, prop_merc=prop_merc, nps_merc=nps_merc,
        # Raw (per compare_channels_enhanced che accede a colonne raw del df)
        pen_az_raw=pen_az_raw, ric_az_raw=ric_az_raw, ing_az_raw=ing_az_raw,
        pen_comp_raw=pen_comp_raw, ric_comp_raw=ric_comp_raw, ing_comp_raw=ing_comp_raw,
        pen_merc_raw=pen_merc_raw, ric_merc_raw=ric_merc_raw, ing_merc_raw=ing_merc_raw,
        canali_perf=canali_perf, col_prop=col_prop,
    )


def _prepare_dfs(body):
    """Estrae e filtra i DataFrame dai parametri della richiesta."""
    targets     = body.get("target", [])
    azienda     = body.get("azienda", "").strip()
    competitors = body.get("competitors", [])[:MAX_COMPETITOR]

    data    = get_data()
    cols    = data["columns"]
    col_tgt = cols.get("col_target")
    col_az  = cols.get("col_azienda")

    df_perf = _filtra(data["df_perf"], col_tgt, targets)

    if not azienda:
        raise ValueError("Seleziona un'azienda focus")

    df_az = _filtra_az(df_perf, col_az, azienda)
    if df_az.empty:
        raise ValueError(f"Nessun dato per: {azienda}")

    market_list = define_market(df_perf, azienda, competitors)
    df_market   = df_perf[df_perf[col_az].isin(market_list)].copy() if col_az else df_perf

    return df_perf, df_az, df_market, azienda, competitors, cols


# ──────────────────────────────────────────────────────────────
# ROUTE HTML
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/")
@login_required
def index():
    data    = get_data()
    cols    = data["columns"]
    aziende = current_user.filter_aziende(_get_aziende(data["df_perf"], cols.get("col_azienda")))
    specs   = current_user.filter_targets(get_specializzazioni())
    return render_template(
        "modulo2/index.html",
        active_page="modulo2",
        aziende=aziende,
        specializzazioni=specs,
        max_competitor=MAX_COMPETITOR,
        n_canali=len(set(CANALI_MAP.values())),
    )


# ──────────────────────────────────────────────────────────────
# API: meta
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/api/meta")
@login_required
def api_meta():
    data   = get_data()
    col_az = data["columns"].get("col_azienda")
    return jsonify({
        "aziende":          current_user.filter_aziende(_get_aziende(data["df_perf"], col_az)),
        "specializzazioni": current_user.filter_targets(get_specializzazioni()),
        "max_competitor":   MAX_COMPETITOR,
        "canali":           sorted(set(CANALI_MAP.values())),
    })


# ──────────────────────────────────────────────────────────────
# API: KPI completi (azienda + competitor + mercato)
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/api/kpi", methods=["POST"])
@login_required
def api_kpi():
    body = request.get_json(silent=True) or {}
    try:
        df_perf, df_az, df_market, azienda, competitors, cols = _prepare_dfs(body)

        # ── Campione minimo: avvisa il frontend senza calcolare i KPI ──
        n_az = int(len(df_az))
        if n_az < MIN_HCP:
            return jsonify({
                "insufficient_data": True,
                "n_hcp_az": n_az,
                "azienda":  azienda,
            })

        k = _calc_all(df_perf, df_az, df_market, competitors, cols)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "azienda":     azienda,
        "competitors": competitors,
        "n_hcp_az":    int(len(df_az)),
        "n_hcp_merc":  int(len(df_market)),
        # Azienda
        "pen_az":   _safe_json(k["pen_az"]),
        "ric_az":   _safe_json(k["ric_az"]),
        "ing_az":   _safe_json(k["ing_az"]),
        "prop_az":  _safe_json(k["prop_az"]),
        "nps_az":   _safe_json(k["nps_az"]),
        # Competitor
        "pen_comp":  _safe_json(k["pen_comp"]),
        "ric_comp":  _safe_json(k["ric_comp"]),
        "ing_comp":  _safe_json(k["ing_comp"]),
        "nps_comp":  _safe_json(k["nps_comp"]),
        # Mercato
        "pen_merc":  _safe_json(k["pen_merc"]),
        "ric_merc":  _safe_json(k["ric_merc"]),
        "ing_merc":  _safe_json(k["ing_merc"]),
        "prop_merc": _safe_json(k["prop_merc"]),
        "nps_merc":  _safe_json(k["nps_merc"]),
    })


# ──────────────────────────────────────────────────────────────
# API: Tabellone comparativo (5 KPI × 3 soggetti)
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/api/compare", methods=["POST"])
@login_required
def api_compare():
    body = request.get_json(silent=True) or {}
    try:
        df_perf, df_az, df_market, azienda, competitors, cols = _prepare_dfs(body)
        k = _calc_all(df_perf, df_az, df_market, competitors, cols)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    try:
        # compare_all_kpi.safe_value() si aspetta DataFrame, ma prop/nps azienda/mercato
        # sono dict — convertiamo con _dict_to_df() senza toccare src/.
        df_tab = compare_all_kpi(
            k["pen_az"],  k["ric_az"],  k["ing_az"],
            _dict_to_df(k["prop_az"]),  _dict_to_df(k["nps_az"]),
            k["pen_comp"],k["ric_comp"],k["ing_comp"],
            k["prop_comp"],  k["nps_comp"],
            k["pen_merc"],k["ric_merc"],k["ing_merc"],
            _dict_to_df(k["prop_merc"]), _dict_to_df(k["nps_merc"]),
        )
    except Exception as e:
        return jsonify({"error": "compare_all_kpi: " + str(e)}), 500

    return jsonify({"tabellone": _safe_json(df_tab)})


# ──────────────────────────────────────────────────────────────
# API: KPI per canale enhanced (NPS/Prop per esposti)
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/api/canali", methods=["POST"])
@login_required
def api_canali():
    body = request.get_json(silent=True) or {}
    try:
        df_perf, df_az, df_market, azienda, competitors, cols = _prepare_dfs(body)
        k = _calc_all(df_perf, df_az, df_market, competitors, cols)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    try:
        # compare_channels_enhanced accede internamente a df_focus[canale].notna()
        # dove 'canale' è il nome RAW della colonna (Q9_x) — quindi passare df RAW.
        # Normalizziamo il risultato finale con _norm_canale().
        df_enhanced = compare_channels_enhanced(
            k["pen_az_raw"],   k["ric_az_raw"],   k["ing_az_raw"],   pd.DataFrame(),
            k["pen_comp_raw"], k["ric_comp_raw"],  k["ing_comp_raw"], pd.DataFrame(),
            k["pen_merc_raw"], k["ric_merc_raw"],  k["ing_merc_raw"], pd.DataFrame(),
            df_focus=df_az,
            df_perf_filt=df_perf,
            df_market=df_market,
            competitor_list=competitors,
            canali_perf=k["canali_perf"],
            col_prop=k["col_prop"],
        )
        df_enhanced = _norm_canale(df_enhanced)
    except Exception as e:
        return jsonify({"error": "compare_channels_enhanced: " + str(e)}), 500

    return jsonify({"canali": _safe_json(df_enhanced)})


# ──────────────────────────────────────────────────────────────
# API: Focus vs singoli Competitor — 4 canali chiave
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/api/vs_competitor", methods=["POST"])
@login_required
def api_vs_competitor():
    """
    Restituisce Penetrazione / Ricordo / Ingaggio per ciascun competitor
    individualmente (non aggregato) su 4 canali chiave: ISF Faccia a Faccia,
    ISF Webcall, Email da ISF, E-mail Aziendali.
    Competitor cappato a MAX_COMPETITOR_VS = 5.
    """
    body = request.get_json(silent=True) or {}
    # cap competitors a 5
    body_vs = dict(body)
    body_vs["competitors"] = body.get("competitors", [])[:MAX_COMPETITOR_VS]

    try:
        df_perf, df_az, df_market, azienda, competitors, cols = _prepare_dfs(body_vs)
        k = _calc_all(df_perf, df_az, df_market, competitors, cols)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Normalizza etichette canali (raw → leggibili)
    pen_az_n   = _norm_canale(k["pen_az_raw"])
    ric_az_n   = _norm_canale(k["ric_az_raw"])
    ing_az_n   = _norm_canale(k["ing_az_raw"])
    pen_comp_n = _norm_canale(k["pen_comp_raw"]) if not k["pen_comp_raw"].empty else pd.DataFrame()
    ric_comp_n = _norm_canale(k["ric_comp_raw"]) if not k["ric_comp_raw"].empty else pd.DataFrame()
    ing_comp_n = _norm_canale(k["ing_comp_raw"]) if not k["ing_comp_raw"].empty else pd.DataFrame()

    def _vf(df, col, canale):
        """Lookup valore KPI per canale (focus — no colonna Azienda)."""
        if df is None or df.empty or "Canale" not in df.columns:
            return None
        sub = df[df["Canale"] == canale]
        if sub.empty or col not in sub.columns:
            return None
        v = sub[col].iloc[0]
        return None if pd.isna(v) else round(float(v), 1)

    def _vc(df, col, canale, comp):
        """Lookup valore KPI per canale + competitor."""
        if df is None or df.empty or "Canale" not in df.columns:
            return None
        sub = df[(df["Canale"] == canale) & (df["Azienda"] == comp)]
        if sub.empty or col not in sub.columns:
            return None
        v = sub[col].iloc[0]
        return None if pd.isna(v) else round(float(v), 1)

    def _nhcp_focus(canale):
        if pen_az_n is None or pen_az_n.empty:
            return None
        sub = pen_az_n[pen_az_n["Canale"] == canale]
        if sub.empty or "Medici raggiunti" not in sub.columns:
            return None
        return int(sub["Medici raggiunti"].iloc[0])

    def _nhcp_comp(canale, comp):
        if pen_comp_n is None or pen_comp_n.empty:
            return None
        sub = pen_comp_n[(pen_comp_n["Canale"] == canale) & (pen_comp_n["Azienda"] == comp)]
        if sub.empty or "Medici raggiunti" not in sub.columns:
            return None
        return int(sub["Medici raggiunti"].iloc[0])

    data = {}
    for canale in TARGET_CANALI_VS:
        entry = {}
        # Azienda focus
        entry[azienda] = {
            "pen":      _vf(pen_az_n, "Penetrazione (%)", canale),
            "ric":      _vf(ric_az_n, "Ricorda (%)",      canale),
            "ing":      _vf(ing_az_n, "Ingaggio (%)",     canale),
            "n_hcp":    _nhcp_focus(canale),
            "is_focus": True,
        }
        # Singoli competitor
        for comp in competitors:
            entry[comp] = {
                "pen":      _vc(pen_comp_n, "Penetrazione (%)", canale, comp),
                "ric":      _vc(ric_comp_n, "Ricorda (%)",      canale, comp),
                "ing":      _vc(ing_comp_n, "Ingaggio (%)",     canale, comp),
                "n_hcp":    _nhcp_comp(canale, comp),
                "is_focus": False,
            }
        data[canale] = entry

    return jsonify({
        "azienda":    azienda,
        "competitors": competitors,
        "canali":     TARGET_CANALI_VS,
        "data":       data,
        "n_hcp_az":   int(len(df_az)),
    })


# ──────────────────────────────────────────────────────────────
# EXPORT Excel (GET con query params)
# ──────────────────────────────────────────────────────────────
@modulo2_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_excel():
    if request.method == "GET":
        body = {
            "target":      request.args.getlist("target"),
            "azienda":     request.args.get("azienda", ""),
            "competitors": request.args.getlist("competitors"),
        }
    else:
        body = request.get_json(silent=True) or {}

    try:
        df_perf, df_az, df_market, azienda, competitors, cols = _prepare_dfs(body)
        k = _calc_all(df_perf, df_az, df_market, competitors, cols)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        k["pen_az"].to_excel(writer,  sheet_name="Pen_Azienda",   index=False)
        k["ric_az"].to_excel(writer,  sheet_name="Ric_Azienda",   index=False)
        k["ing_az"].to_excel(writer,  sheet_name="Ing_Azienda",   index=False)
        _dict_to_df(k["nps_az"]).to_excel(writer, sheet_name="NPS_Azienda", index=False)
        if not k["pen_comp"].empty:
            k["pen_comp"].to_excel(writer, sheet_name="Pen_Competitor", index=False)
            k["ric_comp"].to_excel(writer, sheet_name="Ric_Competitor", index=False)
            k["ing_comp"].to_excel(writer, sheet_name="Ing_Competitor", index=False)
            if isinstance(k["nps_comp"], pd.DataFrame) and not k["nps_comp"].empty:
                k["nps_comp"].to_excel(writer, sheet_name="NPS_Competitor", index=False)
        k["pen_merc"].to_excel(writer,  sheet_name="Pen_Mercato",  index=False)
        k["ric_merc"].to_excel(writer,  sheet_name="Ric_Mercato",  index=False)
        k["ing_merc"].to_excel(writer,  sheet_name="Ing_Mercato",  index=False)
        _dict_to_df(k["nps_merc"]).to_excel(writer, sheet_name="NPS_Mercato", index=False)
    buf.seek(0)

    label    = f"{azienda}_vs_{'_'.join(competitors[:3]) if competitors else 'mercato'}"
    filename = f"MCM_Performance_{label}.xlsx".replace(" ", "_")
    return send_file(
        buf, as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
