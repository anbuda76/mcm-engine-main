"""
app/ai/tools_performance.py
────────────────────────────
Tool functions per Market Performance Agent.

Ogni funzione wrappa i motori src/performance/ e ritorna dict JSON-serializzabili
pronti per essere passati come osservazione nel loop ReAct dell'agente.
"""

import sys, os, json
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.data_cache import get_data
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP
from src.performance.kpi_penetrazione_azienda import kpi_penetrazione_azienda
from src.performance.kpi_ricordo_azienda      import kpi_ricordo_azienda
from src.performance.kpi_nps_azienda          import kpi_nps_azienda
from src.performance.kpi_propensione_azienda  import kpi_propensione_azienda
from src.performance.trend_engine             import trend_engine


# ── Helpers interni ──────────────────────────────────────────────────────────

def _filtra(df: pd.DataFrame, col: str, vals: list) -> pd.DataFrame:
    if not vals or not col or col not in df.columns:
        return df
    return df[df[col].isin(vals)].copy()


def _norm_canale(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _safe_records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _get_az_df(data: dict, azienda: str, target: list):
    """Restituisce (df_all, df_az, col_az, errore_str)."""
    cols   = data["columns"]
    df_all = _filtra(data["df_perf"], cols.get("col_target"), target)
    col_az = cols.get("col_azienda", "")

    if not col_az or col_az not in df_all.columns:
        return None, None, col_az, "Colonna azienda non trovata nel dataset."

    if azienda not in df_all[col_az].values:
        disponibili = df_all[col_az].dropna().unique().tolist()
        return None, None, col_az, (
            f"Azienda '{azienda}' non trovata. "
            f"Usa list_aziende per vedere quelle disponibili. "
            f"Prime disponibili: {disponibili[:8]}"
        )

    df_az = df_all[df_all[col_az] == azienda].copy()
    if len(df_az) < 5:
        return None, None, col_az, (
            f"Campione troppo piccolo per '{azienda}': {len(df_az)} HCP. "
            "Verifica filtri target o dataset."
        )

    return df_all, df_az, col_az, None


# ── Tool 1: Lista aziende ────────────────────────────────────────────────────

def tool_list_aziende(target: list = None) -> dict:
    """
    Lista le aziende disponibili con il numero di HCP per ciascuna.
    """
    target = target or []
    data   = get_data()
    cols   = data["columns"]
    df     = _filtra(data["df_perf"], cols.get("col_target"), target)
    col_az = cols.get("col_azienda", "")

    if not col_az or col_az not in df.columns:
        return {"errore": "Colonna azienda non trovata nel dataset."}

    counts = df[col_az].value_counts()
    return {
        "aziende_disponibili":  counts.index.tolist(),
        "n_hcp_per_azienda":    {az: int(n) for az, n in counts.items()},
        "totale_hcp_dataset":   len(df),
        "target_filtro":        target if target else "tutti i segmenti",
    }


# ── Tool 2: Performance completa azienda ─────────────────────────────────────

def tool_get_performance_azienda(azienda: str, target: list = None) -> dict:
    """
    Analisi completa di un'azienda: NPS, propensione, penetrazione top canali e gap vs mercato.
    """
    target = target or []
    if not azienda:
        return {"errore": "Specifica il nome dell'azienda. Usa list_aziende per vedere quelle disponibili."}

    data = get_data()
    cols = data["columns"]
    df_all, df_az, col_az, err = _get_az_df(data, azienda, target)
    if err:
        return {"errore": err}

    n_az  = len(df_az)
    n_tot = len(df_all)
    col_prop = cols.get("col_prop", "Q16")

    # NPS azienda focus
    nps_az   = kpi_nps_azienda(df_az, col_prop)

    # NPS benchmark (tutto il mercato = tutti gli HCP incluso focus)
    nps_mkt  = kpi_nps_azienda(df_all, col_prop) if n_tot >= 5 else {}

    # Propensione
    prop_az  = kpi_propensione_azienda(df_az, col_prop)

    # Penetrazione top canali
    df_pen   = _norm_canale(kpi_penetrazione_azienda(df_az, cols["canali_perf"]))
    top_pen  = _safe_records(df_pen.head(6)[["Canale", "Penetrazione (%)"]]) \
               if not df_pen.empty else []

    # Gap NPS
    nps_focus = nps_az.get("NPS")
    nps_bench = nps_mkt.get("NPS")
    nps_gap   = round((nps_focus or 0) - (nps_bench or 0), 1) \
                if nps_focus is not None and nps_bench is not None else None

    return {
        "azienda":              azienda,
        "n_hcp_azienda":        n_az,
        "n_hcp_mercato":        n_tot,
        "quota_dataset_%":      round(n_az / n_tot * 100, 1) if n_tot else None,
        "target_filtro":        target if target else "tutti i segmenti",
        "nps": {
            "azienda":          nps_focus,
            "mercato":          nps_bench,
            "gap_pp":           nps_gap,
            "valutazione":      ("sopra mercato" if nps_gap and nps_gap > 0
                                 else "sotto mercato" if nps_gap and nps_gap < 0
                                 else "in linea col mercato"),
            "promoters_%":      nps_az.get("Promoters (%)"),
            "detractors_%":     nps_az.get("Detractors (%)"),
            "n_rispondenti":    nps_az.get("N rispondenti"),
        },
        "propensione": {
            "media":            prop_az.get("Media propensione"),
            "top_box_9_10_%":   prop_az.get("Top box 9-10 (%)"),
            "medio_7_8_%":      prop_az.get("Medio 7-8 (%)"),
            "basso_1_6_%":      prop_az.get("Basso 1-6 (%)"),
        },
        "top_canali_penetrazione": top_pen,
    }


# ── Tool 3: Benchmark canali vs mercato ──────────────────────────────────────

def tool_get_benchmark_canali(azienda: str, target: list = None, top_n: int = 8) -> dict:
    """
    Confronto canale per canale: penetrazione e ricordo dell'azienda vs benchmark di mercato.
    """
    target = target or []
    if not azienda:
        return {"errore": "Specifica il nome dell'azienda."}

    data = get_data()
    cols = data["columns"]
    df_all, df_az, col_az, err = _get_az_df(data, azienda, target)
    if err:
        return {"errore": err}

    col_ricordo = cols.get("col_ricordo", "")

    # Penetrazione azienda vs mercato totale
    pen_az  = _norm_canale(kpi_penetrazione_azienda(df_az,  cols["canali_perf"]))
    pen_mkt = _norm_canale(kpi_penetrazione_azienda(df_all, cols["canali_perf"]))

    mkt_pen_dict = {}
    if not pen_mkt.empty:
        mkt_pen_dict = {r["Canale"]: r["Penetrazione (%)"]
                        for r in _safe_records(pen_mkt[["Canale", "Penetrazione (%)"]])}

    # Ricordo azienda vs mercato (solo se colonna disponibile)
    mkt_ric_dict = {}
    ric_az_dict  = {}
    if col_ricordo:
        try:
            ric_az  = _norm_canale(kpi_ricordo_azienda(df_az,  col_ricordo, cols["canali_perf"]))
            ric_mkt = _norm_canale(kpi_ricordo_azienda(df_all, col_ricordo, cols["canali_perf"]))
            # Escludi riga TOTALE AZIENDA
            ric_az  = ric_az[ric_az["Canale"]  != "TOTALE AZIENDA"]
            ric_mkt = ric_mkt[ric_mkt["Canale"] != "TOTALE AZIENDA"]
            if not ric_az.empty:
                ric_az_dict  = {r["Canale"]: r["Ricorda (%)"]
                                for r in _safe_records(ric_az[["Canale", "Ricorda (%)"]])}
            if not ric_mkt.empty:
                mkt_ric_dict = {r["Canale"]: r["Ricorda (%)"]
                                for r in _safe_records(ric_mkt[["Canale", "Ricorda (%)"]])}
        except Exception:
            pass  # ricordo non disponibile, continua solo con penetrazione

    # Costruisci benchmark per canale
    benchmark = []
    if not pen_az.empty:
        for r in _safe_records(pen_az[["Canale", "Penetrazione (%)"]]):
            c          = r["Canale"]
            pen_focus  = round(r["Penetrazione (%)"], 1)
            pen_mkt_v  = round(mkt_pen_dict.get(c, 0), 1)
            entry = {
                "canale":                   c,
                "penetrazione_azienda_%":   pen_focus,
                "penetrazione_mercato_%":   pen_mkt_v,
                "gap_penetrazione_pp":      round(pen_focus - pen_mkt_v, 1),
            }
            if ric_az_dict:
                ric_focus = ric_az_dict.get(c)
                ric_mkt_v = mkt_ric_dict.get(c)
                if ric_focus is not None:
                    entry["ricordo_azienda_%"]  = round(ric_focus, 1)
                    entry["ricordo_mercato_%"]  = round(ric_mkt_v, 1) if ric_mkt_v else None
                    entry["gap_ricordo_pp"]     = (round(ric_focus - ric_mkt_v, 1)
                                                   if ric_mkt_v is not None else None)
            benchmark.append(entry)

    benchmark.sort(key=lambda x: x["penetrazione_azienda_%"], reverse=True)

    sopra = [b["canale"] for b in benchmark if b["gap_penetrazione_pp"] > 0]
    sotto = [b["canale"] for b in benchmark if b["gap_penetrazione_pp"] < 0]

    return {
        "azienda":              azienda,
        "n_hcp_azienda":        len(df_az),
        "n_hcp_mercato":        len(df_all),
        "target_filtro":        target if target else "tutti i segmenti",
        "benchmark_canali":     benchmark[:top_n],
        "canali_sopra_mercato": sopra,
        "canali_sotto_mercato": sotto,
        "sintesi": (
            f"{azienda} è sopra mercato su {len(sopra)} canali "
            f"e sotto mercato su {len(sotto)} canali."
        ),
    }


# ── Tool 4: Trend temporale ──────────────────────────────────────────────────

def tool_get_trend_azienda(azienda: str, target: list = None) -> dict:
    """
    Evoluzione annuale dei KPI: penetrazione, ricordo, NPS e propensione per anno.
    """
    target = target or []
    if not azienda:
        return {"errore": "Specifica il nome dell'azienda."}

    data = get_data()
    cols = data["columns"]
    df_all, df_az, col_az, err = _get_az_df(data, azienda, target)
    if err:
        return {"errore": err}

    col_anno = "Anno"
    if col_anno not in df_all.columns:
        return {"errore": "Colonna Anno non presente nel dataset — dati trend non disponibili."}

    anni = sorted(df_all[col_anno].dropna().astype(str).unique().tolist())
    if len(anni) < 2:
        return {"errore": f"Serve almeno 2 anni per il trend. Disponibile solo: {anni}"}

    # Prepara df con colonna Periodo per trend_engine
    df_t = df_all.copy()
    df_t["Periodo"] = df_t[col_anno].astype(str)
    periodi = sorted(df_t["Periodo"].dropna().unique().tolist())

    try:
        result = trend_engine(
            df_perf=df_t,
            columns={**cols, "col_azienda": col_az},
            azienda_focus=azienda,
            periodi=periodi,
        )
    except Exception as e:
        return {"errore": f"Errore nel calcolo del trend: {e}"}

    # Serializza KPI per anno
    kpi_per_anno = {}
    for periodo, info in result["Azienda"]["KPI_per_periodo"].items():
        if not info.get("valid"):
            kpi_per_anno[str(periodo)] = {
                "valido":  False,
                "motivo":  info.get("message", "dati insufficienti"),
            }
            continue

        pen  = info.get("Penetrazione")
        ric  = info.get("Ricordo")
        nps  = info.get("NPS")
        prop = info.get("Propensione")

        kpi_per_anno[str(periodo)] = {
            "valido":               True,
            "n_hcp":                len(pen) if pen is not None and not pen.empty else 0,
            "penetrazione_media_%": round(float(pen["Penetrazione (%)"].mean()), 1)
                                    if pen is not None and not pen.empty else None,
            "ricordo_medio_%":      round(float(ric["Ricordo (%)"].mean()), 1)
                                    if ric is not None and not ric.empty else None,
            "nps":                  nps.get("NPS") if isinstance(nps, dict) else None,
            "propensione_media":    prop.get("Media propensione")
                                    if isinstance(prop, dict) else None,
        }

    # Calcola variazione YoY sull'NPS
    anni_validi = [a for a, v in kpi_per_anno.items() if v.get("valido")]
    trend_nps   = []
    for i in range(1, len(anni_validi)):
        a_prec = anni_validi[i - 1]
        a_curr = anni_validi[i]
        nps_p  = kpi_per_anno[a_prec].get("nps")
        nps_c  = kpi_per_anno[a_curr].get("nps")
        if nps_p is not None and nps_c is not None:
            trend_nps.append({
                "da": a_prec, "a": a_curr,
                "variazione_nps_pp": round(nps_c - nps_p, 1),
                "direzione": "↑ crescita" if nps_c > nps_p else "↓ calo" if nps_c < nps_p else "→ stabile",
            })

    return {
        "azienda":          azienda,
        "target_filtro":    target if target else "tutti i segmenti",
        "anni_disponibili": periodi,
        "kpi_per_anno":     kpi_per_anno,
        "trend_nps_yoy":    trend_nps,
    }


# ── Tool 5: Attributi relazionali azienda (Q13 rilevanza + Q15 5D) ───────────

# Mapping Q15 colonne → label leggibile
_Q15_LABELS = {
    "Q15_1": "Chiarezza",
    "Q15_2": "Credibilita",
    "Q15_3": "Rilevanza Topic",
    "Q15_4": "Innovazione",
    "Q15_5": "Affidabilita",
}


def tool_get_attributi_azienda(azienda: str, target: list = None) -> dict:
    """
    Analisi degli attributi relazionali percepiti dai medici per un'azienda.
    Q13: rilevanza dei contenuti (1–5).
    Q15_1..5: Chiarezza, Credibilità, Rilevanza Topic, Innovazione, Affidabilità (scala 1–10).
    Include confronto vs benchmark di mercato per ogni attributo.
    """
    target = target or []
    if not azienda:
        return {"errore": "Specifica il nome dell'azienda (usa list_aziende per vedere quelle disponibili)."}

    data = get_data()
    df_all, df_az, col_az, err = _get_az_df(data, azienda, target)
    if err:
        return {"errore": err}

    def _mean_cols(df: pd.DataFrame, prefix: str) -> dict:
        """Calcola media per ogni colonna che inizia con prefix."""
        cols_found = [c for c in df.columns if c.upper().startswith(prefix.upper())]
        result = {}
        for col in cols_found:
            vals = df[col].dropna()
            if len(vals) >= 5:
                result[col] = round(float(vals.mean()), 2)
        return result

    # Q13 rilevanza
    q13_az  = _mean_cols(df_az,  "Q13")
    q13_mkt = _mean_cols(df_all, "Q13")

    # Q15 attributi
    q15_az  = _mean_cols(df_az,  "Q15")
    q15_mkt = _mean_cols(df_all, "Q15")

    # Formatta output con label leggibili
    attributi_az  = {_Q15_LABELS.get(k, k): v for k, v in q15_az.items()}
    attributi_mkt = {_Q15_LABELS.get(k, k): v for k, v in q15_mkt.items()}

    # Gap vs benchmark
    gap_attributi = {}
    for attr, val_az in attributi_az.items():
        val_mkt = attributi_mkt.get(attr)
        if val_mkt is not None:
            gap_attributi[attr] = {
                "azienda":  val_az,
                "mercato":  val_mkt,
                "gap_pp":   round(val_az - val_mkt, 2),
                "posizione": "sopra mercato" if val_az > val_mkt else "sotto mercato" if val_az < val_mkt else "in linea",
            }

    # Top / bottom attributo
    if attributi_az:
        top_attr    = max(attributi_az, key=attributi_az.get)
        bottom_attr = min(attributi_az, key=attributi_az.get)
    else:
        top_attr = bottom_attr = None

    # Rilevanza Q13
    ril_az  = round(sum(q13_az.values()) / len(q13_az), 2)  if q13_az  else None
    ril_mkt = round(sum(q13_mkt.values()) / len(q13_mkt), 2) if q13_mkt else None

    return {
        "azienda":               azienda,
        "n_hcp_azienda":         len(df_az),
        "n_hcp_mercato":         len(df_all),
        "target_filtro":         target if target else "tutti i segmenti",
        "rilevanza_contenuti": {
            "azienda":   ril_az,
            "mercato":   ril_mkt,
            "gap":       round(ril_az - ril_mkt, 2) if ril_az and ril_mkt else None,
            "scala":     "1=per nulla rilevante  5=molto rilevante",
        },
        "attributi_q15": {
            "azienda":       attributi_az,
            "mercato":       attributi_mkt,
            "gap_vs_mercato": gap_attributi,
            "scala":         "1=molto basso  10=eccellente",
        },
        "attributo_top":    top_attr,
        "attributo_bottom": bottom_attr,
        "nota": (
            "Attributi sopra benchmark = punti di forza nella relazione col medico. "
            "Attributi sotto benchmark = aree di miglioramento nella comunicazione."
        ),
    }


# ── Tool 6: What-if — se l'azienda raggiungesse il benchmark sui canali gap ──

def tool_whatif_benchmark_gap(azienda: str, target: list = None, top_n: int = 8) -> dict:
    """
    Simulazione what-if: se l'azienda colmasse il gap di penetrazione
    sui canali dove è sotto il benchmark di mercato, quanti HCP aggiuntivi raggiungerebbe?
    Include stima del ricordo incrementale applicando il tasso di ricordo di mercato.
    NOTA: proiezione lineare, non previsione causale.
    """
    target = target or []
    if not azienda:
        return {"errore": "Specifica il nome dell'azienda."}

    data = get_data()
    cols = data["columns"]
    df_all, df_az, col_az, err = _get_az_df(data, azienda, target)
    if err:
        return {"errore": err}

    n_az  = len(df_az)
    n_mkt = len(df_all)

    col_ricordo = cols.get("col_ricordo", "")

    # Penetrazione azienda vs mercato
    pen_az  = _norm_canale(kpi_penetrazione_azienda(df_az,  cols["canali_perf"]))
    pen_mkt = _norm_canale(kpi_penetrazione_azienda(df_all, cols["canali_perf"]))

    mkt_pen_map = {}
    if not pen_mkt.empty:
        mkt_pen_map = {r["Canale"]: r["Penetrazione (%)"]
                       for r in _safe_records(pen_mkt[["Canale", "Penetrazione (%)"]])}

    # Ricordo mercato per canale (per stimare recall incrementale)
    mkt_ric_map = {}
    if col_ricordo:
        try:
            ric_mkt = _norm_canale(kpi_ricordo_azienda(df_all, col_ricordo, cols["canali_perf"]))
            ric_mkt = ric_mkt[ric_mkt["Canale"] != "TOTALE AZIENDA"]
            if not ric_mkt.empty:
                mkt_ric_map = {r["Canale"]: r.get("Ricorda (%)", 0)
                               for r in _safe_records(ric_mkt)}
        except Exception:
            pass

    # Costruisci opportunità per canale (solo dove azienda < benchmark)
    opportunita = []
    if not pen_az.empty:
        for r in _safe_records(pen_az[["Canale", "Penetrazione (%)"]]):
            c        = r["Canale"]
            pen_f    = round(r["Penetrazione (%)"], 1)
            pen_b    = round(mkt_pen_map.get(c, pen_f), 1)
            gap      = round(pen_b - pen_f, 1)

            if gap <= 0:
                continue  # già sopra o in linea col benchmark

            hcp_potenziali = round((gap / 100.0) * n_az)
            tasso_ric      = mkt_ric_map.get(c)
            recall_stima   = round(hcp_potenziali * (tasso_ric or 0) / 100)

            priorita = "Alta" if gap > 10 else "Media" if gap > 5 else "Bassa"

            opportunita.append({
                "canale":                       c,
                "penetrazione_azienda_%":       pen_f,
                "penetrazione_benchmark_%":     pen_b,
                "gap_pp":                       gap,
                "hcp_aggiuntivi_stimati":       hcp_potenziali,
                "recall_incrementale_stimato":  recall_stima if tasso_ric else None,
                "tasso_ricordo_mercato_%":      round(tasso_ric, 1) if tasso_ric else None,
                "priorita":                     priorita,
            })

    opportunita.sort(key=lambda x: x["gap_pp"], reverse=True)

    totale_hcp_potenziali    = sum(o["hcp_aggiuntivi_stimati"] for o in opportunita)
    totale_recall_potenziale = sum(o["recall_incrementale_stimato"] or 0 for o in opportunita)

    return {
        "azienda":                    azienda,
        "n_hcp_azienda":              n_az,
        "target_filtro":              target if target else "tutti i segmenti",
        "scenario":                   f"Colmare il gap di penetrazione verso il benchmark di mercato",
        "canali_con_opportunita":     len(opportunita),
        "opportunita_per_canale":     opportunita[:top_n],
        "totale_hcp_potenziali":      totale_hcp_potenziali,
        "totale_recall_potenziale":   totale_recall_potenziale if mkt_ric_map else None,
        "avvertenza": (
            "SIMULAZIONE LINEARE — stima il potenziale se l'azienda raggiungesse il benchmark "
            "di mercato su ogni canale sotto-performante. "
            "Non incorpora vincoli di budget, effetti competitivi o saturazione. "
            "Usare come prioritizzazione strategica, non come forecast."
        ),
    }


# ── Schema tools (formato Ollama / OpenAI) ───────────────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_aziende",
            "description": (
                "Lista le aziende disponibili nel dataset con il numero di HCP per ciascuna. "
                "Usa come PRIMO passo se l'utente non specifica l'azienda "
                "o vuole sapere quali sono disponibili."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_azienda",
            "description": (
                "Analisi completa di un'azienda: NPS, propensione al consiglio, "
                "penetrazione top canali e confronto gap vs benchmark di mercato. "
                "Usa per una panoramica completa delle performance di un'azienda."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "azienda": {
                        "type": "string",
                        "description": "Nome esatto dell'azienda (usa list_aziende se non noto).",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                },
                "required": ["azienda"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_benchmark_canali",
            "description": (
                "Confronto canale per canale: penetrazione (e ricordo se disponibile) "
                "dell'azienda focus vs benchmark mercato, con gap in punti percentuali. "
                "Usa per capire su quali canali l'azienda è sopra o sotto il mercato."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "azienda": {
                        "type": "string",
                        "description": "Nome dell'azienda da confrontare col mercato.",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Numero di canali da restituire (default 8).",
                        "default": 8,
                    },
                },
                "required": ["azienda"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_azienda",
            "description": (
                "Evoluzione annuale dei KPI di un'azienda: penetrazione, ricordo, NPS e propensione "
                "con variazione year-over-year. "
                "Usa per domande su crescita, calo, trend nel tempo o evoluzione storica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "azienda": {
                        "type": "string",
                        "description": "Nome dell'azienda di cui analizzare il trend.",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                },
                "required": ["azienda"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_attributi_azienda",
            "description": (
                "Analisi degli attributi relazionali percepiti dai medici per un'azienda: "
                "Q13 (rilevanza contenuti, 1–5) e Q15 (5 dimensioni: Chiarezza, Credibilità, "
                "Rilevanza Topic, Innovazione, Affidabilità, scala 1–10), "
                "con confronto vs benchmark di mercato. "
                "Usa per domande su percezione, reputazione, credibilità, chiarezza comunicazione, "
                "punti di forza/debolezza relazionali, attributi Q15."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "azienda": {
                        "type": "string",
                        "description": "Nome esatto dell'azienda (usa list_aziende se non noto).",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                },
                "required": ["azienda"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "whatif_benchmark_gap",
            "description": (
                "Simulazione what-if: se l'azienda colmasse il gap di penetrazione sui canali "
                "dove è sotto il benchmark di mercato, quanti HCP aggiuntivi raggiungerebbe? "
                "Include stima del ricordo incrementale e priorità per canale. "
                "Usa per domande 'cosa succederebbe se', 'potenziale', 'se investissimo di più', "
                "'e se raggiungessimo il benchmark', 'where to invest', 'priorità canali'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "azienda": {
                        "type": "string",
                        "description": "Nome dell'azienda da analizzare.",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Numero di canali opportunità da restituire (default 8).",
                        "default": 8,
                    },
                },
                "required": ["azienda"],
            },
        },
    },
]

# ── Registry locale: nome → funzione Python ──────────────────────────────────

TOOL_REGISTRY = {
    "list_aziende":            tool_list_aziende,
    "get_performance_azienda": tool_get_performance_azienda,
    "get_benchmark_canali":    tool_get_benchmark_canali,
    "get_trend_azienda":       tool_get_trend_azienda,
    "get_attributi_azienda":   tool_get_attributi_azienda,
    "whatif_benchmark_gap":    tool_whatif_benchmark_gap,
}
