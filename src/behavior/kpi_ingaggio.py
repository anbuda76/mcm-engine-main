import pandas as pd

def kpi_ingaggio_canali(df, canali_perf):
    """
    Calcola l'ingaggio del medico per ciascun canale Q9 basato su Q13_1.
    Q13_1:
        1 = condiviso
        2 = cercato ulteriori info
        3 = nulla
    """

    risultati = []

    for col in canali_perf:

        # Medici che hanno ricevuto quel canale
        df_canale = df[df[col].notna()]

        # Consideriamo solo risposte valide
        df_validi = df_canale[df_canale["Q13_1 Le informazioni erano Rilevanti"].isin([1, 2, 3])]

        if df_validi.empty:
            condiviso = 0
            approfondito = 0
            nulla = 0
        else:
            condiviso = (df_validi["Q13_1 Le informazioni erano Rilevanti"] == 1).mean() * 100
            approfondito = (df_validi["Q13_1 Le informazioni erano Rilevanti"] == 2).mean() * 100
            nulla = (df_validi["Q13_1 Le informazioni erano Rilevanti"] == 3).mean() * 100

        ingaggio_totale = condiviso + approfondito

        risultati.append({
            "Canale": col,
            "Condiviso (%)": round(condiviso, 1),
            "Approfondito (%)": round(approfondito, 1),
            "Nulla (%)": round(nulla, 1),
            "Ingaggio totale (%)": round(ingaggio_totale, 1)
        })

    if not risultati:
        empty = pd.DataFrame(columns=[
            "Canale", "Condiviso (%)", "Approfondito (%)", "Nulla (%)", "Ingaggio totale (%)"
        ])
        empty.attrs["media_ingaggio"] = 0.0
        return empty

    df_out = pd.DataFrame(risultati)

    # 1️⃣ Ordina in base all’ingaggio
    df_out = df_out.sort_values(by="Ingaggio totale (%)", ascending=False)

    # 2️⃣ Calcola la media complessiva dell’ingaggio
    media_ingaggio = df_out["Ingaggio totale (%)"].mean().round(1)

    # Aggiungiamo un attributo al dataframe (comodissimo in Python)
    df_out.attrs["media_ingaggio"] = media_ingaggio

    return df_out
