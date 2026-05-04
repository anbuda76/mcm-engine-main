import pandas as pd

def kpi_propensione_competitor(df_perf, competitor_list, col_prop):
    """
    KPI PROPENSIONE COMPETITOR (Q16, scala 1-10)

    Per ogni competitor calcola:
    - Media propensione
    - % top box 9-10
    - % medio 7-8
    - % basso 1-6
    - N rispondenti

    OUTPUT:
        DataFrame con righe per competitor
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
                "Media propensione": None,
                "Top box 9-10 (%)": None,
                "Medio 7-8 (%)": None,
                "Basso 1-6 (%)": None,
                "N rispondenti": 0
            })
            continue

        mean_val = round(valid.mean(), 2)

        pct_top = round((valid >= 9).mean() * 100, 1)
        pct_mid = round(valid.between(7, 8).mean() * 100, 1)
        pct_low = round((valid <= 6).mean() * 100, 1)

        results.append({
            "Azienda": comp,
            "Media propensione": mean_val,
            "Top box 9-10 (%)": pct_top,
            "Medio 7-8 (%)": pct_mid,
            "Basso 1-6 (%)": pct_low,
            "N rispondenti": len(valid)
        })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)

    # Ordina competitor per media propensione decrescente
    df_out = df_out.sort_values(
        "Media propensione",
        ascending=False
    ).reset_index(drop=True)

    return df_out
