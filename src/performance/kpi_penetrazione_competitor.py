import pandas as pd

def kpi_penetrazione_competitor(df_perf, competitor_list, canali_perf):
    """
    Calcola la penetrazione dei canali Q9 per ciascun competitor selezionato.

    INPUT:
        df_perf          → df Performance filtrato per target medico
        competitor_list  → lista di aziende competitor
        canali_perf      → lista dei canali Q9

    OUTPUT:
        DataFrame con:
        Azienda | Canale | Medici raggiunti | Totale medici | Penetrazione (%)
    """

    results = []

    for competitor in competitor_list:

        # Filtra solo i medici esposti a questo competitor
        df_comp = df_perf[df_perf["Azienda"] == competitor]

        if df_comp.empty:
            continue

        tot = len(df_comp)

        for c in canali_perf:
            if c not in df_comp.columns:
                continue

            raggiunti = df_comp[c].notna().sum()
            pct = round((raggiunti / tot * 100), 1) if tot > 0 else 0

            results.append({
                "Azienda": competitor,
                "Canale": c,
                "Medici raggiunti": int(raggiunti),
                "Totale medici": int(tot),
                "Penetrazione (%)": pct
            })

    if not results:
        return pd.DataFrame()

    df_out = pd.DataFrame(results)

    # Ordiniamo: prima per azienda, poi per penetrazione decrescente
    df_out = df_out.sort_values(
        ["Azienda", "Penetrazione (%)"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return df_out
