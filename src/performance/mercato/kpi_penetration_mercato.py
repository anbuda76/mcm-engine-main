import pandas as pd

def kpi_penetration_mercato(df_market, canali_perf):
    """
    Penetrazione del mercato per ciascun canale Q9.
    """

    if df_market.empty:
        return pd.DataFrame()

    tot = len(df_market)

    results = []

    for c in canali_perf:
        if c not in df_market.columns:
            continue

        raggiunti = df_market[c].notna().sum()
        pct = round((raggiunti / tot) * 100, 1)

        results.append({
            "Mercato": "Totale",
            "Canale": c,
            "Medici raggiunti": int(raggiunti),
            "Totale medici": tot,
            "Penetrazione (%)": pct
        })

    df_out = pd.DataFrame(results)
    return df_out.sort_values("Penetrazione (%)", ascending=False).reset_index(drop=True)
