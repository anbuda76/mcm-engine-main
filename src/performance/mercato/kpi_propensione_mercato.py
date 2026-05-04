import pandas as pd

def kpi_propensione_mercato(df_market, col_prop):
    """
    Propensione media e distribuzione (Q16) del mercato.
    """

    valid = df_market[col_prop].dropna()

    if valid.empty:
        return {
            "Mercato": "Totale",
            "Media propensione": None,
            "Top box 9-10 (%)": None,
            "Medio 7-8 (%)": None,
            "Basso 1-6 (%)": None,
            "N rispondenti": 0
        }

    mean_val = round(valid.mean(), 2)
    pct_top = (valid >= 9).mean() * 100
    pct_mid = valid.between(7, 8).mean() * 100
    pct_low = (valid <= 6).mean() * 100

    return {
        "Mercato": "Totale",
        "Media propensione": mean_val,
        "Top box 9-10 (%)": round(pct_top, 1),
        "Medio 7-8 (%)": round(pct_mid, 1),
        "Basso 1-6 (%)": round(pct_low, 1),
        "N rispondenti": len(valid)
    }
