import pandas as pd

def kpi_ricordo_azienda(df_azienda, col_ricordo, canali_perf):
    """
    Calcola il ricordo della comunicazione per una azienda:

    - Ricordo totale dell’azienda
    - Ricordo per singolo canale (Q9_x → Q10 pairing)

    INPUT:
        df_azienda   → df filtrato solo sull’azienda focus
        col_ricordo  → colonna Q10
        canali_perf  → lista Q9_x

    OUTPUT:
        DataFrame con:
        Azienda | Canale | Medici esposti | Ricorda (%) | Ricorda (#)
    """

    if df_azienda.empty:
        return pd.DataFrame(columns=[
            "Azienda", "Canale", "Medici esposti", "Ricorda (#)", "Ricorda (%)"
        ])

    azienda = df_azienda["Azienda"].iloc[0]

    results = []

    # --- Ricordo totale generale ---
    tot_medici = len(df_azienda)
    ricorda_tot = (df_azienda[col_ricordo] == 1).sum()

    results.append({
        "Azienda": azienda,
        "Canale": "TOTALE AZIENDA",
        "Medici esposti": tot_medici,
        "Ricorda (#)": int(ricorda_tot),
        "Ricorda (%)": round(ricorda_tot / tot_medici * 100, 1)
    })

    # --- Ricordo per singolo canale ---
    for c in canali_perf:
        if c not in df_azienda.columns:
            continue

        # medici che hanno ricevuto info tramite questo canale
        esposti = df_azienda[df_azienda[c].notna()]

        n_esposti = len(esposti)
        if n_esposti == 0:
            continue

        # ricordo (Q10=1) tra gli esposti
        ricorda = (esposti[col_ricordo] == 1).sum()
        pct = round((ricorda / n_esposti * 100), 1)

        results.append({
            "Azienda": azienda,
            "Canale": c,
            "Medici esposti": int(n_esposti),
            "Ricorda (#)": int(ricorda),
            "Ricorda (%)": pct
        })

    df_out = pd.DataFrame(results)

    # ordina: prima record totale, poi per canale in ordine disc.
    df_out = df_out.sort_values(
        ["Canale", "Ricorda (%)"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return df_out
