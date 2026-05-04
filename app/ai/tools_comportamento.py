"""
app/ai/tools_comportamento.py
──────────────────────────────
Tool functions per HCP Behavior Agent.

Ogni funzione wrappa i motori src/behavior/ e ritorna dict JSON-serializzabili
pronti per essere passati come osservazione nel loop ReAct dell'agente.
"""

import sys, os, json
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.data_cache import get_data, get_specializzazioni
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP
from src.behavior.kpi_penetrazione  import kpi_penetrazione
from src.behavior.kpi_utilita       import kpi_utilita
from src.behavior.kpi_ricordo       import kpi_ricordo_canali
from src.behavior.kpi_ingaggio      import kpi_ingaggio_canali
from src.behavior.kpi_nps_canali    import kpi_nps_canali
from src.behavior.kpi_ocv_mix       import ocv_mix_engine


# ── Helpers interni ──────────────────────────────────────────────────────────

def _filtra(df: pd.DataFrame, col: str, vals: list) -> pd.DataFrame:
    if not vals or not col or col not in df.columns:
        return df
    return df[df[col].isin(vals)].copy()


def _norm_canale(df: pd.DataFrame) -> pd.DataFrame:
    """Applica CANALI_MAP alla colonna Canale (nomi leggibili)."""
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _safe_records(df: pd.DataFrame) -> list:
    """DataFrame → list[dict] con NaN convertiti in None."""
    return json.loads(df.to_json(orient="records", force_ascii=False))


# ── Tool 1: KPI Comportamento generale ──────────────────────────────────────

def tool_get_comportamento_kpi(target: list = None, top_n: int = 8) -> dict:
    """
    Penetrazione, ricordo e ingaggio per canale.
    Restituisce i top_n canali ordinati per ciascun KPI.
    """
    target = target or []

    data    = get_data()
    cols    = data["columns"]
    df_beh  = _filtra(data["df_beh"],  cols.get("col_target"), target)
    df_perf = _filtra(data["df_perf"], cols.get("col_target"), target)

    n_hcp = len(df_beh)
    if n_hcp < 5:
        return {
            "errore": f"Campione troppo piccolo: {n_hcp} HCP. "
                      "Prova a rimuovere i filtri target o verifica i dati caricati."
        }

    df_pen = _norm_canale(kpi_penetrazione(df_beh, cols["canali_11"]))
    df_ric = _norm_canale(kpi_ricordo_canali(df_perf, cols["canali_perf"]))
    df_ing = _norm_canale(kpi_ingaggio_canali(df_perf, cols["canali_perf"]))

    top_pen = _safe_records(df_pen.head(top_n)[["Canale", "Penetrazione (%)"]]) \
              if not df_pen.empty else []
    top_ric = _safe_records(df_ric.head(top_n)[["Canale", "Ricordo (%)"]]) \
              if not df_ric.empty else []
    top_ing = _safe_records(df_ing.head(top_n)[["Canale", "Ingaggio totale (%)"]]) \
              if not df_ing.empty else []

    return {
        "n_hcp":                 n_hcp,
        "target_filtro":         target if target else "tutti i segmenti",
        "penetrazione_media_%":  round(float(df_pen["Penetrazione (%)"].mean()), 1)
                                 if not df_pen.empty else None,
        "ricordo_medio_%":       round(float(df_ric["Ricordo (%)"].mean()), 1)
                                 if not df_ric.empty else None,
        "ingaggio_medio_%":      round(float(df_ing.attrs.get("media_ingaggio", 0)), 1),
        "top_canali_penetrazione": top_pen,
        "top_canali_ricordo":      top_ric,
        "top_canali_ingaggio":     top_ing,
    }


# ── Tool 2: Funnel HCP ───────────────────────────────────────────────────────

def tool_get_funnel_hcp(target: list = None) -> dict:
    """
    Funnel per canale: Penetrazione → Ricordo → Ingaggio con conversion rate.
    Utile per capire dove si perdono i medici nel percorso di comunicazione.
    """
    target = target or []

    data    = get_data()
    cols    = data["columns"]
    df_beh  = _filtra(data["df_beh"],  cols.get("col_target"), target)
    df_perf = _filtra(data["df_perf"], cols.get("col_target"), target)

    if len(df_beh) < 5:
        return {"errore": "Campione insufficiente per calcolare il funnel HCP."}

    df_pen = _norm_canale(kpi_penetrazione(df_beh, cols["canali_11"]))
    df_ric = _norm_canale(kpi_ricordo_canali(df_perf, cols["canali_perf"]))
    df_ing = _norm_canale(kpi_ingaggio_canali(df_perf, cols["canali_perf"]))

    # Costruisci dizionario per canale
    funnel: dict[str, dict] = {}
    for _, row in df_pen.iterrows():
        c = row["Canale"]
        funnel[c] = {"canale": c, "penetrazione_%": round(row["Penetrazione (%)"], 1)}

    for _, row in df_ric.iterrows():
        c = row["Canale"]
        if c in funnel:
            funnel[c]["ricordo_%"] = round(row["Ricordo (%)"], 1)

    for _, row in df_ing.iterrows():
        c = row["Canale"]
        if c in funnel:
            funnel[c]["ingaggio_%"] = round(row["Ingaggio totale (%)"], 1)

    # Calcola conversion rate pen→ric e ric→ing
    result = []
    for kpi in funnel.values():
        pen = kpi.get("penetrazione_%", 0)
        ric = kpi.get("ricordo_%")
        ing = kpi.get("ingaggio_%")
        kpi["conv_pen_ric_%"] = round(ric / pen * 100, 1) if pen and ric else None
        kpi["conv_ric_ing_%"] = round(ing / ric * 100, 1) if ric and ing else None
        result.append(kpi)

    result.sort(key=lambda x: x.get("penetrazione_%", 0), reverse=True)

    return {
        "n_hcp":           len(df_beh),
        "target_filtro":   target if target else "tutti i segmenti",
        "funnel_per_canale": result[:12],
        "nota": (
            "conv_pen_ric_%: % dei medici raggiunti che ricordano il messaggio. "
            "conv_ric_ing_%: % dei medici che ricordano e si sono anche ingaggiati."
        ),
    }


# ── Tool 3: OCV Mix ──────────────────────────────────────────────────────────

def tool_get_ocv_mix(target: list = None, max_combo: int = 3) -> dict:
    """
    Calcola le combinazioni di canali che massimizzano l'OCV (Omnichannel Value).
    Restituisce le top combinazioni ordinate per OCV decrescente.
    """
    target    = target or []
    max_combo = max(2, min(4, int(max_combo)))  # clamp 2–4

    data = get_data()
    cols = data["columns"]
    df_beh = _filtra(data["df_beh"], cols.get("col_target"), target)

    if len(df_beh) < 10:
        return {
            "errore": f"Campione insufficiente per OCV: {len(df_beh)} HCP "
                      "(minimo 10). Rimuovi filtri target."
        }

    recall_col = cols.get("col_ricordo", "")
    if not recall_col:
        return {"errore": "Colonna ricordo non configurata nel dataset."}

    try:
        df_ocv = ocv_mix_engine(
            df=df_beh,
            channel_cols=cols["canali_11"],
            recall_col=recall_col,
            max_combination=max_combo,
            min_exposed=10,
        )
    except Exception as e:
        return {"errore": f"Errore calcolo OCV: {e}"}

    if df_ocv.empty:
        return {"errore": "Nessuna combinazione OCV calcolabile con i dati disponibili."}

    cols_out = [c for c in
                ["Channel Mix", "N Channels", "N HCP", "OCV (%)", "OCV Class", "Business Action"]
                if c in df_ocv.columns]

    top = _safe_records(df_ocv.head(10)[cols_out])
    best = df_ocv.iloc[0]

    return {
        "n_hcp":                      len(df_beh),
        "target_filtro":              target if target else "tutti i segmenti",
        "max_combo_canali":           max_combo,
        "n_combinazioni_analizzate":  len(df_ocv),
        "best_mix": {
            "canali":  best.get("Channel Mix"),
            "ocv_%":   round(float(best.get("OCV (%)", 0)), 1),
            "classe":  best.get("OCV Class"),
            "azione":  best.get("Business Action"),
        },
        "top_10_mix": top,
    }


# ── Tool 4: Lista specializzazioni ───────────────────────────────────────────

def tool_list_specializzazioni() -> dict:
    """
    Lista le specializzazioni mediche (target) disponibili con il numero di HCP per ognuna.
    Primo passo utile se l'utente non ha specificato il segmento medico.
    """
    specs = get_specializzazioni()
    data  = get_data()
    col_tgt = data["columns"].get("col_target")

    counts = {}
    if col_tgt and col_tgt in data["df_beh"].columns:
        counts = {k: int(v) for k, v in
                  data["df_beh"][col_tgt].value_counts().items()}

    return {
        "specializzazioni_disponibili": specs,
        "n_hcp_per_specializzazione":   {s: counts.get(s, 0) for s in specs},
        "totale_hcp":                   len(data["df_beh"]),
    }


# ── Tool 5: Utilità percepita per canale (Q6) ────────────────────────────────

def tool_get_utilita_canali(target: list = None) -> dict:
    """
    Utilità media percepita per canale (Q6, scala 1–7).
    Mostra quanto i medici trovano utili i canali indipendentemente dal loro uso attuale.
    Alta utilità + bassa penetrazione = opportunità di investimento.
    """
    target = target or []

    data    = get_data()
    cols    = data["columns"]
    df_beh  = _filtra(data["df_beh"], cols.get("col_target"), target)

    if len(df_beh) < 5:
        return {"errore": f"Campione troppo piccolo ({len(df_beh)} HCP)."}

    canali_util = cols.get("canali_utilita", [])
    if not canali_util:
        return {"errore": "Colonne utilità (Q6) non configurate nel dataset."}

    try:
        df_util = kpi_utilita(df_beh, canali_util)
        df_util = _norm_canale(df_util)

        # Trova la colonna valore (primo campo non-Canale)
        val_cols = [c for c in df_util.columns if c != "Canale"]
        if not val_cols:
            return {"errore": "kpi_utilita non ha restituito colonne di valore."}
        val_col = val_cols[0]

        df_util = df_util.sort_values(val_col, ascending=False).reset_index(drop=True)
        records = _safe_records(df_util[["Canale", val_col]])

        # Classifica
        alta    = [r for r in records if r[val_col] is not None and r[val_col] >= 6.0]
        media   = [r for r in records if r[val_col] is not None and 4.0 <= r[val_col] < 6.0]
        bassa   = [r for r in records if r[val_col] is not None and r[val_col] < 4.0]

        return {
            "n_hcp":                  len(df_beh),
            "target_filtro":          target if target else "tutti i segmenti",
            "top_canali_utilita":     records[:12],
            "media_utilita_overall":  round(float(df_util[val_col].mean()), 2),
            "scala":                  "1=per nulla utile  |  4=neutro  |  7=estremamente utile",
            "canali_alta_utilita":    [r["Canale"] for r in alta],
            "canali_media_utilita":   [r["Canale"] for r in media],
            "canali_bassa_utilita":   [r["Canale"] for r in bassa],
            "nota": (
                "Utilità alta (≥6): i medici preferirebbero usare di più questi canali. "
                "Utilità bassa (≤3): canali poco apprezzati — aumentarne l'uso rischia saturazione."
            ),
        }
    except Exception as e:
        return {"errore": f"Errore calcolo utilità: {e}"}


# ── Tool 6: Gap Utilità–Penetrazione (opportunità e frizioni) ─────────────────

def tool_get_gap_analisi(target: list = None) -> dict:
    """
    Analisi del gap tra utilità percepita (Q6) e penetrazione reale (Q11a).
    Identifica:
    - Opportunità nascoste: alta utilità ma bassa penetrazione (canali sottoinvestiti)
    - Frizioni/rischio saturazione: alta penetrazione ma bassa utilità (possibile fastidio)
    Formula: Gap = Utilità_media − (Penetrazione% / 10)   [entrambe su scala 0–10]
    """
    target = target or []

    data    = get_data()
    cols    = data["columns"]
    df_beh  = _filtra(data["df_beh"],  cols.get("col_target"), target)

    if len(df_beh) < 5:
        return {"errore": f"Campione troppo piccolo ({len(df_beh)} HCP)."}

    canali_util = cols.get("canali_utilita", [])
    if not canali_util:
        return {"errore": "Colonne utilità (Q6) non configurate nel dataset."}

    try:
        # Penetrazione
        df_pen  = _norm_canale(kpi_penetrazione(df_beh, cols["canali_11"]))
        pen_map = {r["Canale"]: r["Penetrazione (%)"]
                   for r in _safe_records(df_pen[["Canale", "Penetrazione (%)"]])}

        # Utilità
        df_util = _norm_canale(kpi_utilita(df_beh, canali_util))
        val_col = [c for c in df_util.columns if c != "Canale"][0]
        util_map = {r["Canale"]: r[val_col]
                    for r in _safe_records(df_util[["Canale", val_col]])}

        # Gap per canale
        tutti = []
        for canale, util in util_map.items():
            if util is None:
                continue
            pen = pen_map.get(canale, 0.0)
            gap = round(float(util) - (float(pen) / 10.0), 2)
            tutti.append({
                "canale":           canale,
                "utilita_media":    round(float(util), 2),
                "penetrazione_%":   round(float(pen), 1),
                "gap_score":        gap,
                "tipo":             (
                    "OPPORTUNITA'" if gap > 1.5
                    else "FRIZIONE" if gap < -1.5
                    else "bilanciato"
                ),
            })

        tutti.sort(key=lambda x: x["gap_score"], reverse=True)
        opportunita = [c for c in tutti if c["tipo"] == "OPPORTUNITA'"]
        frizioni    = [c for c in tutti if c["tipo"] == "FRIZIONE"]

        return {
            "n_hcp":             len(df_beh),
            "target_filtro":     target if target else "tutti i segmenti",
            "tutti_canali":      tutti,
            "opportunita_nascoste": opportunita,
            "frizioni":          frizioni,
            "n_opportunita":     len(opportunita),
            "n_frizioni":        len(frizioni),
            "interpretazione": (
                "Gap > +1.5: canale apprezzato ma sottoutilizzato → opportunità di investimento. "
                "Gap < -1.5: canale molto usato ma poco apprezzato → rischio saturazione/fastidio. "
                "Gap vicino a 0: penetrazione e utilità bilanciate."
            ),
        }
    except Exception as e:
        return {"errore": f"Errore calcolo gap: {e}"}


# ── Tool 7: Simulazione what-if penetrazione canale ──────────────────────────

def tool_whatif_penetrazione(canale: str, delta_pp: float, target: list = None) -> dict:
    """
    Simulazione what-if: cosa succederebbe se la penetrazione del canale X
    aumentasse di delta_pp punti percentuali?
    Stima: HCP aggiuntivi raggiunti + stima ricordo incrementale basata sul tasso attuale.
    NOTA: è una proiezione lineare, non una previsione causale.
    """
    target   = target or []
    delta_pp = float(delta_pp)

    if delta_pp <= 0:
        return {"errore": "delta_pp deve essere un valore positivo (es. 10 = +10 pp)."}
    if delta_pp > 50:
        return {"errore": "delta_pp non può superare 50 punti percentuali per scenario realistico."}

    data    = get_data()
    cols    = data["columns"]
    df_beh  = _filtra(data["df_beh"],  cols.get("col_target"), target)
    df_perf = _filtra(data["df_perf"], cols.get("col_target"), target)

    n_hcp = len(df_beh)
    if n_hcp < 5:
        return {"errore": f"Campione troppo piccolo ({n_hcp} HCP)."}

    # Penetrazione attuale
    df_pen = _norm_canale(kpi_penetrazione(df_beh, cols["canali_11"]))
    match  = df_pen[df_pen["Canale"].str.lower() == canale.lower()]
    if match.empty:
        # Cerca match parziale
        match = df_pen[df_pen["Canale"].str.lower().str.contains(canale.lower(), na=False)]

    if match.empty:
        canali_disponibili = df_pen["Canale"].tolist()
        return {
            "errore": f"Canale '{canale}' non trovato.",
            "canali_disponibili": canali_disponibili,
        }

    canale_nome  = match.iloc[0]["Canale"]
    pen_attuale  = float(match.iloc[0]["Penetrazione (%)"])
    pen_simulata = min(100.0, pen_attuale + delta_pp)
    hcp_attuali  = round(pen_attuale / 100.0 * n_hcp)
    hcp_simulati = round(pen_simulata / 100.0 * n_hcp)
    hcp_delta    = hcp_simulati - hcp_attuali

    # Stima ricordo incrementale: usa il tasso di ricordo attuale del canale
    recall_delta_str = None
    try:
        df_ric   = _norm_canale(kpi_ricordo_canali(df_perf, cols["canali_perf"]))
        ric_match = df_ric[df_ric["Canale"].str.lower() == canale_nome.lower()]
        if not ric_match.empty:
            tasso_ric    = float(ric_match.iloc[0]["Ricordo (%)"])
            recall_delta = round(hcp_delta * tasso_ric / 100)
            recall_delta_str = (
                f"+{recall_delta} HCP in più che ricorderebbero il messaggio "
                f"(tasso ricordo attuale {tasso_ric:.1f}%)"
            )
    except Exception:
        pass

    # Valutabilità: gap vs utilità percepita
    feasibility = "Non valutabile (utilità non disponibile)"
    try:
        canali_util = cols.get("canali_utilita", [])
        if canali_util:
            df_util   = _norm_canale(kpi_utilita(df_beh, canali_util))
            val_col   = [c for c in df_util.columns if c != "Canale"][0]
            util_match = df_util[df_util["Canale"].str.lower() == canale_nome.lower()]
            if not util_match.empty:
                util_val = float(util_match.iloc[0][val_col])
                if util_val >= 5.5:
                    feasibility = f"Alta fattibilità: utilità percepita elevata ({util_val:.1f}/7) → i medici accoglierebbero positivamente l'incremento"
                elif util_val >= 4.0:
                    feasibility = f"Fattibilità media: utilità percepita moderata ({util_val:.1f}/7) → incremento possibile ma richiede qualità del contenuto"
                else:
                    feasibility = f"Fattibilità bassa: utilità percepita scarsa ({util_val:.1f}/7) → incrementare la penetrazione rischia di creare saturazione"
    except Exception:
        pass

    return {
        "canale":                canale_nome,
        "target_filtro":         target if target else "tutti i segmenti",
        "n_hcp_totale":          n_hcp,
        "scenario":              f"+{delta_pp:.0f} punti percentuali di penetrazione",
        "penetrazione_attuale_%": round(pen_attuale, 1),
        "penetrazione_simulata_%": round(pen_simulata, 1),
        "hcp_attuali":           hcp_attuali,
        "hcp_simulati":          hcp_simulati,
        "hcp_aggiuntivi_stimati": hcp_delta,
        "stima_ricordo_incrementale": recall_delta_str,
        "fattibilita":           feasibility,
        "avvertenza": (
            "SIMULAZIONE LINEARE — non incorpora effetti di saturazione, "
            "budget, stagionalità o dinamiche competitive. "
            "Usare come orientamento strategico, non come previsione."
        ),
    }


# ── Schema tools (formato Ollama / OpenAI) ───────────────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_comportamento_kpi",
            "description": (
                "Restituisce i KPI principali di comportamento HCP: penetrazione, ricordo e ingaggio "
                "per canale. Usa questo tool come punto di partenza per qualsiasi analisi "
                "su canali, segmenti medici, copertura o memoria del messaggio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Filtro specializzazioni mediche. "
                            "Esempi: ['Cardiologo'], ['Oncologo', 'Pneumologo']. "
                            "Lista vuota o omessa = tutti i medici."
                        ),
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Numero di canali da restituire per ogni KPI (default 8).",
                        "default": 8,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_funnel_hcp",
            "description": (
                "Calcola il funnel per canale: Penetrazione → Ricordo → Ingaggio, "
                "con i tassi di conversione a ogni step. "
                "Usa quando l'utente chiede dove si perdono i medici, "
                "quale canale converte meglio o qual è la 'dispersione' del messaggio."
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
            "name": "get_ocv_mix",
            "description": (
                "Calcola le combinazioni di canali che massimizzano l'OCV (Omnichannel Value). "
                "Usa quando l'utente chiede la strategia multicanale ottimale, "
                "quale mix di canali usare insieme, come aumentare il ricordo o ridurre la saturazione."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                    "max_combo": {
                        "type": "integer",
                        "description": "Numero massimo di canali nella combinazione (2, 3 o 4). Default 3.",
                        "default": 3,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_specializzazioni",
            "description": (
                "Lista le specializzazioni mediche disponibili nel dataset con il numero di HCP per ciascuna. "
                "Usa come PRIMO passo se l'utente non specifica il segmento medico "
                "o chiede su quale target lavorare."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_utilita_canali",
            "description": (
                "Utilità media percepita per canale (Q6, scala 1–7). "
                "Mostra quanto i medici trovano utili i canali indipendentemente dal loro uso attuale. "
                "Usa per domande su preferenze, canali apprezzati, quality of channel, Q6."
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
            "name": "get_gap_analisi",
            "description": (
                "Analisi gap Utilità–Penetrazione per canale. "
                "Identifica opportunità nascoste (alta utilità, bassa penetrazione) e frizioni "
                "(alta penetrazione, bassa utilità percepita = rischio saturazione). "
                "Usa per domande su potenziale non espresso, canali da sviluppare, "
                "dove investire, rischio di over-communication."
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
            "name": "whatif_penetrazione",
            "description": (
                "Simulazione what-if: stima quanti HCP aggiuntivi verrebbero raggiunti "
                "se la penetrazione di un canale aumentasse di X punti percentuali. "
                "Include stima del ricordo incrementale e valutazione di fattibilità "
                "basata sull'utilità percepita. "
                "Usa per domande 'cosa succederebbe se', 'simula', 'ipotizza', 'what if', "
                "'se aumentassimo', 'e se investissimo di più su'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "canale": {
                        "type": "string",
                        "description": "Nome del canale (es. 'ISF faccia a faccia', 'Email da ISF', 'Webinar').",
                    },
                    "delta_pp": {
                        "type": "number",
                        "description": "Incremento in punti percentuali di penetrazione (es. 10 = +10pp). Range: 1–50.",
                    },
                    "target": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filtro specializzazioni mediche. Lista vuota = tutti.",
                    },
                },
                "required": ["canale", "delta_pp"],
            },
        },
    },
]

# ── Registry locale: nome → funzione Python ──────────────────────────────────

TOOL_REGISTRY = {
    "get_comportamento_kpi":  tool_get_comportamento_kpi,
    "get_funnel_hcp":         tool_get_funnel_hcp,
    "get_ocv_mix":            tool_get_ocv_mix,
    "list_specializzazioni":  tool_list_specializzazioni,
    "get_utilita_canali":     tool_get_utilita_canali,
    "get_gap_analisi":        tool_get_gap_analisi,
    "whatif_penetrazione":    tool_whatif_penetrazione,
}
