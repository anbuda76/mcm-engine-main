import pandas as pd

def kpi_utilita_fasce(df, canali_utilita):
    """
    Calcola la distribuzione % dei giudizi di utilità per ciascun canale
    sulle 5 fasce richieste:
    - Indispensabile (7)
    - Molto utile (6)
    - Utile (5)
    - Poco utile (3-4)
    - Non utile (1-2)
    """

    risultati = []

    for col in canali_utilita:
        if col not in df.columns:
            continue

        serie = df[col].dropna().astype(float)

        totale_risposte = len(serie)
        if totale_risposte == 0:
            risultati.append({
                "Canale": col,
                "Indispensabile (%)": 0.0,
                "Molto utile (%)": 0.0,
                "Utile (%)": 0.0,
                "Poco utile (%)": 0.0,
                "Non utile (%)": 0.0
            })
            continue

        risultati.append({
            "Canale": col,
            "Indispensabile (%)": round((serie == 7).mean() * 100, 1),
            "Molto utile (%)": round((serie == 6).mean() * 100, 1),
            "Utile (%)": round((serie == 5).mean() * 100, 1),
            "Poco utile (%)": round(((serie == 4) | (serie == 3)).mean() * 100, 1),
            "Non utile (%)": round(((serie == 2) | (serie == 1)).mean() * 100, 1)
        })

    if not risultati:
        return pd.DataFrame(columns=[
            "Canale", "Indispensabile (%)", "Molto utile (%)",
            "Utile (%)", "Poco utile (%)", "Non utile (%)"
        ])

    df_out = pd.DataFrame(risultati)

    # Ordine discendente per "Indispensabile"
    df_out = df_out.sort_values(by="Indispensabile (%)", ascending=False)

    return df_out.reset_index(drop=True)
