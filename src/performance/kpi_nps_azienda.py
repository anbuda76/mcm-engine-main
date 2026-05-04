import pandas as pd

def kpi_nps_azienda(df_azienda, col_prop="Q16"):
    """
    KPI NPS aziendale basato su Q16 (probabilità di consiglio 1-10).

    OUTPUT:
        {
            "Azienda": ...,
            "Promoters (%)": ...,
            "Passives (%)": ...,
            "Detractors (%)": ...,
            "NPS": ...,
            "Media propensione": ...,
            "N rispondenti": ...
        }
    """

    if df_azienda.empty:
        return {
            "Azienda": None,
            "Promoters (%)": None,
            "Passives (%)": None,
            "Detractors (%)": None,
            "NPS": None,
            "Media propensione": None,
            "N rispondenti": 0
        }

    azienda = df_azienda["Azienda"].iloc[0]

    # valori validi
    valid = df_azienda[col_prop].dropna()

    if valid.empty:
        return {
            "Azienda": azienda,
            "Promoters (%)": None,
            "Passives (%)": None,
            "Detractors (%)": None,
            "NPS": None,
            "Media propensione": None,
            "N rispondenti": 0
        }

    promoters = (valid >= 9).mean() * 100
    passives = (valid.between(7, 8)).mean() * 100
    detractors = (valid <= 6).mean() * 100

    nps = promoters - detractors
    media_prop = round(valid.mean(), 2)

    return {
        "Azienda": azienda,
        "Promoters (%)": round(promoters, 1),
        "Passives (%)": round(passives, 1),
        "Detractors (%)": round(detractors, 1),
        "NPS": round(nps, 1),
        "Media propensione": media_prop,
        "N rispondenti": len(valid)
    }
