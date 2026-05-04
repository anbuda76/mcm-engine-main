import pandas as pd

def kpi_propensione_azienda(df_azienda, col_prop):
    """
    KPI PROPENSIONE AZIENDALE (Q16)

    Misura:
    - Media propensione 1-10
    - % altissima propensione (9-10)
    - % buona propensione (7-8)
    - % bassa propensione (1-6)
    - N rispondenti

    INPUT:
        df_azienda   → df filtrato sull'azienda focus
        col_prop     → colonna Q16

    OUTPUT:
        Dict con statistiche principali
    """

    if df_azienda.empty:
        return {
            "Azienda": None,
            "Media propensione": None,
            "Top box 9-10 (%)": None,
            "Medio 7-8 (%)": None,
            "Basso 1-6 (%)": None,
            "N rispondenti": 0
        }

    azienda = df_azienda["Azienda"].iloc[0]

    # valori validi
    valid = df_azienda[col_prop].dropna()

    if valid.empty:
        return {
            "Azienda": azienda,
            "Media propensione": None,
            "Top box 9-10 (%)": None,
            "Medio 7-8 (%)": None,
            "Basso 1-6 (%)": None,
            "N rispondenti": 0
        }

    mean_val = round(valid.mean(), 2)

    pct_top = round((valid >= 9).mean() * 100, 1)
    pct_mid = round((valid.between(7, 8)).mean() * 100, 1)
    pct_low = round((valid <= 6).mean() * 100, 1)

    return {
        "Azienda": azienda,
        "Media propensione": mean_val,
        "Top box 9-10 (%)": pct_top,
        "Medio 7-8 (%)": pct_mid,
        "Basso 1-6 (%)": pct_low,
        "N rispondenti": len(valid)
    }
