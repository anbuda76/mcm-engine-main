import pandas as pd

def kpi_ricordo_competitor(df_perf, competitor_list, col_ricordo, canali_perf):
    """
    KPI Ricordo della comunicazione per ciascun competitor (Q10).

    OUTPUT:
        DataFrame con:
        Azienda | Canale | Medici esposti | Ricorda (#) | Ricorda (%)
    """

    results = []

    for comp in competitor_list:

        # filtra i medici che hanno ricevuto comunicazione dal competitor
        df_c = df_perf[df_perf["Azienda"] == comp]

        if df_c.empty:
            continue

        # ricordo totale competitor
        tot_medici = len(df_c)
        ricorda_tot = (df_c[col_ricordo] == 1).sum()

        results.append({
            "Azienda": comp,
            "Canale": "TOTALE AZIENDA",
            "Medici esposti": tot_medici,
            "Ricorda (#)": int(ricorda_tot),
            "Ricorda (%)": round(ricorda_tot / tot_medici * 100, 1)
        })

        # ricordo per singolo canale
        for c in canali_perf:
            if c not in df_c.columns:
                continue

            esposti = df_c[df_c[c].notna()]
            n_esposti = len(esposti)

            if n_esposti == 0:
                continue

            ricorda = (esposti[col_ricordo] == 1).sum()
            pct = round((ricorda / n_esposti * 100), 1)

            results.append({
                "Azienda": comp,
                "Canale": c,
                "Medici esposti": n_esposti,
                "Ricorda (#)": int(ricorda),
                "Ricorda (%)": pct
            })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)

    # Ordine: prima per azienda, poi ricordo decrescente
    df_out = df_out.sort_values(
        ["Azienda", "Canale", "Ricorda (%)"],
        ascending=[True, True, False]
    ).reset_index(drop=True)

    return df_out
