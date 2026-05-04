import pandas as pd


# ----------------------------------------------------------
# 1) Funzioni di normalizzazione competitor
# ----------------------------------------------------------

def collapse_prop(prop_value):
    if isinstance(prop_value, list):
        df = pd.DataFrame(prop_value)
        return df["Media propensione"].mean()

    if isinstance(prop_value, dict):
        return prop_value.get("Media propensione", None)

    return None


def collapse_nps(nps_value):
    if isinstance(nps_value, list):
        df = pd.DataFrame(nps_value)
        return df["NPS"].mean()

    if isinstance(nps_value, dict):
        return nps_value.get("NPS", None)

    return None


# ----------------------------------------------------------
# 2) FUNZIONE compare_channels_enhanced (SEMPLIFICATA)
# ----------------------------------------------------------

def compare_channels_enhanced(
        df_pen_az, df_ric_az, df_ing_az, df_prop_az,
        df_pen_comp, df_ric_comp, df_ing_comp, df_prop_comp,
        df_pen_merc, df_ric_merc, df_ing_merc, df_prop_merc,
        df_focus=None, df_perf_filt=None, df_market=None,
        competitor_list=None, canali_perf=None, col_prop=None
):
    """
    Tabella avanzata di confronto canali:
    - Penetrazione / Ricordo / Ingaggio (Focus / Competitor / Mercato)
    - Propensione globale
    - 🔥 NPS & Propensione per canale reale (solo medici esposti)
    (SEZIONE DELTA KPI RIMOSSA)
    """

    # ------------------------------------------------------
    # 1) PROPENSIONE GLOBALE
    # ------------------------------------------------------
    prop_focus = df_prop_az.get("Media propensione", None)
    prop_comp = collapse_prop(df_prop_comp)
    prop_merc = df_prop_merc.get("Media propensione", None)

    # ------------------------------------------------------
    # 2) MERGE Penetrazione + Ricordo + Ingaggio
    # ------------------------------------------------------
    df = df_pen_az.copy()
    df = df.rename(columns={"Penetrazione (%)": "Pen Focus (%)"})

    # --- FIX: MERCATO (evita perdita colonna Canale) ---
    df_pen_merc_tmp = df_pen_merc.rename(columns={"Penetrazione (%)": "Pen Merc (%)"})
    if "Mercato" in df_pen_merc_tmp.columns:
        df_pen_merc_tmp = df_pen_merc_tmp.drop(columns=["Mercato"])
    df = df.merge(df_pen_merc_tmp, on="Canale", how="left")

    # COMPETITOR
    if df_pen_comp.empty:
        raise ValueError("df_pen_comp è vuoto.")

    df_comp_pen = df_pen_comp.groupby("Canale")["Penetrazione (%)"].mean().reset_index()
    df_comp_pen = df_comp_pen.rename(columns={"Penetrazione (%)": "Pen Competitor (%)"})
    df = df.merge(df_comp_pen, on="Canale", how="left")

    # --- RICORDO ---
    df_ric_az = df_ric_az.rename(columns={"Ricorda (%)": "Ricordo Focus (%)"})
    df_ric_comp = df_ric_comp.groupby("Canale")["Ricorda (%)"].mean().reset_index()
    df_ric_comp = df_ric_comp.rename(columns={"Ricorda (%)": "Ricordo Competitor (%)"})
    df_ric_merc = df_ric_merc.rename(columns={"Ricorda (%)": "Ricordo Mercato (%)"})

    df = df.merge(df_ric_az[["Canale", "Ricordo Focus (%)"]], on="Canale", how="left")
    df = df.merge(df_ric_comp, on="Canale", how="left")
    df = df.merge(df_ric_merc[["Canale", "Ricordo Mercato (%)"]], on="Canale", how="left")

    # --- INGAGGIO ---
    df_ing_az = df_ing_az.rename(columns={"Condivisione (%)": "Ingaggio Focus (%)"})
    df_ing_comp = df_ing_comp.groupby("Canale")["Condivisione (%)"].mean().reset_index()
    df_ing_comp = df_ing_comp.rename(columns={"Condivisione (%)": "Ingaggio Competitor (%)"})
    df_ing_merc = df_ing_merc.rename(columns={"Condivisione (%)": "Ingaggio Mercato (%)"})

    df = df.merge(df_ing_az[["Canale", "Ingaggio Focus (%)"]], on="Canale", how="left")
    df = df.merge(df_ing_comp, on="Canale", how="left")
    df = df.merge(df_ing_merc[["Canale", "Ingaggio Mercato (%)"]], on="Canale", how="left")

    # ------------------------------------------------------
    # 3) Propensione globale
    # ------------------------------------------------------
    df["Propensione Focus"] = prop_focus
    df["Propensione Competitor"] = prop_comp
    df["Propensione Mercato"] = prop_merc

    # ------------------------------------------------------
    # 4) NPS & PROPENSIONE PER CANALE (solo esposti)
    # ------------------------------------------------------
    if df_focus is None or df_market is None or df_perf_filt is None:
        return df

    nps_focus_list = []
    nps_comp_list = []
    nps_merc_list = []

    prop_focus_list = []
    prop_comp_list = []
    prop_merc_list = []

    for canale in df["Canale"]:

        # --- Focus ---
        focus_exp = df_focus[df_focus[canale].notna()]
        if not focus_exp.empty:
            nps_f = ((focus_exp[col_prop] >= 9).mean() * 100) - ((focus_exp[col_prop] <= 6).mean() * 100)
            prop_f = focus_exp[col_prop].mean()
        else:
            nps_f = None
            prop_f = None

        # --- Competitor ---
        comp_nps_vals = []
        comp_prop_vals = []

        for comp in competitor_list:
            df_c = df_perf_filt[df_perf_filt["Azienda"] == comp]
            comp_exp = df_c[df_c[canale].notna()]
            if not comp_exp.empty:
                comp_n = ((comp_exp[col_prop] >= 9).mean() * 100) - ((comp_exp[col_prop] <= 6).mean() * 100)
                comp_p = comp_exp[col_prop].mean()
                comp_nps_vals.append(comp_n)
                comp_prop_vals.append(comp_p)

        nps_c = round(sum(comp_nps_vals) / len(comp_nps_vals), 1) if comp_nps_vals else None
        prop_c = round(sum(comp_prop_vals) / len(comp_prop_vals), 2) if comp_prop_vals else None

        # --- Mercato ---
        merc_exp = df_market[df_market[canale].notna()]
        if not merc_exp.empty:
            nps_m = ((merc_exp[col_prop] >= 9).mean() * 100) - ((merc_exp[col_prop] <= 6).mean() * 100)
            prop_m = merc_exp[col_prop].mean()
        else:
            nps_m = None
            prop_m = None

        # Store
        nps_focus_list.append(nps_f)
        nps_comp_list.append(nps_c)
        nps_merc_list.append(nps_m)

        prop_focus_list.append(prop_f)
        prop_comp_list.append(prop_c)
        prop_merc_list.append(prop_m)

    # ------------------------------------------------------
    # 5) Aggiunta colonne finali
    # ------------------------------------------------------
    df["NPS Focus (esposti)"] = [round(x, 1) if x is not None else None for x in nps_focus_list]
    df["NPS Competitor (esposti)"] = nps_comp_list
    df["NPS Mercato (esposti)"] = [round(x, 1) if x is not None else None for x in nps_merc_list]

    df["Prop Focus (esposti)"] = prop_focus_list
    df["Prop Competitor (esposti)"] = prop_comp_list
    df["Prop Mercato (esposti)"] = prop_merc_list

    return df
