import pandas as pd
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP

def normalizza_canale(nome):
    return CANALI_MAP.get(nome, None)

def kpi_penetrazione(df_beh, canali_11):
    """
    Penetrazione corretta dei canali Q11a:
    - Qualsiasi testo = canale ricevuto (1)
    - NaN o stringa vuota = non ricevuto (0)
    """

    if df_beh.empty:
        return pd.DataFrame()

    totale_medici = len(df_beh)

    df_bin = df_beh.copy()

    # Trasformiamo le colonne Q11a in valori binari 1/0
    for c in canali_11:
        df_bin[c] = df_bin[c].apply(
            lambda x: 1 if pd.notnull(x) and str(x).strip() != "" else 0
        )

    # Calcolo penetrazione percentuale
    pen = (df_bin[canali_11].sum() / totale_medici * 100).round(1)

    # Costruisco il dataframe finale
    df_out = (
        pen.reset_index()
           .rename(columns={"index": "Canale", 0: "Penetrazione (%)"})
           .sort_values("Penetrazione (%)", ascending=False)
    )

    # 🔥 QUI VA INSERITA LA NORMALIZZAZIONE
    df_out["Canale_std"] = df_out["Canale"].apply(normalizza_canale)

    return df_out
