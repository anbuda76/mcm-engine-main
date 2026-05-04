import pandas as pd
import numpy as np

def _compute_channel_metrics(df, channel, col_ricordo, col_ingaggio, col_prop):
    """
    Calcola i 5 KPI per un singolo canale:
    - Penetrazione
    - Ricordo
    - Ingaggio
    - Propensione media
    - NPS
    """

    if channel not in df.columns:
        return {
            "Penetrazione (%)": None,
            "Ricordo (%)": None,
            "Ingaggio (%)": None,
            "Propensione media": None,
            "NPS": None,
        }

    esposti = df[df[channel].notna()]
    n_esposti = len(esposti)
    n_tot = len(df)

    if n_tot == 0:
        return {
            "Penetrazione (%)": None,
            "Ricordo (%)": None,
            "Ingaggio (%)": None,
            "Propensione media": None,
            "NPS": None,
        }

    pen = round((n_esposti / n_tot) * 100, 1)

    # Ricordo
    ric = None
    if col_ricordo in esposti.columns:
        ric = round((esposti[col_ricordo] == 1).mean() * 100, 1)

    # Ingaggio
    ing = None
    if col_ingaggio in esposti.columns:
        ing = round(esposti[col_ingaggio].isin([1, 2]).mean() * 100, 1)

    # Propensione
    prop = None
    nps = None
    if col_prop in esposti.columns:
        valid = esposti[col_prop].dropna()
        if len(valid) > 0:
            prop = round(valid.mean(), 2)
            promoters = (valid >= 9).mean() * 100
            detractors = (valid <= 6).mean() * 100
            nps = round(promoters - detractors, 1)

    return {
        "Penetrazione (%)": pen,
        "Ricordo (%)": ric,
        "Ingaggio (%)": ing,
        "Propensione media": prop,
        "NPS": nps,
    }


def compare_channels(df_focus, df_comp, df_market, cols):
    """
    Confronto Focus vs Competitor vs Mercato per ogni singolo canale Q9.
    """

    results = []

    canali = cols["canali_perf"]
    col_ricordo = cols["col_ricordo"]
    col_ingaggio = cols["col_ingaggio"]
    col_prop = cols["col_prop"]

    for channel in canali:

        # KPI Focus
        focus_kpi = _compute_channel_metrics(df_focus, channel, col_ricordo, col_ingaggio, col_prop)

        # KPI Competitor aggregati
        comp_kpi = _compute_channel_metrics(df_comp, channel, col_ricordo, col_ingaggio, col_prop)

        # KPI Mercato
        merc_kpi = _compute_channel_metrics(df_market, channel, col_ricordo, col_ingaggio, col_prop)

        # Deltone (Focus - Competitor | Focus - Mercato)
        def delta(a, b):
            if a is None or b is None:
                return None
            return round(a - b, 1)

        results.append({
            "Canale": channel,

            # KPI Focus
            "Pen Focus (%)": focus_kpi["Penetrazione (%)"],
            "Ricordo Focus (%)": focus_kpi["Ricordo (%)"],
            "Ingaggio Focus (%)": focus_kpi["Ingaggio (%)"],
            "Propensione Focus": focus_kpi["Propensione media"],
            "NPS Focus": focus_kpi["NPS"],

            # KPI Competitor
            "Pen Competitor (%)": comp_kpi["Penetrazione (%)"],
            "Ricordo Competitor (%)": comp_kpi["Ricordo (%)"],
            "Ingaggio Competitor (%)": comp_kpi["Ingaggio (%)"],
            "Propensione Competitor": comp_kpi["Propensione media"],
            "NPS Competitor": comp_kpi["NPS"],

            # KPI Mercato
            "Pen Mercato (%)": merc_kpi["Penetrazione (%)"],
            "Ricordo Mercato (%)": merc_kpi["Ricordo (%)"],
            "Ingaggio Mercato (%)": merc_kpi["Ingaggio (%)"],
            "Propensione Mercato": merc_kpi["Propensione media"],
            "NPS Mercato": merc_kpi["NPS"],

            # Delta Focus vs others
            "Delta Pen vs Competitor": delta(focus_kpi["Penetrazione (%)"], comp_kpi["Penetrazione (%)"]),
            "Delta Pen vs Mercato": delta(focus_kpi["Penetrazione (%)"], merc_kpi["Penetrazione (%)"]),
        })

    return pd.DataFrame(results)
