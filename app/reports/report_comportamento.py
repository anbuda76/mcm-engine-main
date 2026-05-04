"""
app/reports/report_comportamento.py
─────────────────────────────────────
Orchestratore principale del report PDF Comportamento HCP.

Struttura 4 pagine:
  Pag.1 — Cover: header, KPI sintesi, top canali, insight
  Pag.2 — KPI Generali: penetrazione, ricordo, ingaggio (grafici + commenti)
  Pag.3 — Mappa Canali + Funnel HCP (scatter + tabella conversion)
  Pag.4 — OCV: mix ottimale, tabella top mix, note metodologiche

Funzione pubblica:
  genera_report(targets: list[str]) -> io.BytesIO
"""

from __future__ import annotations

import io
import sys
import os
from datetime import datetime

import pandas as pd
from fpdf import FPDF

# ── path per src/ ──────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.data_cache import get_data
from src.behavior.kpi_penetrazione     import kpi_penetrazione
from src.behavior.kpi_utilita          import kpi_utilita
from src.behavior.kpi_ricordo          import kpi_ricordo_canali
from src.behavior.kpi_ingaggio         import kpi_ingaggio_canali
from src.behavior.kpi_propensione      import kpi_propensione_canali
from src.behavior.kpi_ocv_mix          import ocv_delta, ocv_mix_engine
from src.behavior.mappe.mappa_canali   import crea_mappa_canali
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP

from app.reports.pdf_utils import (
    FPDF, PW, PH, ML, MR, MT, MB, CW, FOOTER_Y, C,
    _safe_text, _fc, _tc, _dc,
    fill_page_bg, draw_header_band, draw_section_band,
    draw_card, draw_kpi_box, draw_highlight_box,
    write_body, write_note, write_label,
    draw_table, add_footer,
)
from app.reports import charts as ch
from app.reports import commenti as cm

TOTAL_PAGES = 4


# ── Helpers ────────────────────────────────────────────────────────────────────

def _filtra(df: pd.DataFrame, col: str, vals: list) -> pd.DataFrame:
    if not vals or not col or col not in df.columns:
        return df
    return df[df[col].isin(vals)].copy()


def _filtra_q7(df_beh: pd.DataFrame, df_perf: pd.DataFrame,
               aree: list, patologie: list):
    """Filtra df_beh per area terapeutica (Q7a) e/o patologie (Q7b_*),
    poi propaga il filtro a df_perf tramite join su Respondent."""
    import re as _re
    from src.behavior.mappe.mappa_patologie import normalizza_q7a, normalizza_q7b

    if not aree and not patologie:
        return df_beh, df_perf

    q7a_col  = next((c for c in df_beh.columns if c.startswith("Q7a")), None)
    q7b_cols = [c for c in df_beh.columns if _re.match(r"Q7b_\d+", c)]

    mask = pd.Series(True, index=df_beh.index)

    if aree and q7a_col:
        norm_area = df_beh[q7a_col].apply(normalizza_q7a)
        mask &= norm_area.isin(set(aree))

    if patologie and q7b_cols:
        pat_mask = pd.Series(False, index=df_beh.index)
        for col in q7b_cols:
            pat_mask |= df_beh[col].apply(normalizza_q7b).isin(set(patologie))
        mask &= pat_mask

    df_beh_f = df_beh[mask].copy()
    df_perf_f = df_perf
    if "Respondent" in df_beh_f.columns and "Respondent" in df_perf.columns:
        df_perf_f = df_perf[
            df_perf["Respondent"].isin(set(df_beh_f["Respondent"]))
        ].copy()

    return df_beh_f, df_perf_f


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza label canali via CANALI_MAP."""
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _norm_mix_str(mix_str: str) -> str:
    parts = str(mix_str).split(" + ")
    return " + ".join(CANALI_MAP.get(p.strip(), p.strip()) for p in parts)


def _embed_chart(pdf: FPDF, img_bytes: bytes, y: float, w: float = CW) -> float:
    """
    Incorpora un'immagine PNG nel PDF.
    Ritorna la y dopo l'immagine (y + altezza effettiva).
    """
    buf = io.BytesIO(img_bytes)
    # FPDF2 auto-calcola h proporzionalmente se passiamo solo w
    pdf.image(buf, x=ML, y=y, w=w)
    # Stima altezza (la img viene incorporata dal pdf.image, poi ci spostiamo)
    # Usiamo pdf.get_y() dopo; FPDF2 non aggiorna get_y() automaticamente con image
    # → usiamo formula: h_mm = w_mm * (img_height_px / img_width_px)
    # Per semplicità usiamo un offset fisso basato sul rendering precedente
    # La funzione ritorna la y corrente aggiornata
    return pdf.get_y()


def _safe_chart(fn, *args, **kwargs) -> bytes | None:
    """Esegue fn(*args, **kwargs) per generare PNG. Ritorna None in caso di errore."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[report_pdf] Errore generazione chart {fn.__name__}: {e}")
        return None


# ── Pagina 1: Cover + Executive Summary ───────────────────────────────────────

def _pag1_cover(pdf: FPDF, target_label: str, n_hcp: int,
                df_pen, df_ric, df_ing,
                aree: list | None = None, patologie: list | None = None):
    """
    Pagina 1 (Cover) — layout ad Y assoluta per evitare sovrapposizioni.

    Struttura verticale (Y in mm):
      0–44  : Header band (navy) — titolo "Summary Multichannel Monitoring"
      47    : Intro box descrittivo         h=34
      84    : Target info card              h=13 (espansa se area/patologie presenti)
      100+  : KPI 3 boxes (row)            h=26
      129+  : Divider teal + label
      136+  : Top 3 channel cards          h=23
      163+  : Insight principale           h=dinamica (~90mm)
      265   : Nota metodologica
      285   : Footer
    """
    aree      = aree      or []
    patologie = patologie or []
    fill_page_bg(pdf)

    # ── 1. HEADER BAND ─────────────────────────────────────────────────────────
    draw_header_band(
        pdf,
        title="Summary Multichannel Monitoring",
        subtitle="Analisi del Comportamento HCP -- Canali di Comunicazione Scientifica",
    )
    # ® marchio registrato — apice piccolo (9pt) a y -2mm rispetto al titolo (20pt)
    _r_base_text = _safe_text("Summary Multichannel Monitoring")
    pdf.set_font("Helvetica", "B", 20)
    _r_x = ML + 6 + pdf.get_string_width(_r_base_text) + 0.5
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C["white"])
    pdf.set_xy(_r_x, 7)   # y=7 → 2mm sopra il titolo (y=9) → effetto apice
    pdf.cell(5, 5, "\u00ae")

    # ── 2. INTRO BOX DESCRITTIVO ──────────────────────────────────────────────
    # Testo fisso che spiega scopo, contenuto e obiettivo del summary
    _INTRO = (
        "Questo Summary Multichannel Monitoring\u00ae analizza il comportamento degli HCP "
        "(Healthcare Professionals) nell'interazione con i canali di comunicazione "
        "scientifica nel periodo di riferimento. "
        "Il documento e' strutturato in quattro aree di analisi: KPI di Penetrazione, "
        "Ricordo e Ingaggio per canale; Mappa Strategica di posizionamento; "
        "Funnel di conversione HCP (Penetrazione > Ricordo > Ingaggio); "
        "OCV -- Omnichannel Value e analisi del mix ottimale.\n"
        "L'obiettivo e' supportare la comprensione del journey dell'informazione "
        "scientifica: come raggiunge i medici target, quanto viene ricordata e in "
        "che misura genera ingaggio attivo -- dati essenziali per orientare "
        "le decisioni strategiche multicanale."
    )
    intro_text = _safe_text(_INTRO)

    # Stima altezza dinamica dell'intro box (~100 chars/riga a 7.5pt in 164mm)
    _CPL_INTRO = 100
    _LH_INTRO  = 4.0
    _nw_intro  = sum(
        max(1, (len(s) + _CPL_INTRO - 1) // _CPL_INTRO)
        for s in intro_text.split("\n")
    )
    H_INTRO = max(30, 11 + _nw_intro * _LH_INTRO)

    Y_INTRO = 47
    draw_card(pdf, ML, Y_INTRO, CW, H_INTRO, "surface_800")
    # Barra teal verticale sinistra
    pdf.set_fill_color(*C["teal"])
    pdf.rect(ML, Y_INTRO, 2.5, H_INTRO, style="F")
    # Barra teal top sottile
    pdf.rect(ML, Y_INTRO, CW, 1.2, style="F")

    pdf.set_text_color(*C["white_70"])
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_xy(ML + 6, Y_INTRO + 5)
    pdf.multi_cell(CW - 10, _LH_INTRO, intro_text)

    # ── 3. TARGET INFO CARD ────────────────────────────────────────────────────
    Y_TGT = Y_INTRO + H_INTRO + 3  # dinamico, si adatta all'altezza dell'intro

    # Calcola altezza card in base ai filtri attivi
    H_TGT_BASE = 13
    H_AREA_ROW = 6   # mm per la riga area terapeutica
    H_PAT_ROW  = 6   # mm per la riga patologie
    H_TGT = H_TGT_BASE + (H_AREA_ROW if aree else 0) + (H_PAT_ROW if patologie else 0)

    draw_card(pdf, ML, Y_TGT, CW, H_TGT, "surface_700")

    # Barra accent sinistra
    pdf.set_fill_color(*C["teal"])
    pdf.rect(ML, Y_TGT, 2, H_TGT, style="F")

    # ── riga 1: label "TARGET IN ANALISI" | "HCP analizzati: N"
    pdf.set_text_color(*C["white_40"])
    pdf.set_font("Helvetica", "", 7)
    pdf.set_xy(ML + 4, Y_TGT + 2.5)
    pdf.cell(50, 4, "TARGET IN ANALISI")

    pdf.set_text_color(*C["white_40"])
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_xy(ML + CW - 52, Y_TGT + 2.5)
    pdf.cell(49, 4, f"HCP analizzati: {n_hcp:,}", align="R")

    # ── riga 2: valore target | data
    pdf.set_text_color(*C["teal"])
    pdf.set_font("Helvetica", "B", 9)
    tgt_display = _safe_text(target_label[:60])
    pdf.set_xy(ML + 4, Y_TGT + 7.5)
    pdf.cell(CW - 60, 4.5, tgt_display)

    pdf.set_text_color(*C["white_40"])
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_xy(ML + CW - 52, Y_TGT + 7.5)
    pdf.cell(49, 4, f"Data: {datetime.now().strftime('%d/%m/%Y')}", align="R")

    # ── riga 3 (facoltativa): area terapeutica
    _row_y = Y_TGT + H_TGT_BASE
    if aree:
        aree_str = _safe_text((" · ".join(aree))[:80])
        pdf.set_text_color(*C["white_40"])
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(ML + 4, _row_y + 1)
        pdf.cell(30, 4, "AREA TERAPEUTICA:")
        pdf.set_text_color(*C["teal"])
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(ML + 36, _row_y + 1)
        pdf.cell(CW - 40, 4, aree_str)
        _row_y += H_AREA_ROW

    # ── riga 4 (facoltativa): patologie
    if patologie:
        pat_str = _safe_text((" · ".join(patologie))[:90])
        pdf.set_text_color(*C["white_40"])
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(ML + 4, _row_y + 1)
        pdf.cell(22, 4, "PATOLOGIE:")
        pdf.set_text_color(*C["white"])
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_xy(ML + 28, _row_y + 1)
        pdf.cell(CW - 32, 4, pat_str)

    # ── 4. KPI BOXES (3 in riga) ───────────────────────────────────────────────
    Y_KPI = Y_TGT + H_TGT + 4
    H_KPI = 26
    bw = (CW - 8) / 3  # ~57.3mm per box (gap 4mm)

    pen_avg = round(float(df_pen["Penetrazione (%)"].mean()), 1) if df_pen is not None and not df_pen.empty else 0
    ric_avg = round(float(df_ric["Ricordo (%)"].mean()), 1)      if df_ric is not None and not df_ric.empty else 0
    ing_avg = round(float(df_ing["Ingaggio totale (%)"].mean()), 1) if df_ing is not None and not df_ing.empty else 0

    draw_kpi_box(pdf, ML,             Y_KPI, bw, H_KPI, "Penetrazione Media", f"{pen_avg}", "% HCP raggiunti")
    draw_kpi_box(pdf, ML + bw + 4,    Y_KPI, bw, H_KPI, "Ricordo Medio",      f"{ric_avg}", "% HCP che ricordano")
    draw_kpi_box(pdf, ML + 2*(bw+4),  Y_KPI, bw, H_KPI, "Ingaggio Medio",     f"{ing_avg}", "% HCP ingaggiati")

    # ── 5. SEZIONE TOP CANALI ──────────────────────────────────────────────────
    Y_DIV1  = Y_KPI + H_KPI + 3   # linea divisore teal
    Y_LABEL = Y_DIV1 + 2          # label sezione
    Y_CARDS = Y_DIV1 + 9          # inizio card canali
    H_CARD  = 23                  # altezza card canale

    # Linea divisore orizzontale teal
    pdf.set_fill_color(*C["teal"])
    pdf.rect(ML, Y_DIV1, CW, 0.6, style="F")

    # Label "TOP CANALI PER PENETRAZIONE"
    pdf.set_text_color(*C["teal"])
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(ML, Y_LABEL)
    pdf.cell(CW, 5, "TOP CANALI PER PENETRAZIONE")

    # Card per ognuno dei top 3
    card_w = (CW - 8) / 3  # ~57.3mm
    RANK_COLORS = ["teal", "teal_mid", "white_70"]
    RANK_DRAW   = [C["teal"], C["teal_mid"], C["white_40"]]

    if df_pen is not None and not df_pen.empty:
        top3 = (df_pen.dropna(subset=["Penetrazione (%)"])
                       .nlargest(3, "Penetrazione (%)")
                       .reset_index(drop=True))
        for i, row in top3.iterrows():
            xc = ML + i * (card_w + 4)

            # Card background + bordo colorato
            pdf.set_fill_color(*C["surface_700"])
            pdf.set_draw_color(*RANK_DRAW[i])
            pdf.set_line_width(0.4)
            pdf.rect(xc, Y_CARDS, card_w, H_CARD, style="FD")

            # Barra accent top (1.5mm)
            pdf.set_fill_color(*RANK_DRAW[i])
            pdf.rect(xc, Y_CARDS, card_w, 1.5, style="F")

            # Rank (#1 #2 #3) — sinistra, grande
            pdf.set_text_color(*C[RANK_COLORS[i]])
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_xy(xc + 3, Y_CARDS + 2.5)
            pdf.cell(18, 9, f"#{i+1}")

            # Valore % — destra, grande, stesso colore rank
            val_str = f"{row['Penetrazione (%)']:.1f}%"
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_xy(xc + card_w - 30, Y_CARDS + 2.5)
            pdf.cell(27, 9, val_str, align="R")

            # Nome canale — sotto, bianco, più piccolo
            nome = _safe_text(str(row["Canale"]))
            pdf.set_text_color(*C["white"])
            pdf.set_font("Helvetica", "", 7)
            pdf.set_xy(xc + 3, Y_CARDS + 14)
            pdf.multi_cell(card_w - 6, 3.6, nome[:36])

    # ── 6. INSIGHT PRINCIPALE ─────────────────────────────────────────────────
    Y_INS = Y_CARDS + H_CARD + 4
    insight_text = _safe_text(cm.insight_cover(df_pen, df_ric, df_ing))

    # Stima altezza dinamica — font 8pt, line-height 4.2mm, ~88 chars/riga in 172mm
    LINE_H         = 4.2
    CHARS_PER_LINE = 88
    n_wrap_lines   = sum(
        max(1, (len(seg) + CHARS_PER_LINE - 1) // CHARS_PER_LINE)
        for seg in insight_text.split("\n")
    )
    H_INS = max(45, 14 + n_wrap_lines * LINE_H)
    H_INS = min(H_INS, FOOTER_Y - 28 - Y_INS)

    draw_card(pdf, ML, Y_INS, CW, H_INS, "surface_800")
    # Barra teal top
    pdf.set_fill_color(*C["teal"])
    pdf.rect(ML, Y_INS, CW, 2.5, style="F")
    # Barra accent verticale sinistra
    pdf.rect(ML, Y_INS, 3, H_INS, style="F")

    pdf.set_text_color(*C["teal"])
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_xy(ML + 7, Y_INS + 5)
    pdf.cell(CW - 11, 5, "INSIGHT PRINCIPALE")

    pdf.set_text_color(*C["white_70"])
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(ML + 7, Y_INS + 13)
    pdf.multi_cell(CW - 11, LINE_H, insight_text)

    # ── 7. NOTA METODOLOGICA + FOOTER ─────────────────────────────────────────
    pdf.set_y(FOOTER_Y - 20)
    write_note(pdf,
        "Il presente summary e' generato automaticamente dalla piattaforma MCM Engine -- BHAVE Platform. "
        "I dati si riferiscono al campione di HCP analizzato per il target selezionato. "
        "I KPI sono calcolati sulla base delle risposte al questionario BHAVE."
    )

    add_footer(pdf, 1, TOTAL_PAGES)


# ── Pagina 2: KPI Generali ────────────────────────────────────────────────────

def _pag2_kpi(pdf: FPDF, df_pen, df_ric, df_ing):
    """Costruisce la pagina 2 (KPI: Penetrazione, Ricordo, Ingaggio)."""
    import PIL.Image

    fill_page_bg(pdf)
    draw_section_band(pdf, "KPI Generali -- Penetrazione - Ricordo - Ingaggio")

    # TOP_N = 8 canali per chart  →  h_px ≈ 22*8+40 = 216px → ~55mm per chart
    # 3 chart × 55mm = 165mm + band 13mm + commenti 3×11mm = 211mm  <<  285mm (FOOTER_Y)
    TOP_N = 8

    sections = [
        (df_pen, "Penetrazione (%)",    "#00A896", "Penetrazione per Canale (%)",        cm.commento_penetrazione),
        (df_ric, "Ricordo (%)",         "#028090", "Ricordo del Messaggio per Canale (%)", cm.commento_ricordo),
        (df_ing, "Ingaggio totale (%)", "#0066CC", "Ingaggio per Canale (%)",             cm.commento_ingaggio),
    ]

    # Spazio disponibile: da y corrente a nota metodologica (FOOTER_Y - 25mm)
    NOTA_Y   = FOOTER_Y - 25   # 260mm — inizio nota metodologica
    GUARD_MM = 20              # margine minimo sotto il chart per commento + spazio

    for df_kpi, col_val, colore, titolo_chart, fn_commento in sections:
        y_cur = pdf.get_y()

        # Guard pre-loop: se siamo già troppo vicini alla nota, interrompi
        if y_cur > NOTA_Y - GUARD_MM:
            break

        # Genera chart PNG
        img_bytes = _safe_chart(ch.chart_barre_kpi, df_kpi, "Canale", col_val,
                                 colore=colore, titolo=titolo_chart, top_n=TOP_N)
        if img_bytes:
            pil = PIL.Image.open(io.BytesIO(img_bytes))
            img_w_px, img_h_px = pil.size
            img_h_mm = CW * img_h_px / img_w_px  # altezza proporzionale in mm

            # Guard post-stima: verifica che chart + commento entrino prima della nota
            if y_cur + img_h_mm + GUARD_MM > NOTA_Y:
                break  # chart non ci sta → interrompi per proteggere nota/footer

            pdf.image(io.BytesIO(img_bytes), x=ML, y=y_cur, w=CW)
            pdf.set_y(y_cur + img_h_mm + 2)
        else:
            write_body(pdf, f"[Grafico {col_val} non disponibile]", "white_40", size=8)

        # Commento strategico
        commento = fn_commento(df_kpi)
        write_body(pdf, commento, "white_70", size=8)
        pdf.ln(3)

    # Nota metodologica — posizione fissa sicura sopra il footer
    pdf.set_y(NOTA_Y)
    write_note(pdf,
        "Penetrazione (%): % HCP raggiunti dal canale sul totale HCP del segmento. "
        "Ricordo (%): % HCP esposti che ricordano il messaggio. "
        "Ingaggio (%): % HCP che hanno interagito/condiviso il contenuto ricevuto."
    )

    add_footer(pdf, 2, TOTAL_PAGES)


# ── Pagina 3: Mappa Canali + Funnel HCP ──────────────────────────────────────

def _pag3_mappa_funnel(pdf: FPDF, df_mappa, df_pen, df_ric, df_ing):
    """Costruisce la pagina 3 (Mappa + Funnel)."""
    fill_page_bg(pdf)
    draw_section_band(pdf, "Mappa Canali + Funnel HCP")

    # ── Mappa scatter ──
    import PIL.Image

    write_label(pdf, "Mappa Canali — Posizionamento Strategico", "teal", size=9)

    img_bytes = _safe_chart(ch.chart_scatter_mappa, df_mappa)
    if img_bytes:
        pil = PIL.Image.open(io.BytesIO(img_bytes))
        iw, ih = pil.size
        img_h_mm = CW * ih / iw
        y_img = pdf.get_y()
        # Guard: non renderizzare se la chart sfonda lo spazio disponibile
        if y_img + img_h_mm + 10 <= FOOTER_Y - 80:
            pdf.image(io.BytesIO(img_bytes), x=ML, y=y_img, w=CW)
            pdf.set_y(y_img + img_h_mm + 2)
        else:
            write_body(pdf, "[Mappa: spazio insufficiente su questa pagina]", "white_40", size=8)
    else:
        write_body(pdf, "[Mappa canali non disponibile]", "white_40", size=8)

    commento_mappa = cm.commento_mappa(df_mappa)
    write_body(pdf, commento_mappa, "white_70", size=8)
    pdf.ln(3)

    # ── Funnel HCP (tabella) ──
    write_label(pdf, "Funnel HCP -- Penetrazione > Ricordo > Ingaggio", "teal", size=9)

    # Costruisci dati funnel dai 3 DataFrame
    funnel_rows = []
    if df_pen is not None and not df_pen.empty:
        for _, row_pen in df_pen.nlargest(8, "Penetrazione (%)").iterrows():
            canale = row_pen["Canale"]
            pen    = row_pen["Penetrazione (%)"]

            ric = None
            if df_ric is not None and not df_ric.empty:
                match_ric = df_ric[df_ric["Canale"] == canale]
                if not match_ric.empty:
                    ric = float(match_ric.iloc[0]["Ricordo (%)"])

            ing = None
            if df_ing is not None and not df_ing.empty:
                match_ing = df_ing[df_ing["Canale"] == canale]
                if not match_ing.empty:
                    ing = float(match_ing.iloc[0]["Ingaggio totale (%)"])

            conv_pr = round(ric / pen * 100, 1) if pen and ric else None
            conv_ri = round(ing / ric * 100, 1) if ric and ing else None

            funnel_rows.append({
                "canale": canale, "pen": pen, "ric": ric, "ing": ing,
                "conv_pen_ric": conv_pr, "conv_ric_ing": conv_ri,
            })

    if funnel_rows:
        headers = ["Canale", "Penetraz. %", "Ricordo %", "Ingaggio %", "Conv P→R %", "Conv R→I %"]
        col_ws  = [55, 24, 24, 24, 26, 27]
        rows_tbl = []
        for r in funnel_rows:
            rows_tbl.append([
                str(r["canale"]),
                f"{r['pen']:.1f}" if r["pen"] is not None else "-",
                f"{r['ric']:.1f}" if r["ric"] is not None else "-",
                f"{r['ing']:.1f}" if r["ing"] is not None else "-",
                f"{r['conv_pen_ric']:.1f}" if r["conv_pen_ric"] is not None else "-",
                f"{r['conv_ric_ing']:.1f}" if r["conv_ric_ing"] is not None else "-",
            ])
        draw_table(pdf, headers, rows_tbl, col_ws)

    # Commento funnel
    commento_fn = cm.commento_funnel(funnel_rows)
    write_body(pdf, commento_fn, "white_70", size=8)

    # Nota metodologica
    pdf.set_y(FOOTER_Y - 18)
    write_note(pdf,
        "Conv P→R%: % degli HCP raggiunti che ricordano il messaggio. "
        "Conv R→I%: % degli HCP che ricordano e si sono ingaggiati. "
        "Quadranti mappa calcolati sulla mediana di Penetrazione e Utilità del campione."
    )

    add_footer(pdf, 3, TOTAL_PAGES)


# ── Pagina 4: OCV ────────────────────────────────────────────────────────────

def _draw_ocv_legend(pdf: FPDF):
    """
    Disegna 4 mini-card orizzontali con la legenda classi OCV + Business Action.
    Altezza totale ~18mm. Ritorna la y finale.
    """
    CLASSES = [
        # (soglia, classe, azione, colore_accent)
        ("OCV >= 20%",        "High Positive OCV",  "Scale / Invest",       C["green_ok"]),
        ("0% <= OCV < 20%",   "Low Positive OCV",   "Test / Optimize",      C["teal"]),
        ("-20% <= OCV < 0%",  "Low Negative OCV",   "Monitor",              C["orange"]),
        ("OCV < -20%",        "High Negative OCV",  "Avoid / Deprioritize", C["red_ko"]),
    ]
    BOX_H  = 18          # altezza mini-card
    GAP    = 2.5         # gap tra card
    box_w  = (CW - GAP * 3) / 4   # ~42.4mm per card

    y0 = pdf.get_y()

    for i, (soglia, classe, azione, col) in enumerate(CLASSES):
        x = ML + i * (box_w + GAP)

        # Sfondo card
        _fc(pdf, "surface_700")
        _dc(pdf, "surface_700")
        pdf.rect(x, y0, box_w, BOX_H, style="F")

        # Barra colorata sinistra (2mm)
        pdf.set_fill_color(*col)
        pdf.rect(x, y0, 2, BOX_H, style="F")

        # Soglia OCV (grigio, 6.5pt)
        _tc(pdf, "white_40")
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(x + 4, y0 + 2.5)
        pdf.cell(box_w - 5, 3.5, _safe_text(soglia))

        # Classe (colore accent, 7.5pt bold)
        pdf.set_text_color(*col)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(x + 4, y0 + 7)
        pdf.cell(box_w - 5, 4, _safe_text(classe))

        # Azione (bianco, 6.5pt, pill simulato con rettangolo sottile)
        _tc(pdf, "white_70")
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(x + 4, y0 + 12.5)
        pdf.cell(box_w - 5, 3.5, _safe_text(azione))

    pdf.set_y(y0 + BOX_H + 3)
    return pdf.get_y()


def _pag4_ocv(pdf: FPDF, df_mix, delta, best, best_impatto=None, n_hcp_total=0):
    """Costruisce la pagina 4 (OCV)."""
    fill_page_bg(pdf)
    draw_section_band(pdf, "OCV — Omnichannel Value: Mix Ottimale dei Canali")

    # ── Legenda classi OCV ──
    _draw_ocv_legend(pdf)

    # ── OCV Delta info box ──
    if delta:
        r1 = delta.get("Recall 1 Channel", 0)
        r3 = delta.get("Recall \u22653 Channels", delta.get("Recall >=3 Channels", 0))
        d  = delta.get("OCV Delta (%)", 0)

        bw2 = (CW - 4) / 2
        y_d = pdf.get_y()
        draw_kpi_box(pdf, ML,          y_d, bw2, 24, "Ricordo (1 Canale)",   f"{r1:.1f}", "%")
        draw_kpi_box(pdf, ML + bw2 + 4, y_d, bw2, 24, "Ricordo (≥3 Canali)",  f"{r3:.1f}", f"% (Δ OCV: {d:+.1f}%)")
        pdf.set_y(y_d + 28)
        pdf.ln(2)

    # ── Chart OCV Mix ──
    write_label(pdf, "Top Mix Canali per OCV (%)", "teal", size=9)

    if df_mix is not None and not df_mix.empty:
        img_bytes = _safe_chart(ch.chart_ocv_mix, df_mix, 8)
        if img_bytes:
            import PIL.Image
            pil = PIL.Image.open(io.BytesIO(img_bytes))
            iw, ih = pil.size
            img_h_mm = CW * ih / iw
            y_img = pdf.get_y()
            pdf.image(io.BytesIO(img_bytes), x=ML, y=y_img, w=CW)
            pdf.set_y(y_img + img_h_mm + 2)
    else:
        write_body(pdf, "[Grafico OCV non disponibile]", "white_40", size=8)

    # ── Tabella: mix di canali più utilizzati nel funnel HCP ──
    # Ordina per N HCP desc → i mix con cui i medici si confrontano più frequentemente
    if df_mix is not None and not df_mix.empty:
        write_label(pdf, "Mix di Canali piu' Utilizzati nel Funnel HCP", "teal", size=9)
        top8 = (df_mix.sort_values("N HCP", ascending=False).head(8))
        has_recall_ass = "Recall Assoluto (%)" in df_mix.columns
        if has_recall_ass:
            headers = ["Mix Canali Funnel", "N HCP", "OCV %", "Rec. Ass. %", "Classe", "Azione"]
            col_ws  = [70, 15, 15, 20, 32, 28]  # tot=180=CW
        else:
            headers = ["Mix Canali Funnel", "N HCP", "OCV %", "Classe", "Azione"]
            col_ws  = [84, 18, 16, 34, 28]       # tot=180=CW
        rows_tbl = []
        for _, row in top8.iterrows():
            mix_str = _norm_mix_str(str(row.get("Channel Mix", "")))
            if has_recall_ass:
                rows_tbl.append([
                    mix_str,
                    str(row.get("N HCP", "-")),
                    f"{row.get('OCV (%)', 0):.1f}%",
                    f"{row.get('Recall Assoluto (%)', 0):.1f}%",
                    str(row.get("OCV Class", "-"))[:20],
                    str(row.get("Business Action", "-"))[:20],
                ])
            else:
                rows_tbl.append([
                    mix_str,
                    str(row.get("N HCP", "-")),
                    f"{row.get('OCV (%)', 0):.1f}%",
                    str(row.get("OCV Class", "-"))[:20],
                    str(row.get("Business Action", "-"))[:20],
                ])
        draw_table(pdf, headers, rows_tbl, col_ws)

    # ── Best mix highlight (OCV massimo + Impatto Reale) ──
    if best and best.get("mix"):
        y_bm = pdf.get_y() + 2

        # Box 1: Mix con OCV massimo
        body_bm = (
            f"Mix: {_norm_mix_str(best['mix'])}\n"
            f"OCV: {best['ocv']:+.1f}%  |  Ricordo mix: {best['recall']:.1f}%\n"
            f"Azione raccomandata: {best['action']}"
        )
        y_after_bm = draw_highlight_box(pdf, ML, y_bm, CW, "MIX OTTIMALE — MAX OCV", body_bm)
        pdf.set_y(y_after_bm + 2)

    # Box 2: Mix con Impatto Reale massimo (Recall Assoluto)
    if best_impatto and best_impatto.get("mix"):
        y_bi = pdf.get_y()
        if y_bi < FOOTER_Y - 55:   # guard: spazio sufficiente
            pen_pct = best_impatto.get("pen_mix", 0)
            rec_ass = best_impatto.get("recall_ass", 0)
            rec_mix = best_impatto.get("recall", 0)
            body_bi = (
                f"Mix: {_norm_mix_str(best_impatto['mix'])}\n"
                f"Reach: {pen_pct:.1f}% HCP  |  Ricordo mix: {rec_mix:.1f}%  |  "
                f"Recall Assoluto: {rec_ass:.1f} su 100 HCP\n"
                f"Azione raccomandata: {best_impatto['action']}"
            )
            y_after_bi = draw_highlight_box(
                pdf, ML, y_bi, CW,
                "MIX OTTIMALE — MAX IMPATTO REALE (Recall Assoluto)", body_bi
            )
            pdf.set_y(y_after_bi)

    # ── Commento OCV ──
    # Guard: scrive commento solo se c'è spazio sufficiente prima della nota
    pdf.ln(2)
    if pdf.get_y() < FOOTER_Y - 45:
        commento = cm.commento_ocv(best or {}, delta)
        write_body(pdf, commento, "white_70", size=8)

    # ── Note metodologiche — posizione fissa sicura sopra footer ──
    pdf.set_y(FOOTER_Y - 25)
    write_note(pdf,
        "OCV%: incremento % del ricordo combinando piu' canali vs media singolo canale. "
        "Recall Assoluto%: (HCP esposti al mix / tot HCP) x Ricordo mix% -- "
        "risponde a 'Su 100 medici, quanti ricordano il messaggio grazie a questo mix?'. "
        "Mix calcolato su combinazioni 2-4 canali con almeno 10 HCP esposti. "
        "Classi e Business Action: vedi legenda in alto a pagina."
    )

    add_footer(pdf, 4, TOTAL_PAGES)


# ── Funzione principale ────────────────────────────────────────────────────────

def genera_report(targets: list[str],
                  aree: list[str] | None = None,
                  patologie: list[str] | None = None) -> io.BytesIO:
    """
    Genera il report PDF Comportamento HCP.

    Args:
        targets:   lista specializzazioni (es. ["Cardiologo"]). Lista vuota = tutti.
        aree:      lista aree terapeutiche canoniche (Q7a). None/[] = nessun filtro.
        patologie: lista patologie (Q7b_*). None/[] = nessun filtro.

    Returns:
        BytesIO con il contenuto PDF pronto per send_file().
    """
    aree      = aree      or []
    patologie = patologie or []

    # ── Carica dati ──
    data    = get_data()
    cols    = data["columns"]
    col_tgt = cols.get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)

    # ── Filtra per area terapeutica / patologie (Q7) ──
    if aree or patologie:
        df_beh, df_perf = _filtra_q7(df_beh, df_perf, aree, patologie)

    # ── Calcola KPI ──
    df_pen   = _norm(kpi_penetrazione(df_beh, cols["canali_11"]))
    df_util  = kpi_utilita(df_beh, cols["canali_utilita"])          # non normalizzare: serve raw per mappa
    df_ric   = _norm(kpi_ricordo_canali(df_perf, cols["canali_perf"]))
    df_ing   = _norm(kpi_ingaggio_canali(df_perf, cols["canali_perf"]))
    df_prop  = kpi_propensione_canali(df_perf, cols["canali_perf"]) # raw per mappa

    # Mappa canali (usa DF originali — normalizzazione interna)
    df_pen_raw  = kpi_penetrazione(df_beh, cols["canali_11"])
    df_mappa    = crea_mappa_canali(df_pen_raw, df_util, df_ing, df_prop)

    # OCV
    channel_cols = cols.get("canali_perf", [])
    recall_col   = cols.get("col_ricordo", "")
    delta        = None
    df_mix       = pd.DataFrame()
    best         = {}
    best_impatto = {}
    n_hcp_total  = int(len(df_perf))

    if channel_cols and recall_col:
        try:
            delta = ocv_delta(df_perf, channel_cols, recall_col)
        except Exception:
            delta = None
        try:
            df_mix = ocv_mix_engine(df_perf, channel_cols, recall_col)
            if not df_mix.empty:
                df_mix["Channel Mix"] = df_mix["Channel Mix"].apply(_norm_mix_str)

                # Recall Assoluto: penetrazione_mix × recall_mix / 100
                # = (N HCP esposti / totale HCP) × Recall Mix%
                if n_hcp_total > 0:
                    df_mix["Recall Assoluto (%)"] = (
                        df_mix["N HCP"] / n_hcp_total * df_mix["Recall Mix (%)"]
                    ).round(1)
                else:
                    df_mix["Recall Assoluto (%)"] = 0.0

                # Best per OCV massimo
                row0 = df_mix.iloc[0]
                best = {
                    "mix":    str(row0.get("Channel Mix", "")),
                    "ocv":    round(float(row0.get("OCV (%)", 0)), 1),
                    "recall": round(float(row0.get("Recall Mix (%)", 0)), 1),
                    "action": str(row0.get("Business Action", "")),
                }

                # Best per Impatto Reale (Recall Assoluto massimo)
                row_i = df_mix.sort_values("Recall Assoluto (%)", ascending=False).iloc[0]
                best_impatto = {
                    "mix":        str(row_i.get("Channel Mix", "")),
                    "recall_ass": round(float(row_i.get("Recall Assoluto (%)", 0)), 1),
                    "recall":     round(float(row_i.get("Recall Mix (%)", 0)), 1),
                    "pen_mix":    round(float(row_i.get("N HCP", 0)) / n_hcp_total * 100, 1)
                                  if n_hcp_total > 0 else 0.0,
                    "n_hcp":      int(row_i.get("N HCP", 0)),
                    "action":     str(row_i.get("Business Action", "")),
                }
        except Exception:
            df_mix = pd.DataFrame()

    # ── Label target ──
    target_label = (
        " · ".join(targets) if targets else "Tutti i target (nessun filtro specializzazione)"
    )
    n_hcp = len(df_beh)

    # ── Crea PDF ──
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(0, 0, 0)

    # Pagina 1
    pdf.add_page()
    _pag1_cover(pdf, target_label, n_hcp, df_pen, df_ric, df_ing,
                aree=aree, patologie=patologie)

    # Pagina 2
    pdf.add_page()
    _pag2_kpi(pdf, df_pen, df_ric, df_ing)

    # Pagina 3
    pdf.add_page()
    _pag3_mappa_funnel(pdf, df_mappa, df_pen, df_ric, df_ing)

    # Pagina 4
    pdf.add_page()
    _pag4_ocv(
        pdf,
        df_mix if not df_mix.empty else None,
        delta, best,
        best_impatto=best_impatto,
        n_hcp_total=n_hcp_total,
    )

    # ── Output ──
    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
