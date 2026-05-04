import pandas as pd

def kpi_propensione_canali(df, canali_perf):
    """
    Calcola la probabilità media di consiglio (Q16) per ciascun canale Q9.
    Si considerano solo i medici che:
    - hanno ricevuto il canale (colonna Q9 non NaN)
    - hanno fornito una valutazione valida a Q16 (1-10)
    """

    risultati = []

    for col in canali_perf:

        # Medici che hanno ricevuto quel canale
        df_canale = df[df[col].notna()]

        # Risposte valide a Q16 (da 1 a 10)
        df_validi = df_canale[
            df_canale["Q16 probabilita di consiglio"].between(1, 10, inclusive="both")
        ]

        if df_validi.empty:
            prop_media = 0
            n_medici = 0
        else:
            prop_media = df_validi["Q16 probabilita di consiglio"].mean()
            n_medici = len(df_validi)

        risultati.append({
            "Canale": col,
            "N medici valutanti": n_medici,
            "Probabilità media consiglio": round(prop_media, 1)
        })

    if not risultati:
        return pd.DataFrame(columns=["Canale", "N medici valutanti", "Probabilità media consiglio"])

    df_out = pd.DataFrame(risultati)

    # Ordina i canali dal più consigliato al meno
    df_out = df_out.sort_values(by="Probabilità media consiglio", ascending=False)

    return df_out.reset_index(drop=True)
