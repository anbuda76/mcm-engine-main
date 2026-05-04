import pandas as pd
import numpy as np

# ------------------------------------------------------------
# SAFE HELPERS
# ------------------------------------------------------------

def safe_mean(df, col):
    """Ritorna media sicura: se df è vuoto o colonna mancante → NaN."""
    if df is None or not isinstance(df, pd.DataFrame):
        return np.nan
    if df.empty or col not in df.columns:
        return np.nan
    try:
        return df[col].astype(float).mean()
    except:
        return np.nan

def safe_value(df, col):
    """Ritorna valore singolo da df → se manca: NaN."""
    if df is None or not isinstance(df, pd.DataFrame):
        return np.nan
    if df.empty or col not in df.columns:
        return np.nan
    try:
        return df[col].iloc[0]
    except:
        return np.nan


# ------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------

def compare_all_kpi(
    df_pen_az, df_ric_az, df_ing_az, df_prop_az, df_nps_az,
    df_pen_comp, df_ric_comp, df_ing_comp, df_prop_comp, df_nps_comp,
    df_pen_merc, df_ric_merc, df_ing_merc, df_prop_merc, df_nps_merc
):

    results = []

    # ------------------------------------------------------------
    # 1) Penetrazione (%)
    # ------------------------------------------------------------
    results.append({
        "KPI": "Penetrazione (%)",
        "Azienda Focus": safe_mean(df_pen_az, "Penetrazione (%)"),
        "Competitor": safe_mean(df_pen_comp, "Penetrazione (%)"),
        "Mercato": safe_mean(df_pen_merc, "Penetrazione (%)")
    })

    # ------------------------------------------------------------
    # 2) Ricordo (%)
    # ------------------------------------------------------------
    results.append({
        "KPI": "Ricordo (%)",
        "Azienda Focus": safe_mean(df_ric_az, "Ricorda (%)"),
        "Competitor": safe_mean(df_ric_comp, "Ricorda (%)"),
        "Mercato": safe_mean(df_ric_merc, "Ricorda (%)")
    })

    # ------------------------------------------------------------
    # 3) Ingaggio (%)
    # ------------------------------------------------------------
    results.append({
        "KPI": "Ingaggio (%)",
        "Azienda Focus": safe_mean(df_ing_az, "Ingaggio totale (%)"),
        "Competitor": safe_mean(df_ing_comp, "Ingaggio totale (%)"),
        "Mercato": safe_mean(df_ing_merc, "Ingaggio totale (%)")
    })

    # ------------------------------------------------------------
    # 4) Propensione media
    # ------------------------------------------------------------
    results.append({
        "KPI": "Propensione media",
        "Azienda Focus": safe_value(df_prop_az, "Media propensione"),
        "Competitor": safe_value(df_prop_comp, "Media propensione"),
        "Mercato": safe_value(df_prop_merc, "Media propensione")
    })

    # ------------------------------------------------------------
    # 5) NPS
    # ------------------------------------------------------------
    results.append({
        "KPI": "NPS",
        "Azienda Focus": safe_value(df_nps_az, "NPS"),
        "Competitor": safe_value(df_nps_comp, "NPS"),
        "Mercato": safe_value(df_nps_merc, "NPS")
    })

    return pd.DataFrame(results)
