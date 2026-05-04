"""
app/reports/commenti.py
────────────────────────
Generazione commenti strategici data-driven per il report PDF.
Nessuna dipendenza LLM — logica basata su soglie e template.
"""

from __future__ import annotations
import pandas as pd


# ── Soglie interpretazione ───────────────────────────────────────────────────

_SOGLIE_PEN = [
    (60, "molto alta",  "La copertura multicanale è eccellente: la maggior parte degli HCP è raggiunta."),
    (40, "alta",        "La copertura dei medici è solida, con buon presidio dei canali principali."),
    (20, "media",       "La copertura è nella norma, ma esistono margini di ampliamento su canali secondari."),
    (0,  "bassa",       "La copertura degli HCP risulta limitata: si consiglia di attivare nuovi canali o intensificare quelli esistenti."),
]

_SOGLIE_RIC = [
    (60, "alto",   "Il ricordo del messaggio è elevato: i canali comunicano in modo efficace."),
    (35, "medio",  "Il ricordo è nella media di settore. Ottimizzare il contenuto dei messaggi può aumentare il ritorno."),
    (0,  "basso",  "Il ricordo risulta basso: i messaggi potrebbero non essere sufficientemente rilevanti o frequenti per gli HCP."),
]

_SOGLIE_ING = [
    (30, "alto",   "L'ingaggio è elevato: gli HCP interagiscono attivamente con i contenuti multicanale."),
    (15, "medio",  "L'ingaggio è nella media. Contenuti più interattivi o personalizzati potrebbero aumentare la partecipazione."),
    (0,  "basso",  "L'ingaggio è basso: valutare formati più coinvolgenti (webinar, materiali digitali interattivi)."),
]


def _livello_soglia(val: float, soglie: list[tuple]) -> tuple[str, str]:
    """Restituisce (livello, commento) in base al valore e alle soglie."""
    for thr, lv, commento in soglie:
        if val >= thr:
            return lv, commento
    return "non disponibile", ""


def _top3_str(df: pd.DataFrame, col_canale: str, col_val: str, unit: str = "%") -> str:
    """Restituisce stringa 'C1 (X%), C2 (Y%), C3 (Z%)'."""
    top = df.dropna(subset=[col_canale, col_val]).nlargest(3, col_val)
    parts = []
    for _, row in top.iterrows():
        parts.append(f"{row[col_canale]} ({row[col_val]:.1f}{unit})")
    return ", ".join(parts) if parts else "n.d."


# ── Commenti KPI ─────────────────────────────────────────────────────────────

def commento_penetrazione(df_pen: pd.DataFrame) -> str:
    """Commento strategico per la sezione Penetrazione."""
    if df_pen is None or df_pen.empty:
        return "Dati penetrazione non disponibili per il target selezionato."
    col = "Penetrazione (%)"
    avg = float(df_pen[col].mean())
    livello, nota = _livello_soglia(avg, _SOGLIE_PEN)
    top3 = _top3_str(df_pen, "Canale", col)
    return (
        f"I canali con maggiore penetrazione sono: {top3}. "
        f"La penetrazione media tra tutti i canali è {avg:.1f}% — livello {livello}. "
        f"{nota}"
    )


def commento_ricordo(df_ric: pd.DataFrame) -> str:
    """Commento strategico per la sezione Ricordo."""
    if df_ric is None or df_ric.empty:
        return "Dati ricordo non disponibili per il target selezionato."
    col = "Ricordo (%)"
    avg = float(df_ric[col].mean())
    livello, nota = _livello_soglia(avg, _SOGLIE_RIC)
    top3 = _top3_str(df_ric, "Canale", col)
    return (
        f"I canali con ricordo più elevato sono: {top3}. "
        f"Il ricordo medio tra i canali analizzati è {avg:.1f}% — livello {livello}. "
        f"{nota}"
    )


def commento_ingaggio(df_ing: pd.DataFrame) -> str:
    """Commento strategico per la sezione Ingaggio."""
    if df_ing is None or df_ing.empty:
        return "Dati ingaggio non disponibili per il target selezionato."
    col = "Ingaggio totale (%)"
    avg = float(df_ing[col].mean())
    livello, nota = _livello_soglia(avg, _SOGLIE_ING)
    top3 = _top3_str(df_ing, "Canale", col)
    return (
        f"L'ingaggio più elevato si registra su: {top3}. "
        f"La media di ingaggio è {avg:.1f}% — livello {livello}. "
        f"{nota}"
    )


# ── Commento Mappa ────────────────────────────────────────────────────────────

def commento_mappa(df_mappa: pd.DataFrame) -> str:
    """
    Identifica canali nei 4 quadranti e genera commento interpretativo.
    Quadranti basati sulla mediana di Penetrazione (%) e Utilità media (1-7).
    """
    if df_mappa is None or df_mappa.empty:
        return "Dati mappa non disponibili."

    df = df_mappa.dropna(subset=["Penetrazione (%)", "Utilità media (1-7)"]).copy()
    if df.empty:
        return "Dati insufficienti per la mappa canali."

    x_med = df["Penetrazione (%)"].median()
    y_med = df["Utilità media (1-7)"].median()

    alto_valore  = df[(df["Penetrazione (%)"] >= x_med) & (df["Utilità media (1-7)"] >= y_med)]["Canale"].tolist()
    da_sviluppare = df[(df["Penetrazione (%)"] < x_med)  & (df["Utilità media (1-7)"] >= y_med)]["Canale"].tolist()
    quick_win    = df[(df["Penetrazione (%)"] >= x_med) & (df["Utilità media (1-7)"] < y_med)]["Canale"].tolist()
    secondari    = df[(df["Penetrazione (%)"] < x_med)  & (df["Utilità media (1-7)"] < y_med)]["Canale"].tolist()

    parti = []
    if alto_valore:
        parti.append(f"Canali ad Alto Valore (alta penetrazione e alta utilità): {', '.join(alto_valore[:3])} — da presidiare e investire.")
    if da_sviluppare:
        parti.append(f"Canali Da Sviluppare (bassa penetrazione, alta utilità): {', '.join(da_sviluppare[:3])} — potenziale inespresso, aumentarne la copertura.")
    if quick_win:
        parti.append(f"Canali Quick Win (alta penetrazione, bassa utilità): {', '.join(quick_win[:3])} — ampia reach ma bassa engagement, ottimizzare il contenuto.")
    if secondari:
        parti.append(f"Canali Secondari: {', '.join(secondari[:2])} — bassa priorità, monitorare.")

    return " ".join(parti) if parti else "Distribuzione canali nella norma."


# ── Commento Funnel ───────────────────────────────────────────────────────────

def commento_funnel(funnel_rows: list[dict]) -> str:
    """
    Analizza il funnel Pen→Ric→Ing e identifica il punto di maggior dispersione.
    funnel_rows: lista di dict con chiavi canale, pen, ric, ing, conv_pen_ric, conv_ric_ing.
    """
    if not funnel_rows:
        return "Dati funnel non disponibili."

    # Trova il canale con migliore conversione pen→ric
    valid = [r for r in funnel_rows if r.get("conv_pen_ric") is not None]
    if not valid:
        return "Dati di conversione insufficienti."

    best_conv = max(valid, key=lambda r: r["conv_pen_ric"])
    worst_conv = min(valid, key=lambda r: r["conv_pen_ric"])

    # Stima gap medio pen→ric
    avg_conv_pen_ric = sum(r["conv_pen_ric"] for r in valid) / len(valid)

    commento = (
        f"Il canale con migliore conversione Penetrazione→Ricordo è "
        f"{best_conv['canale']} ({best_conv['conv_pen_ric']:.1f}%), "
        f"mentre {worst_conv['canale']} mostra la maggiore dispersione ({worst_conv['conv_pen_ric']:.1f}%). "
        f"In media il {avg_conv_pen_ric:.1f}% degli HCP raggiunti ricorda il messaggio ricevuto. "
    )

    if avg_conv_pen_ric < 40:
        commento += "Il funnel evidenzia una perdita significativa tra penetrazione e ricordo: considerare messaggi più rilevanti o frequenza di contatto maggiore."
    else:
        commento += "La conversione nel funnel è positiva, a conferma dell'efficacia dei contenuti veicolati."

    return commento


# ── Commento OCV ─────────────────────────────────────────────────────────────

def commento_ocv(best_mix: dict, delta: dict | None) -> str:
    """
    Commento strategico sulla sezione OCV.
    best_mix: {"mix": str, "ocv": float, "recall": float, "action": str}
    delta: {"Recall 1 Channel": float, "Recall >=3 Channels": float, "OCV Delta (%)": float}
    """
    parti = []

    if best_mix and best_mix.get("mix"):
        ocv_val = best_mix.get("ocv", 0)
        recall  = best_mix.get("recall", 0)
        action  = best_mix.get("action", "")
        mix_str = best_mix.get("mix", "")

        if ocv_val > 0:
            cls = "sinergia positiva"
        elif ocv_val > -5:
            cls = "lieve saturazione"
        else:
            cls = "saturazione significativa"

        parti.append(
            f"Il mix ottimale identificato è: {mix_str} (OCV {ocv_val:+.1f}%, ricordo {recall:.1f}%) — {cls}. "
            f"Azione raccomandata: {action}."
        )

    if delta:
        r1  = delta.get("Recall 1 Channel", 0)
        r3  = delta.get("Recall \u22653 Channels", delta.get("Recall >=3 Channels", 0))
        d   = delta.get("OCV Delta (%)", 0)
        if r1 and r3:
            parti.append(
                f"L'esposizione a 1 solo canale genera un ricordo del {r1:.1f}%, "
                f"mentre l'esposizione a 3+ canali sale a {r3:.1f}% "
                f"(incremento OCV: {d:+.1f}%). "
                f"{'La strategia multicanale è chiaramente vantaggiosa.' if d > 0 else 'Attenzione alla saturazione: troppi canali possono ridurre il ricordo.'}"
            )

    return " ".join(parti) if parti else "Dati OCV non disponibili per questo target."


# ── Insight cover (pagina 1) ──────────────────────────────────────────────────

def insight_cover(df_pen: pd.DataFrame, df_ric: pd.DataFrame,
                  df_ing: pd.DataFrame) -> str:
    """
    Genera l'insight principale per la cover page — circa 10 righe descrittive.
    Struttura:
      1. Penetrazione: top canale + media + livello
      2. Ricordo: top canale + media + livello
      3. Ingaggio: top canale + media + livello
      4. Gap pen-ric: opportunita' di ottimizzazione
      5. Canale best-performer composito (pen+ric+ing)
      6. Direzione strategica in base ai KPI aggregati
    """
    if df_pen is None or df_pen.empty:
        return "Dati insufficienti per generare l'insight principale."

    righe = []

    # ── 1. PENETRAZIONE ──────────────────────────────────────────────────────
    col_pen = "Penetrazione (%)"
    top_pen   = df_pen.dropna(subset=[col_pen]).nlargest(1, col_pen).iloc[0]
    bot_pen   = df_pen.dropna(subset=[col_pen]).nsmallest(1, col_pen).iloc[0]
    pen_media = float(df_pen[col_pen].mean())
    pen_lv, _ = _livello_soglia(pen_media, _SOGLIE_PEN)
    top3_pen  = _top3_str(df_pen, "Canale", col_pen)

    righe.append(
        f"PENETRAZIONE: Il canale con massima copertura e' {top_pen['Canale']} "
        f"({top_pen[col_pen]:.1f}%), seguito da {top3_pen.split(', ', 1)[1] if ', ' in top3_pen else ''}. "
        f"La media complessiva tra tutti i canali e' {pen_media:.1f}% (livello {pen_lv}); "
        f"il canale meno presidiato e' {bot_pen['Canale']} ({bot_pen[col_pen]:.1f}%)."
    )

    # ── 2. RICORDO ───────────────────────────────────────────────────────────
    if df_ric is not None and not df_ric.empty:
        col_ric = "Ricordo (%)"
        top_ric   = df_ric.dropna(subset=[col_ric]).nlargest(1, col_ric).iloc[0]
        ric_media = float(df_ric[col_ric].mean())
        ric_lv, _ = _livello_soglia(ric_media, _SOGLIE_RIC)
        top3_ric  = _top3_str(df_ric, "Canale", col_ric)

        righe.append(
            f"RICORDO MESSAGGIO: Il ricordo piu' alto appartiene a {top_ric['Canale']} "
            f"({top_ric[col_ric]:.1f}%). Top 3: {top3_ric}. "
            f"Media di ricordo: {ric_media:.1f}% (livello {ric_lv})."
        )

        # ── 3. GAP PENETRAZIONE – RICORDO (opportunita') ──────────────────
        merged_pr = (
            df_pen[["Canale", col_pen]]
            .merge(df_ric[["Canale", col_ric]], on="Canale", how="inner")
        )
        if not merged_pr.empty:
            merged_pr["gap"] = merged_pr[col_pen] - merged_pr[col_ric]
            max_gap = merged_pr.nlargest(1, "gap").iloc[0]
            if max_gap["gap"] > 10:
                righe.append(
                    f"OPPORTUNITA': {max_gap['Canale']} presenta il gap piu' elevato tra "
                    f"penetrazione ({max_gap[col_pen]:.1f}%) e ricordo del messaggio "
                    f"({max_gap[col_ric]:.1f}%, gap {max_gap['gap']:.1f} pp). "
                    f"Ottimizzare la frequenza e la rilevanza dei contenuti su questo canale "
                    f"potrebbe incrementare sensibilmente la memorabilita' del messaggio."
                )

    # ── 4. INGAGGIO ──────────────────────────────────────────────────────────
    if df_ing is not None and not df_ing.empty:
        col_ing = "Ingaggio totale (%)"
        top_ing   = df_ing.dropna(subset=[col_ing]).nlargest(1, col_ing).iloc[0]
        ing_media = float(df_ing[col_ing].mean())
        ing_lv, _ = _livello_soglia(ing_media, _SOGLIE_ING)
        top3_ing  = _top3_str(df_ing, "Canale", col_ing)

        righe.append(
            f"INGAGGIO: L'interazione attiva piu' elevata si registra su {top_ing['Canale']} "
            f"({top_ing[col_ing]:.1f}%). Top 3 per ingaggio: {top3_ing}. "
            f"Ingaggio medio: {ing_media:.1f}% (livello {ing_lv})."
        )

        # ── 5. CANALE BEST-PERFORMER COMPOSITO ───────────────────────────
        if df_ric is not None and not df_ric.empty:
            df_all = (
                df_pen[["Canale", col_pen]]
                .merge(df_ric[["Canale", col_ric]], on="Canale", how="inner")
                .merge(df_ing[["Canale", col_ing]], on="Canale", how="inner")
            )
            if not df_all.empty:
                for c in [col_pen, col_ric, col_ing]:
                    mx = df_all[c].max()
                    df_all[f"{c}_n"] = df_all[c] / mx if mx > 0 else 0
                df_all["score"] = (df_all[f"{col_pen}_n"] +
                                   df_all[f"{col_ric}_n"] +
                                   df_all[f"{col_ing}_n"])
                best = df_all.nlargest(1, "score").iloc[0]
                righe.append(
                    f"BEST-PERFORMER: {best['Canale']} ottiene il punteggio composito "
                    f"piu' alto, con penetrazione {best[col_pen]:.1f}%, "
                    f"ricordo {best[col_ric]:.1f}% e ingaggio {best[col_ing]:.1f}%. "
                    f"E' il canale strategicamente prioritario per questo target."
                )

    # ── 6. DIREZIONE STRATEGICA ───────────────────────────────────────────────
    if pen_media < 25:
        strategia = (
            "DIREZIONE STRATEGICA: La copertura degli HCP e' limitata su quasi tutti i canali. "
            "Priorita' all'espansione del presidio: attivare canali non ancora utilizzati e "
            "intensificare quelli con maggiore potenziale di reach nel target."
        )
    elif pen_media < 45:
        strategia = (
            "DIREZIONE STRATEGICA: La copertura e' nella media. Il bilanciamento ottimale "
            "e' tra espansione della reach (canali meno presidiati) e miglioramento dei contenuti "
            "sui canali gia' attivi per aumentare ricordo e ingaggio degli HCP raggiunti."
        )
    else:
        strategia = (
            "DIREZIONE STRATEGICA: La copertura degli HCP e' ampia. Il focus deve spostarsi "
            "sulla qualita': aumentare il ricordo del messaggio attraverso contenuti piu' "
            "rilevanti e stimolare l'ingaggio attivo degli HCP gia' raggiunti dai canali chiave."
        )
    righe.append(strategia)

    return "\n".join(righe)
