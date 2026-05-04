import os
import pandas as pd


RAW_FOLDER = "data_raw"


def clean_company_name(name: str) -> str:
    """Normalizza i nomi delle aziende in modo semplice e robusto."""
    if pd.isna(name):
        return ""
    name = str(name).strip().upper()

    # Correzioni frequenti
    replacements = {
        "  ": " ",
        "(ITALIA)": "",
        "(IT)": "",
        "-": " ",
        "_": " ",
    }

    for k, v in replacements.items():
        name = name.replace(k, v)

    return name.strip()


def detect_columns_perf(df_perf):
    """
    Identifica automaticamente le colonne chiave del file Performance.
    Funziona anche se i nomi cambiano.
    """

    col_target = next(
        (c for c in df_perf.columns if "spec" in c.lower() or "target" in c.lower()),
        None
    )

    col_azienda = next(
        (c for c in df_perf.columns if "aziend" in c.lower() or "company" in c.lower()),
        None
    )

    col_prodotto = next(
        (c for c in df_perf.columns if "prodott" in c.lower() or "brand" in c.lower()),
        None
    )

    canali_perf = [c for c in df_perf.columns if c.lower().startswith("q9_")]
    col_ricordo = next((c for c in df_perf.columns if "q10" in c.lower()), None)
    col_ingaggio = next((c for c in df_perf.columns if "q13" in c.lower()), None)
    col_prop = next((c for c in df_perf.columns if "q16" in c.lower()), None)

    return {
        "col_target": col_target,
        "col_azienda": col_azienda,
        "col_prodotto": col_prodotto,
        "canali_perf": canali_perf,
        "col_ricordo": col_ricordo,
        "col_ingaggio": col_ingaggio,
        "col_prop": col_prop,
    }


def build_company_mapping(df_perf, col_azienda, col_prodotto):
    """
    Costruisce il mapping Azienda → lista prodotti.
    Gestisce automaticamente:
    - normalizzazione
    - duplicati
    """

    df_temp = df_perf[[col_azienda, col_prodotto]].copy()
    df_temp[col_azienda] = df_temp[col_azienda].apply(clean_company_name)
    df_temp[col_prodotto] = df_temp[col_prodotto].astype(str)

    mapping = (
        df_temp.groupby(col_azienda)[col_prodotto]
        .unique()
        .apply(list)
        .to_dict()
    )

    return mapping


def load_performance_data():
    """
    Carica il file Performance, normalizza i nomi aziende, identifica colonne e crea mapping.
    """

    files = os.listdir(RAW_FOLDER)
    file_perf = next((f for f in files if "Performance" in f), None)

    if not file_perf:
        raise FileNotFoundError("⚠️ ERRORE: file Performance non trovato nella cartella data_raw")

    df_perf = pd.read_excel(os.path.join(RAW_FOLDER, file_perf))

    # --------------------------------------------------------
    # Aggiunta colonna Quarter e Periodo (Anno_Quarter)
    # --------------------------------------------------------

    # Verifica che le colonne Anno e Mese esistano
    if "Anno" not in df_perf.columns or "Mese" not in df_perf.columns:
        raise ValueError("⚠️ ERRORE: nel dataset Performance mancano le colonne 'Anno' e/o 'Mese'.")

    # Conversione sicura
    df_perf["Anno"] = pd.to_numeric(df_perf["Anno"], errors="coerce").astype("Int64")
    df_perf["Mese"] = pd.to_numeric(df_perf["Mese"], errors="coerce").astype("Int64")

    # Funzione di calcolo Quarter
    def assign_quarter(month):
        if month in [1, 2, 3]:
            return "Q1"
        elif month in [4, 5, 6]:
            return "Q2"
        elif month in [7, 8, 9]:
            return "Q3"
        elif month in [10, 11, 12]:
            return "Q4"
        else:
            return None

    # Applicazione Quarter
    df_perf["Quarter"] = df_perf["Mese"].apply(assign_quarter)

    # Creazione Periodo
    df_perf["Periodo"] = df_perf["Anno"].astype(str) + "_" + df_perf["Quarter"]

    # --------------------------------------------------------
    # Riconoscimento colonne e mapping prodotti
    # --------------------------------------------------------

    columns = detect_columns_perf(df_perf)

    col_azienda = columns["col_azienda"]
    col_prodotto = columns["col_prodotto"]

    # normalizza aziende
    df_perf[col_azienda] = df_perf[col_azienda].apply(clean_company_name)

    # mapping azienda-prodotti
    mapping = build_company_mapping(df_perf, col_azienda, col_prodotto)

    # lista aziende disponibili (set pulito)
    aziende = sorted([a for a in df_perf[col_azienda].unique() if str(a).strip() != ""])

    print("File Performance caricato.")
    print("Aziende trovate:", len(aziende))

    return {
        "df_perf": df_perf,
        "columns": columns,
        "aziende": aziende,
        "azienda_prodotti": mapping,
    }
