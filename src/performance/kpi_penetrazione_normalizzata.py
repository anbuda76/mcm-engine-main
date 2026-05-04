import pandas as pd

def kpi_penetrazione_normalizzata(df_perf, canali_perf):
    """
    KPI: Penetrazione normalizzata dei canali su base 10 medici.

    DEFINIZIONE:
    Per ogni azienda:
        Valore = (Medici esposti al canale / Totale medici dell’azienda) * 10

    COSA RESTITUISCE:
        Un DataFrame a forma larga:
        Azienda | Canale1 | Canale2 | ... | CanaleN
        con valori 0–10 (interi o decimali).

    ARGOMENTI:
        df_perf     → dataframe performance filtrato sul target medico
        canali_perf → lista colonne dei canali Q9 (rilevata dal loader)

    OUTPUT:
        df_out → tabella normalizzata per azienda
    """

    # Lista aziende presenti nel data
    aziende = sorted(df_perf["Azienda"].unique())

    rows = []

    for az in aziende:
        df_az = df_perf[df_perf["Azienda"] == az]

        if df_az.empty:
            continue

        tot_medici = len(df_az)

        row = {"Azienda": az}

        # Calcolo per ogni canale
        for c in canali_perf:

            if c not in df_az.columns:
                row[c] = 0
                continue

            # Medici esposti al canale (notna() = ha ricevuto comunicazione)
            esposti = df_az[c].notna().sum()

            # Normalizzazione su 10
            val = (esposti / tot_medici) * 10 if tot_medici > 0 else 0

            row[c] = round(val, 1)

        rows.append(row)

    # Tabella finale
    df_out = pd.DataFrame(rows)

    # Ordina per azienda in modo crescente
    df_out = df_out.sort_values("Azienda").reset_index(drop=True)

    return df_out
