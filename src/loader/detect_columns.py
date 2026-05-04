def detect_columns(df_beh, df_perf):
    """
    Auto-detect robusto delle colonne chiave nei file raw.
    Funziona anche se i nomi cambiano nel tempo.
    """

    # -----------------------------------------
    # Target medico (specializzazione)
    # -----------------------------------------
    col_target = next(
        (c for c in df_beh.columns if "spec" in c.lower() or "target" in c.lower()),
        None
    )

    # -----------------------------------------
    # Azienda
    # -----------------------------------------
    col_azienda = next(
        (c for c in df_perf.columns if "aziend" in c.lower() or "azienda" in c.lower()),
        None
    )

    # -----------------------------------------
    # Prodotto
    # -----------------------------------------
    col_prodotto = next(
        (c for c in df_perf.columns if "prodott" in c.lower() or "nome farmaco" in c.lower()),
        None
    )

    # -----------------------------------------
    # Canali comportamento (Q11a – file Comportamento)
    # -----------------------------------------
    canali_11 = [c for c in df_beh.columns if c.lower().startswith("q11a")]

    # -----------------------------------------
    # Distribuzione comunicazione Aziende (Q2)
    # -----------------------------------------
    q2_cols = [
        c for c in df_beh.columns
        if c.lower().startswith("q2_1") or c.lower().startswith("q2_2") or c.lower().startswith("q2_3")
    ]

    # -----------------------------------------
    # Utilità canali (Q6 – file comportamento)
    # -----------------------------------------
    canali_utilita = [c for c in df_beh.columns if c.lower().startswith("q6")]

    # -----------------------------------------
    # Canali performance azienda (Q9 – file performance)
    # -----------------------------------------
    canali_perf = [c for c in df_perf.columns if c.lower().startswith("q9")]

    # -----------------------------------------
    # Ricordo (Q10_Ricorda Comunicazione)
    # -----------------------------------------
    col_ricordo = next(
        (c for c in df_perf.columns
         if "ricorda" in c.lower() or "q10" in c.lower() or "ricordo" in c.lower()),
        "Q10_Ricorda Comunicazione"
    )

    # -----------------------------------------
    # Ingaggio (Q13_1 Le informazioni erano Rilevanti)
    # -----------------------------------------
    col_ingaggio = next(
        (c for c in df_perf.columns
         if "q13" in c.lower() or "rilevanti" in c.lower() or "ingaggio" in c.lower()),
        "Q13_1 Le informazioni erano Rilevanti"
    )

    # -----------------------------------------
    # Propensione (Q16 probabilita di consiglio)
    # -----------------------------------------
    col_prop = next(
        (c for c in df_perf.columns
         if "q16" in c.lower() or "probabil" in c.lower() or "consiglio" in c.lower()),
        "Q16 probabilita di consiglio"
    )

    # -----------------------------------------
    # RETURN COMPLETO
    # -----------------------------------------
    return {
        "col_target": col_target,
        "col_azienda": col_azienda,
        "col_prodotto": col_prodotto,
        "canali_11": canali_11,
        "q2_cols": q2_cols,
        "canali_utilita": canali_utilita,
        "canali_perf": canali_perf,
        "col_ricordo": col_ricordo,
        "col_ingaggio": col_ingaggio,
        "col_prop": col_prop
    }
