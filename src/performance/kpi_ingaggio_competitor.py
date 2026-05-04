import pandas as pd

def kpi_ingaggio_competitor(df_perf, competitor_list, col_ingaggio, canali_perf):
    """
    KPI INGAGGIO COMPETITOR (Q13)

    Calcola, per ciascun competitor:
    - Ingaggio totale
    - Ingaggio per singolo canale
    - Breakdown % per tipo di comportamento (1,2,3)

    OUTPUT:
        DataFrame con:
        Azienda | Canale | Medici esposti | Ingaggio (%) |
        Condivisione (%) | Approfondimento (%) | No azione (%)
    """

    results = []

    for comp in competitor_list:

        # Filtra i medici esposti al competitor
        df_c = df_perf[df_perf["Azienda"] == comp]

        if df_c.empty:
            continue

        # ---- Ingaggio totale competitor ----
        tot = len(df_c)

        pct_share = (df_c[col_ingaggio] == 1).mean() * 100
        pct_deep = (df_c[col_ingaggio] == 2).mean() * 100
        pct_none = (df_c[col_ingaggio] == 3).mean() * 100

        pct_ingaggio = pct_share + pct_deep

        results.append({
            "Azienda": comp,
            "Canale": "TOTALE AZIENDA",
            "Medici esposti": tot,
            "Ingaggio (%)": round(pct_ingaggio, 1),
            "Condivisione (%)": round(pct_share, 1),
            "Approfondimento (%)": round(pct_deep, 1),
            "No azione (%)": round(pct_none, 1)
        })

        # ---- Ingaggio per singolo canale ----
        for c in canali_perf:
            if c not in df_c.columns:
                continue

            esposti = df_c[df_c[c].notna()]
            n_esposti = len(esposti)

            if n_esposti == 0:
                continue

            pct_s = (esposti[col_ingaggio] == 1).mean() * 100
            pct_d = (esposti[col_ingaggio] == 2).mean() * 100
            pct_n = (esposti[col_ingaggio] == 3).mean() * 100

            pct_ing = pct_s + pct_d

            results.append({
                "Azienda": comp,
                "Canale": c,
                "Medici esposti": n_esposti,
                "Ingaggio (%)": round(pct_ing, 1),
                "Condivisione (%)": round(pct_s, 1),
                "Approfondimento (%)": round(pct_d, 1),
                "No azione (%)": round(pct_n, 1)
            })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)

    # Ordine: prima competitor, poi ingaggio decrescente
    df_out = df_out.sort_values(
        ["Azienda", "Canale", "Ingaggio (%)"],
        ascending=[True, True, False]
    ).reset_index(drop=True)

    return df_out
