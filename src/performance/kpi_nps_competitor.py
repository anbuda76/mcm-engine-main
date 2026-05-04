import pandas as pd

def kpi_nps_competitor(df_perf, competitor_list, col_prop="Q16"):
    """
    Calcola l'NPS (Net Promoter Score) per ciascun competitor
    sulla base della probabilità di consiglio (Q16).

    OUTPUT:
        DataFrame con per ogni competitor:
        Azienda | Promoters (%) | Passives (%) | Detractors (%) | NPS | Media propensione | N rispondenti
    """

    results = []

    for comp in competitor_list:

        df_c = df_perf[df_perf["Azienda"] == comp]

        if df_c.empty:
            continue

        valid = df_c[col_prop].dropna()

        if valid.empty:
            results.append({
                "Azienda": comp,
                "Promoters (%)": None,
                "Passives (%)": None,
                "Detractors (%)": None,
                "NPS": None,
                "Media propensione": None,
                "N rispondenti": 0
            })
            continue

        promoters = (valid >= 9).mean() * 100
        passives = valid.between(7, 8).mean() * 100
        detractors = (valid <= 6).mean() * 100

        nps = promoters - detractors
        media_prop = round(valid.mean(), 2)

        results.append({
            "Azienda": comp,
            "Promoters (%)": round(promoters, 1),
            "Passives (%)": round(passives, 1),
            "Detractors (%)": round(detractors, 1),
            "NPS": round(nps, 1),
            "Media propensione": media_prop,
            "N rispondenti": len(valid)
        })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)

    # Ordina competitor dal migliore al peggiore NPS
    df_out = df_out.sort_values("NPS", ascending=False).reset_index(drop=True)

    return df_out
