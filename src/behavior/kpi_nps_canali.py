import pandas as pd

def kpi_nps_canali(df_perf, canali_perf, col_prop="Q16"):
    """
    KPI NPS PER SINGOLO CANALE (Q16)

    Per ogni canale misura:
    - % Promoters (9-10)
    - % Passives (7-8)
    - % Detractors (1-6)
    - NPS = Promoters - Detractors
    - Media propensione
    - Numero esposti

    INPUT:
        df_perf      → dataframe performance filtrato per target
        canali_perf  → lista colonne Q9_
        col_prop     → colonna Q16 (probabilità di consiglio)

    OUTPUT:
        DataFrame con:
        Canale | Medici esposti | Promoters (%) | Passives (%) |
        Detractors (%) | NPS | Media propensione | N rispondenti
    """

    results = []

    for c in canali_perf:
        if c not in df_perf.columns:
            continue

        # medici esposti al canale (Q9_x non è NA)
        esposti = df_perf[df_perf[c].notna()]

        if len(esposti) == 0:
            continue

        # valori Q16 validi
        valid = esposti[col_prop].dropna()

        if valid.empty:
            results.append({
                "Canale": c,
                "Medici esposti": len(esposti),
                "Promoters (%)": None,
                "Passives (%)": None,
                "Detractors (%)": None,
                "NPS": None,
                "Media propensione": None,
                "N rispondenti": 0
            })
            continue

        promoters = (valid >= 9).mean() * 100
        passives = valid.between(7, 8).mean() * 100
        detractors = (valid <= 6).mean() * 100
        nps = promoters - detractors
        media = round(valid.mean(), 2)

        results.append({
            "Canale": c,
            "Medici esposti": len(esposti),
            "Promoters (%)": round(promoters, 1),
            "Passives (%)": round(passives, 1),
            "Detractors (%)": round(detractors, 1),
            "NPS": round(nps, 1),
            "Media propensione": media,
            "N rispondenti": len(valid)
        })

    if not results:
        return pd.DataFrame(columns=[
            "Canale", "Medici esposti", "Promoters (%)", "Passives (%)",
            "Detractors (%)", "NPS", "Media propensione", "N rispondenti"
        ])

    df_out = pd.DataFrame(results)

    # Ordina per miglior NPS (ignora righe con NPS None/NaN)
    df_out = df_out.sort_values("NPS", ascending=False, na_position="last").reset_index(drop=True)

    return df_out
