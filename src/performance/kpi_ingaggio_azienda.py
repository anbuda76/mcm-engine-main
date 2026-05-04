import pandas as pd

def kpi_ingaggio_azienda(df_azienda, col_ingaggio, canali_perf):
    """
    KPI INGAGGIO AZIENDALE (Q13)

    Misura:
    - Ingaggio totale azienda (azioni 1 o 2)
    - Ingaggio per singolo canale
    - Breakdown % per tipo di azione

    INPUT:
        df_azienda   → df filtrato solo sull’azienda focus
        col_ingaggio → colonna Q13 (ingaggio)
        canali_perf  → lista Q9_x (canali utilizzati dall’azienda)

    OUTPUT:
        DataFrame con:
            Azienda | Canale | Medici esposti | Ingaggio (%) |
            Condivisione (%) | Approfondimento (%) | No azione (%)
    """

    if df_azienda.empty:
        return pd.DataFrame(columns=[
            "Azienda", "Canale", "Medici esposti",
            "Ingaggio (%)", "Condivisione (%)",
            "Approfondimento (%)", "No azione (%)"
        ])

    azienda = df_azienda["Azienda"].iloc[0]

    results = []

    # --- INGAGGIO TOTALE AZIENDA ---
    tot = len(df_azienda)

    pct_share = (df_azienda[col_ingaggio] == 1).mean() * 100
    pct_deep = (df_azienda[col_ingaggio] == 2).mean() * 100
    pct_none = (df_azienda[col_ingaggio] == 3).mean() * 100

    pct_ingaggio = pct_share + pct_deep

    results.append({
        "Azienda": azienda,
        "Canale": "TOTALE AZIENDA",
        "Medici esposti": tot,
        "Ingaggio (%)": round(pct_ingaggio, 1),
        "Condivisione (%)": round(pct_share, 1),
        "Approfondimento (%)": round(pct_deep, 1),
        "No azione (%)": round(pct_none, 1)
    })

    # --- INGAGGIO PER SINGOLO CANALE ---
    for c in canali_perf:
        if c not in df_azienda.columns:
            continue

        esposti = df_azienda[df_azienda[c].notna()]
        n_esposti = len(esposti)

        if n_esposti == 0:
            continue

        pct_s = (esposti[col_ingaggio] == 1).mean() * 100
        pct_d = (esposti[col_ingaggio] == 2).mean() * 100
        pct_n = (esposti[col_ingaggio] == 3).mean() * 100

        pct_ing = pct_s + pct_d

        results.append({
            "Azienda": azienda,
            "Canale": c,
            "Medici esposti": n_esposti,
            "Ingaggio (%)": round(pct_ing, 1),
            "Condivisione (%)": round(pct_s, 1),
            "Approfondimento (%)": round(pct_d, 1),
            "No azione (%)": round(pct_n, 1)
        })

    df_out = pd.DataFrame(results)

    # Ordina: prima totale azienda, poi canali per ingaggio
    df_out = df_out.sort_values(
        ["Canale", "Ingaggio (%)"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return df_out
