import pandas as pd

def kpi_utilita(df, canali_utilita):
    """
    Calcola l'utilità media percepita (scala 1–7) per ciascun canale.
    
    - Esclude i NaN dal calcolo (non risposta)
    - Mantiene la metrica coerente 1–7
    """

    risultati = []

    for col in canali_utilita:
        if col in df.columns:

            serie = df[col].dropna()

            if len(serie) == 0:
                utilita_media = 0
            else:
                utilita_media = serie.astype(float).mean()

            risultati.append({
                "Canale": col,
                "Utilità media (1-7)": round(utilita_media, 2)
            })

    if not risultati:
        return pd.DataFrame(columns=["Canale", "Utilità media (1-7)"])

    df_out = pd.DataFrame(risultati)

    # Ordiniamo dal più utile al meno utile
    df_out = df_out.sort_values(by="Utilità media (1-7)", ascending=False)

    return df_out.reset_index(drop=True)
