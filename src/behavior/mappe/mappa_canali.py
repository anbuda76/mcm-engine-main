import pandas as pd
from .mappa_canali_labels import CANALI_MAP

def normalizza_canale(nome):
    """Restituisce il nome standard del canale"""
    return CANALI_MAP.get(nome, None)

def crea_mappa_canali(df_pen, df_util, df_ing, df_prop):
    """
    Unisce i KPI principali usando nomi canale normalizzati
    """

    # ===== NORMALIZZAZIONE =====
    df_pen["Canale_std"] = df_pen["Canale"].apply(normalizza_canale)
    df_util["Canale_std"] = df_util["Canale"].apply(normalizza_canale)
    df_ing["Canale_std"]  = df_ing["Canale"].apply(normalizza_canale)
    df_prop["Canale_std"] = df_prop["Canale"].apply(normalizza_canale)

    # Mantieni solo quelli che hanno match
    df_pen = df_pen.dropna(subset=["Canale_std"])
    df_util = df_util.dropna(subset=["Canale_std"])
    df_ing  = df_ing.dropna(subset=["Canale_std"])
    df_prop = df_prop.dropna(subset=["Canale_std"])

    # ===== MERGE =====
    df_merge = (
        df_pen[["Canale_std","Penetrazione (%)"]]
        .merge(df_util[["Canale_std","Utilità media (1-7)"]], on="Canale_std", how="outer")
        .merge(df_ing[["Canale_std","Ingaggio totale (%)"]], on="Canale_std", how="outer")
        .merge(df_prop[["Canale_std","Probabilità media consiglio"]], on="Canale_std", how="outer")
    )

    df_merge = df_merge.rename(columns={
        "Canale_std": "Canale"
    })

    return df_merge
