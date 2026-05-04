import pandas as pd

def kpi_ricordo_canali(df, canali_perf):
    """
    Calcola il ricordo della comunicazione per ogni canale Q9.
    df = Performance Channel filtrato per target
    canali_perf = lista colonne Q9 rilevate dal detect_columns
    """

    risultati = []

    for col in canali_perf:
        # medici che hanno ricevuto quel canale
        df_canale = df[df[col].notna()]

        # consideriamo solo le risposte valide 1-2
        df_validi = df_canale[df_canale["Q10_Ricorda Comunicazione"].isin([1, 2])]

        if df_validi.empty:
            ricorda = 0
            non_ricorda = 0
        else:
            ricorda = (df_validi["Q10_Ricorda Comunicazione"] == 1).mean() * 100
            non_ricorda = (df_validi["Q10_Ricorda Comunicazione"] == 2).mean() * 100

        risultati.append({
            "Canale": col,
            "Ricordo (%)": round(ricorda, 1),
            "Non ricordo (%)": round(non_ricorda, 1)
        })

    if not risultati:
        return pd.DataFrame(columns=["Canale", "Ricordo (%)", "Non ricordo (%)"])

    df_out = pd.DataFrame(risultati)
    return df_out.sort_values("Ricordo (%)", ascending=False).reset_index(drop=True)
