import pandas as pd

def kpi_nps_mercato(df_market, col_prop="Q16"):
    """
    NPS del mercato su Q16.
    """

    valid = df_market[col_prop].dropna()

    if valid.empty:
        return {
            "Mercato": "Totale",
            "Promoters (%)": None,
            "Passives (%)": None,
            "Detractors (%)": None,
            "NPS": None,
            "N rispondenti": 0
        }

    promoters = (valid >= 9).mean() * 100
    passives = valid.between(7, 8).mean() * 100
    detractors = (valid <= 6).mean() * 100

    nps = promoters - detractors

    return {
        "Mercato": "Totale",
        "Promoters (%)": round(promoters, 1),
        "Passives (%)": round(passives, 1),
        "Detractors (%)": round(detractors, 1),
        "NPS": round(nps, 1),
        "N rispondenti": len(valid)
    }
