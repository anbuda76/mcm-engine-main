import pandas as pd

def kpi_ricordo_mercato(df_market, col_ricordo, canali_perf):
    """
    Ricordo totale e per canale del mercato.
    """

    if df_market.empty:
        return pd.DataFrame()

    results = []

    tot = len(df_market)
    ricorda = (df_market[col_ricordo] == 1).sum()

    # totale mercato
    results.append({
        "Mercato": "Totale",
        "Canale": "TOTALE MERCATO",
        "Medici esposti": tot,
        "Ricorda (#)": int(ricorda),
        "Ricorda (%)": round((ricorda / tot) * 100, 1)
    })

    # per singolo canale
    for c in canali_perf:
        esposti = df_market[df_market[c].notna()]
        n_esposti = len(esposti)

        if n_esposti == 0:
            continue

        ric = (esposti[col_ricordo] == 1).sum()

        results.append({
            "Mercato": "Totale",
            "Canale": c,
            "Medici esposti": n_esposti,
            "Ricorda (#)": int(ric),
            "Ricorda (%)": round((ric / n_esposti) * 100, 1)
        })

    df_out = pd.DataFrame(results)
    return df_out.sort_values(["Canale"]).reset_index(drop=True)
