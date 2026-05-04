def define_market(df_perf, azienda_focus, competitor_list):
    """
    Definisce il mercato aziendale come:
    Focus + Competitor selezionati.
    """

    mercato = [azienda_focus] + competitor_list

    # Rimuovi eventuali duplicati
    mercato = list(dict.fromkeys(mercato))

    return mercato
