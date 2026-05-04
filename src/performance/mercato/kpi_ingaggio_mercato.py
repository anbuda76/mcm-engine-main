import pandas as pd

def kpi_ingaggio_mercato(df_market, col_ingaggio, canali_perf):
    """
    Ingaggio totale e per canale del mercato (Q13).
    """

    if df_market.empty:
        return pd.DataFrame()

    results = []

    tot = len(df_market)

    pct_s = (df_market[col_ingaggio] == 1).mean() * 100
    pct_d = (df_market[col_ingaggio] == 2).mean() * 100
    pct_n = (df_market[col_ingaggio] == 3).mean() * 100

    pct_tot = pct_s + pct_d

    # totale
    results.append({
        "Mercato": "Totale",
        "Canale": "TOTALE MERCATO",
        "Medici esposti": tot,
        "Ingaggio (%)": round(pct_tot, 1),
        "Condivisione (%)": round(pct_s, 1),
        "Approfondimento (%)": round(pct_d, 1),
        "No azione (%)": round(pct_n, 1)
    })

    # per canale
    for c in canali_perf:

        esposti = df_market[df_market[c].notna()]
        n_esposti = len(esposti)

        if n_esposti == 0:
            continue

        pct_s = (esposti[col_ingaggio] == 1).mean() * 100
        pct_d = (esposti[col_ingaggio] == 2).mean() * 100
        pct_n = (esposti[col_ingaggio] == 3).mean() * 100

        pct_tot = pct_s + pct_d

        results.append({
            "Mercato": "Totale",
            "Canale": c,
            "Medici esposti": n_esposti,
            "Ingaggio (%)": round(pct_tot, 1),
            "Condivisione (%)": round(pct_s, 1),
            "Approfondimento (%)": round(pct_d, 1),
            "No azione (%)": round(pct_n, 1)
        })

    df_out = pd.DataFrame(results)
    return df_out.sort_values(["Canale"]).reset_index(drop=True)
