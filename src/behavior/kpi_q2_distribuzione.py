import pandas as pd

def kpi_q2_distribuzione(df_beh, q2_cols):
    """
    Calcola la distribuzione percepita della comunicazione delle aziende (Q2).
    - df_beh: dataframe filtrato per target medico
    - q2_cols: lista colonne Q2[1..3]

    Ritorna un dataframe con pesi normalizzati al 100%.
    """

    if df_beh.empty:
        return pd.DataFrame()

    # 1️⃣ Calcolo media grezza per ogni dimensione
    medie = df_beh[q2_cols].mean()

    # 2️⃣ Normalizzazione
    totale = medie.sum()

    if totale == 0:
        return pd.DataFrame()

    distrib_norm = (medie / totale * 100).round(1)

    # 3️⃣ Dataframe finale pulito
    df_out = distrib_norm.reset_index()
    df_out.columns = ["KPI", "Peso (%)"]

    return df_out
