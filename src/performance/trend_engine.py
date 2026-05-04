import pandas as pd

from src.performance.kpi_penetrazione_azienda import kpi_penetrazione_azienda
from src.performance.kpi_ricordo_azienda import kpi_ricordo_azienda
from src.performance.kpi_ingaggio_azienda import kpi_ingaggio_azienda
from src.performance.kpi_propensione_azienda import kpi_propensione_azienda
from src.performance.kpi_nps_azienda import kpi_nps_azienda


def compute_kpi_for_period(df_period, columns, azienda_focus):
    if df_period.empty:
        return None

    df_focus = df_period[df_period[columns["col_azienda"]] == azienda_focus]
    if df_focus.empty:
        return None

    return {
        "Penetrazione": kpi_penetrazione_azienda(df_focus, columns["canali_perf"]),
        "Ricordo": kpi_ricordo_azienda(df_focus, columns["col_ricordo"], columns["canali_perf"]),
        "Ingaggio": kpi_ingaggio_azienda(df_focus, columns["col_ingaggio"], columns["canali_perf"]),
        "Propensione": kpi_propensione_azienda(df_focus, columns["col_prop"]),
        "NPS": kpi_nps_azienda(df_focus, columns["col_prop"]),
    }


def compute_series(kpi_per_periodo):
    rows = []
    for periodo, info in kpi_per_periodo.items():
        if not info["valid"]:
            continue

        rows.append({
            "Periodo": periodo,
            "KPI": "Propensione_media",
            "Valore": info["Propensione"]["Media propensione"]
        })
        rows.append({
            "Periodo": periodo,
            "KPI": "NPS",
            "Valore": info["NPS"]["NPS"]
        })
    return pd.DataFrame(rows)


def compute_kpi_for_entity(df, columns, azienda, periodi):
    out = {"KPI_per_periodo": {}, "Series": None}

    for p in periodi:
        df_p = df[df["Periodo"] == p]
        kpi = compute_kpi_for_period(df_p, columns, azienda)

        if kpi is None:
            out["KPI_per_periodo"][p] = {
                "valid": False,
                "message": f"Nessun dato disponibile per il periodo {p}",
                "Penetrazione": None,
                "Ricordo": None,
                "Ingaggio": None,
                "Propensione": None,
                "NPS": None
            }
        else:
            out["KPI_per_periodo"][p] = {
                "valid": True,
                "message": "",
                **kpi
            }

    out["Series"] = compute_series(out["KPI_per_periodo"])
    return out


def trend_engine(df_perf, columns, azienda_focus, periodi, prodotti=None):

    # ========================
    # KPI azienda (totali)
    # ========================
    df_azienda = df_perf[df_perf[columns["col_azienda"]] == azienda_focus]
    result_azienda = compute_kpi_for_entity(df_azienda, columns, azienda_focus, periodi)

    # ========================
    # KPI prodotti (se selezionati)
    # ========================
    prodotti_dict = {}

    if prodotti:
        for prod in prodotti:
            df_prod = df_azienda[df_azienda[columns["col_prodotto"]] == prod]
            prodotti_dict[prod] = compute_kpi_for_entity(df_prod, columns, azienda_focus, periodi)

    return {
        "Azienda": result_azienda,
        "Prodotti": prodotti_dict
    }
