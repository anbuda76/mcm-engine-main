import pandas as pd

def kpi_penetrazione_azienda(df_azienda, canali_perf):
    """
    Calcola la penetrazione dei canali (Q9) per una azienda specifica.

    DEFINIZIONE:
    Penetrazione = % medici che hanno ricevuto almeno una comunicazione
    tramite quel canale da quella azienda.

    INPUT:
    - df_azienda: subset del df_perf filtrato SOLO per l'azienda focus
    - canali_perf: lista colonne Q9 (rilevate dal loader)

    OUTPUT:
    - DataFrame con:
        Azienda | Canale | Medici raggiunti | Totale medici | Penetrazione (%)
    """

    if df_azienda.empty:
        return pd.DataFrame(columns=[
            "Azienda", "Canale", "Medici raggiunti", "Totale medici", "Penetrazione (%)"
        ])

    azienda = df_azienda["Azienda"].iloc[0]
    totale_medici = len(df_azienda)

    results = []

    for c in canali_perf:
        if c not in df_azienda.columns:
            continue

        # medico raggiunto = cella non vuota
        raggiunti = df_azienda[c].notna().sum()

        pct = round((raggiunti / totale_medici * 100), 1) if totale_medici > 0 else 0

        results.append({
            "Azienda": azienda,
            "Canale": c,
            "Medici raggiunti": int(raggiunti),
            "Totale medici": int(totale_medici),
            "Penetrazione (%)": pct
        })

    df_out = pd.DataFrame(results)

    # Ordina dal canale con maggiore penetrazione
    df_out = df_out.sort_values("Penetrazione (%)", ascending=False).reset_index(drop=True)

    return df_out
