import pandas as pd
import itertools
from typing import List, Optional

"""
MCM Engage – OCV Analytics Engine (Production Ready)
---------------------------------------------------
Questo modulo implementa il calcolo standardizzato dell'Orchestration Channel Value (OCV)
secondo il framework MCM Engage.

Il modulo restituisce output ANALITICI + DECISIONALI, pronti per reporting business-oriented.
"""

# --------------------------------------------------
# Utility: classificazione OCV
# --------------------------------------------------

def classify_ocv(ocv_value: float) -> str:
    """Classifica l'OCV secondo standard MCM Engage."""
    if ocv_value >= 20:
        return "High Positive OCV"
    elif ocv_value >= 0:
        return "Low Positive OCV"
    elif ocv_value > -20:
        return "Low Negative OCV"
    else:
        return "High Negative OCV"


def ocv_decision(ocv_class: str) -> str:
    """Traduce la classe OCV in raccomandazione decisionale."""
    mapping = {
        "High Positive OCV": "Scale / Invest",
        "Low Positive OCV": "Test / Optimize",
        "Low Negative OCV": "Monitor",
        "High Negative OCV": "Avoid / Deprioritize"
    }
    return mapping.get(ocv_class, "Undefined")


# --------------------------------------------------
# OCV Δ – Effetto descrittivo macro
# --------------------------------------------------

def ocv_delta(
    df: pd.DataFrame,
    channel_cols: List[str],
    recall_col: str
) -> Optional[dict]:
    """
    Confronto descrittivo tra:
    - esposizione a 1 canale
    - esposizione a >=3 canali

    Ritorna un dizionario KPI-level (non decisionale).
    """
    data = df.copy()
    data["n_channels"] = data[channel_cols].notna().sum(axis=1)

    single = data[data["n_channels"] == 1]
    multi = data[data["n_channels"] >= 3]

    if single.empty or multi.empty:
        return None

    recall_single = (single[recall_col] == 1).mean()
    recall_multi = (multi[recall_col] == 1).mean()

    delta_pct = ((recall_multi - recall_single) / recall_single) * 100

    return {
        "Recall 1 Channel": round(recall_single * 100, 1),
        "Recall ≥3 Channels": round(recall_multi * 100, 1),
        "OCV Delta (%)": round(delta_pct, 1)
    }


# --------------------------------------------------
# Lift Curve – baseline di esposizione
# --------------------------------------------------

def ocv_lift_curve(
    df: pd.DataFrame,
    channel_cols: List[str],
    recall_col: str
) -> pd.DataFrame:
    """
    Curva di riferimento: ricordo del brand in funzione
    del numero di canali ricevuti.
    """
    data = df.copy()
    data["n_channels"] = data[channel_cols].notna().sum(axis=1)

    curve = (
        data.groupby("n_channels")[recall_col]
        .apply(lambda x: (x == 1).mean())
        .reset_index()
    )

    curve.columns = ["N Channels", "Brand Recall"]
    curve["Brand Recall"] = (curve["Brand Recall"] * 100).round(1)

    return curve.sort_values("N Channels")


# --------------------------------------------------
# OCV Mix – Motore principale di orchestrazione
# --------------------------------------------------

def ocv_mix_engine(
    df: pd.DataFrame,
    channel_cols: List[str],
    recall_col: str,
    max_combination: int = 3,
    min_exposed: int = 10
) -> pd.DataFrame:
    """
    Calcola l'OCV per tutte le combinazioni di canali
    fino a max_combination.

    Output: tabella decision-ready.
    """
    data = df.copy()
    data["n_channels"] = data[channel_cols].notna().sum(axis=1)

    results = []

    for k in range(2, max_combination + 1):
        for combo in itertools.combinations(channel_cols, k):
            combo = list(combo)
            mask = data[combo].notna().all(axis=1)
            subset = data[mask]

            n_medici = len(subset)
            if n_medici < min_exposed:
                continue

            recall_combo = (subset[recall_col] == 1).mean()

            recall_singles = []
            for ch in combo:
                recall_singles.append(
                    (data[data[ch].notna()][recall_col] == 1).mean()
                )

            recall_single_avg = sum(recall_singles) / len(recall_singles)

            ocv_value = ((recall_combo - recall_single_avg) / recall_single_avg) * 100
            ocv_value = round(ocv_value, 1)

            ocv_class = classify_ocv(ocv_value)

            results.append({
                "Channel Mix": " + ".join(combo),
                "N Channels": k,
                "N HCP": n_medici,
                "Recall Mix (%)": round(recall_combo * 100, 1),
                "Recall Singles Avg (%)": round(recall_single_avg * 100, 1),
                "OCV (%)": ocv_value,
                "OCV Class": ocv_class,
                "Business Action": ocv_decision(ocv_class)
            })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)
    return df_out.sort_values("OCV (%)", ascending=False).reset_index(drop=True)


# --------------------------------------------------
# KPI sintetico per target
# --------------------------------------------------

def ocv_efficiency_index(df_ocv: pd.DataFrame) -> Optional[dict]:
    """
    KPI sintetico per confronto tra target:
    % mix con OCV positivo.
    """
    if df_ocv.empty:
        return None

    total = len(df_ocv)
    positive = len(df_ocv[df_ocv["OCV (%)"] > 0])

    return {
        "Total Mix Analysed": total,
        "Positive OCV Mix (%)": round((positive / total) * 100, 1)
    }
