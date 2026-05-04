"""
app/reports/pdf_utils.py
─────────────────────────
Costanti colori, font e funzioni helper per report PDF dark theme MCM Engine.
Tema dark identico alla piattaforma web (custom.css).
"""

import os

from fpdf import FPDF
from datetime import datetime

# ── Path logo Bhave ──────────────────────────────────────────────────────────
# File atteso:  app/static/images/logo-bhave.png
# Il report lo carica automaticamente se presente (fallback silenzioso se assente).
_REPORTS_DIR = os.path.dirname(__file__)   # app/reports/
LOGO_PATH = os.path.normpath(
    os.path.join(_REPORTS_DIR, "..", "static", "images", "logo-bhave.png")
)

# ── Colori dark theme (identici a CSS custom.css) ──────────────────────────
C: dict[str, tuple] = {
    "bg_page":     (13,  17,  23),   # #0D1117  sfondo pagina
    "surface_800": (22,  27,  39),   # #161B27  card principale
    "surface_700": (28,  35,  51),   # #1C2333  card secondaria
    "surface_600": (33,  41,  61),   # #21293D  card chiara
    "teal":        (0,  168, 150),   # #00A896  accent principale
    "teal_mid":    (2,  128, 144),   # #028090  accent medio
    "navy":        (30,  39,  97),   # #1E2761  navy header
    "green_ok":    (2,  195, 154),   # #02C39A  positivo
    "red_ko":      (229, 62,  62),   # #E53E3E  negativo
    "orange":      (247, 127,  0),   # #F77F00  warning
    "white":       (255, 255, 255),
    "white_70":    (179, 179, 179),  # ~70% opacity su dark
    "white_50":    (128, 128, 128),  # ~50%
    "white_40":    (102, 102, 102),  # ~40%
    "white_20":    (51,  51,  51),   # ~20%
}

# ── Layout A4 ───────────────────────────────────────────────────────────────
PW, PH  = 210, 297   # page width/height mm
ML = MR = 15          # margini laterali
MT      = 15          # margine top
MB      = 18          # margine bottom (più alto per footer)
CW      = PW - ML - MR   # 180mm content width
FOOTER_Y = PH - 12        # y-coordinata inizio footer


# ── Sanitizzazione testo (Latin-1 safe per Helvetica built-in) ───────────────
_UNICODE_MAP = [
    ('\u2014', '--'),    # em dash —
    ('\u2013', '-'),     # en dash –
    ('\u2012', '-'),     # figure dash
    ('\u2011', '-'),     # non-breaking hyphen
    ('\u2192', '->'),    # right arrow →
    ('\u2190', '<-'),    # left arrow ←
    ('\u2193', 'v'),     # down arrow ↓
    ('\u2191', '^'),     # up arrow ↑
    ('\u2265', '>='),    # greater or equal ≥
    ('\u2264', '<='),    # less or equal ≤
    ('\u2248', '~'),     # almost equal ≈
    ('\u2260', '!='),    # not equal ≠
    ('\u00D7', 'x'),     # multiplication sign ×
    ('\u203A', '>'),     # single right angle ›
    ('\u2039', '<'),     # single left angle ‹
    ('\u2018', "'"),     # left single quotation '
    ('\u2019', "'"),     # right single quotation '
    ('\u201C', '"'),     # left double quotation "
    ('\u201D', '"'),     # right double quotation "
    ('\u2022', '-'),     # bullet •
    ('\u00A0', ' '),     # non-breaking space
    ('\u2026', '...'),   # ellipsis …
    # Lettere greche comuni nei KPI
    ('\u0394', 'Delta'), # Δ (delta maiuscolo)
    ('\u03B4', 'delta'), # δ (delta minuscolo)
    ('\u03B1', 'alpha'), # α
    ('\u03B2', 'beta'),  # β
    ('\u03C3', 'sigma'), # σ
    ('\u03BC', 'mu'),    # μ
    ('\u03C0', 'pi'),    # π
]


def _safe_text(text) -> str:
    """
    Sanitizza il testo per la compatibilità Latin-1 (font Helvetica built-in di FPDF2).
    1. Sostituisce i caratteri noti con equivalenti ASCII leggibili.
    2. Fallback: qualsiasi altro carattere fuori Latin-1 viene rimosso.
    """
    if not isinstance(text, str):
        text = str(text)
    for char, replacement in _UNICODE_MAP:
        text = text.replace(char, replacement)
    # Fallback universale: rimuove caratteri non codificabili in Latin-1
    text = text.encode('latin-1', errors='ignore').decode('latin-1')
    return text


# ── Shortcut colori ─────────────────────────────────────────────────────────

def _fc(pdf: FPDF, key: str):
    """Set fill color dalla palette."""
    pdf.set_fill_color(*C[key])


def _tc(pdf: FPDF, key: str):
    """Set text color dalla palette."""
    pdf.set_text_color(*C[key])


def _dc(pdf: FPDF, key: str):
    """Set draw color dalla palette."""
    pdf.set_draw_color(*C[key])


# ── Sfondo pagina ────────────────────────────────────────────────────────────

def fill_page_bg(pdf: FPDF):
    """Riempie l'intera pagina con sfondo dark #0D1117."""
    _fc(pdf, "bg_page")
    pdf.rect(0, 0, PW, PH, style="F")


# ── Header cover (pagina 1) ──────────────────────────────────────────────────

def draw_header_band(pdf: FPDF, title: str, subtitle: str):
    """
    Banner pagina 1: sfondo navy 44mm con striscia teal in basso (4mm)
    e barra teal verticale sinistra (4mm).
    Mostra il logo Bhave in alto a destra se il file è presente in app/static/img/.
    """
    title    = _safe_text(title)
    subtitle = _safe_text(subtitle)

    # Sfondo navy
    _fc(pdf, "navy")
    pdf.rect(0, 0, PW, 44, style="F")
    # Striscia teal in basso
    _fc(pdf, "teal")
    pdf.rect(0, 40, PW, 4, style="F")
    # Barra decorativa sinistra
    pdf.rect(0, 0, 4, 44, style="F")

    # Logo Bhave — angolo superiore destro dell'header
    # Logo 147×53px → aspect ~2.77:1 (orizzontale)
    # Usiamo w=38mm → h = 38 × 53/147 ≈ 13.7mm, ben visibile nel band di 44mm
    _logo_w = 38
    _logo_x = PW - MR - _logo_w - 2   # x = 210-15-38-2 = 155mm
    _logo_y = 13                        # centrato verticalmente nel band (0-40mm)
    _has_logo = False
    if os.path.isfile(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=_logo_x, y=_logo_y, w=_logo_w)
            _has_logo = True
        except Exception:
            pass  # logo non supportato: continua senza

    # Titolo — larghezza adattata se logo presente (lascia 45mm liberi a destra)
    _title_w = CW - 48 if _has_logo else CW
    _tc(pdf, "white")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(ML + 6, 9)
    pdf.cell(_title_w, 10, title, ln=True)

    # Sottotitolo
    _tc(pdf, "white_70")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(ML + 6, 22)
    pdf.cell(_title_w, 6, subtitle)


# ── Banner sezione (pagine 2-4) ──────────────────────────────────────────────

def draw_section_band(pdf: FPDF, title: str, y: float | None = None):
    """
    Banner sezione per pagine 2-4: sfondo surface_700 con barra teal sinistra.
    Altezza 11mm. Se y=None usa MT.
    """
    title = _safe_text(title)

    if y is None:
        y = MT - 2

    _fc(pdf, "surface_700")
    pdf.rect(0, y, PW, 11, style="F")
    _fc(pdf, "teal")
    pdf.rect(0, y, 4, 11, style="F")

    _tc(pdf, "white")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(ML + 6, y + 2)
    pdf.cell(CW, 7, title.upper())

    pdf.set_y(y + 13)


# ── Card generica ────────────────────────────────────────────────────────────

def draw_card(pdf: FPDF, x: float, y: float, w: float, h: float,
              color: str = "surface_800", border: bool = True):
    """Rettangolo card dark con bordo teal sottile opzionale."""
    _fc(pdf, color)
    if border:
        _dc(pdf, "teal")
        pdf.set_line_width(0.2)
        pdf.rect(x, y, w, h, style="FD")
    else:
        pdf.rect(x, y, w, h, style="F")


# ── KPI box (cover) ───────────────────────────────────────────────────────────

def draw_kpi_box(pdf: FPDF, x: float, y: float, w: float, h: float,
                 label: str, value: str, unit: str = ""):
    """
    Box KPI: card dark surface_700 con:
      - barra accent teal top (1.5mm)
      - label piccola in alto
      - valore grande (teal)
      - unità opzionale sotto
    """
    label = _safe_text(label)
    value = _safe_text(value)
    unit  = _safe_text(unit)

    draw_card(pdf, x, y, w, h, "surface_700")
    # Barra accent top
    _fc(pdf, "teal")
    pdf.rect(x, y, w, 1.5, style="F")
    # Label
    _tc(pdf, "white_40")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_xy(x + 3, y + 4)
    pdf.cell(w - 6, 4, label.upper())
    # Valore
    _tc(pdf, "teal")
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_xy(x + 3, y + 9)
    pdf.cell(w - 6, 9, str(value))
    # Unità
    if unit:
        _tc(pdf, "white_70")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_xy(x + 3, y + 19)
        pdf.cell(w - 6, 4, unit)


# ── Box highlight (best mix, insight) ───────────────────────────────────────

def draw_highlight_box(pdf: FPDF, x: float, y: float, w: float,
                       title: str, body: str) -> float:
    """
    Box evidenziato teal_mid.
    Ritorna la y finale (y + altezza effettiva).
    """
    title = _safe_text(title)
    body  = _safe_text(body)

    # Stima altezza per multi_cell (approssimata)
    lines = max(1, len(body) // 90 + body.count("\n") + 1)
    h = 8 + lines * 4.5

    _fc(pdf, "teal_mid")
    _dc(pdf, "teal")
    pdf.set_line_width(0.4)
    pdf.rect(x, y, w, h, style="FD")
    # Barra top
    _fc(pdf, "teal")
    pdf.rect(x, y, w, 2, style="F")

    _tc(pdf, "white")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(x + 3, y + 4)
    pdf.cell(w - 6, 5, title)

    _tc(pdf, "white")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(x + 3, y + 10)
    pdf.multi_cell(w - 6, 4, body)

    return y + h + 2


# ── Testo corpo ───────────────────────────────────────────────────────────────

def write_body(pdf: FPDF, text: str, color: str = "white_70",
               size: float = 8.5, indent: float = 0) -> float:
    """
    Scrive un paragrafo di testo con word wrap.
    Ritorna la nuova y corrente.
    """
    text = _safe_text(text)
    _tc(pdf, color)
    pdf.set_font("Helvetica", "", size)
    pdf.set_x(ML + indent)
    pdf.multi_cell(CW - indent, 4.2, text)
    pdf.ln(2)
    return pdf.get_y()


def write_note(pdf: FPDF, text: str) -> float:
    """Testo nota metodologica: piccolo, corsivo, bianco 40%."""
    text = _safe_text(text)
    _tc(pdf, "white_40")
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_x(ML)
    pdf.multi_cell(CW, 3.8, text)
    pdf.ln(1.5)
    return pdf.get_y()


def write_label(pdf: FPDF, text: str, color: str = "teal",
                size: float = 10, bold: bool = True) -> float:
    """Label titolo sotto-sezione."""
    text = _safe_text(text)
    _tc(pdf, color)
    pdf.set_font("Helvetica", "B" if bold else "", size)
    pdf.set_x(ML)
    pdf.cell(CW, 6, text, ln=True)
    pdf.ln(1)
    return pdf.get_y()


# ── Tabella dati ─────────────────────────────────────────────────────────────

def draw_table(pdf: FPDF, headers: list[str], rows: list[list[str]],
               col_widths: list[float] | None = None) -> float:
    """
    Tabella con header teal + righe alternate surface_700/surface_800.
    headers: lista stringhe intestazioni
    rows: lista di liste (una lista per riga)
    col_widths: larghezze colonne in mm (somma deve essere ~CW). Default: equali.
    """
    if col_widths is None:
        cw = CW / len(headers)
        col_widths = [cw] * len(headers)

    # Sanitizza header e celle
    headers = [_safe_text(h) for h in headers]
    rows    = [[_safe_text(c) for c in row] for row in rows]

    row_h = 6.5
    header_h = 7.5

    # Header row
    _fc(pdf, "teal")
    pdf.set_fill_color(*C["teal"])
    x_start = ML
    y_start = pdf.get_y()

    _tc(pdf, "white")
    pdf.set_font("Helvetica", "B", 8)
    x = x_start
    for i, h in enumerate(headers):
        pdf.set_xy(x, y_start)
        pdf.cell(col_widths[i], header_h, str(h), border=0, fill=True)
        x += col_widths[i]
    pdf.ln(header_h)

    # Data rows
    pdf.set_font("Helvetica", "", 7.5)
    for ri, row in enumerate(rows):
        bg = "surface_700" if ri % 2 == 0 else "surface_800"
        _fc(pdf, bg)
        y_row = pdf.get_y()
        # Riempi sfondo intera riga
        pdf.rect(ML, y_row, CW, row_h, style="F")
        # Testo celle
        _tc(pdf, "white_70")
        x = x_start
        for i, cell in enumerate(row):
            pdf.set_xy(x, y_row)
            # FPDF cell() clippa automaticamente il testo alla larghezza della cella
            pdf.cell(col_widths[i], row_h, str(cell), border=0, fill=False)
            x += col_widths[i]
        pdf.ln(row_h)

    # Linea bordo bottom
    _dc(pdf, "teal")
    pdf.set_line_width(0.3)
    pdf.line(ML, pdf.get_y(), ML + CW, pdf.get_y())
    pdf.ln(2)
    return pdf.get_y()


# ── Footer ────────────────────────────────────────────────────────────────────

def add_footer(pdf: FPDF, page_num: int, total_pages: int = 4):
    """Footer su ogni pagina: logo (se presente) + fonte dati + data + numero pagina."""
    # Linea separatrice teal
    _dc(pdf, "teal")
    pdf.set_line_width(0.3)
    pdf.line(ML, FOOTER_Y, PW - MR, FOOTER_Y)

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    _tc(pdf, "white_40")
    pdf.set_font("Helvetica", "", 6.5)

    # Logo nel footer — piccolo (w=14mm ≈ h5mm per logo 147x53px), allineato a sinistra
    # Logo 147x53px → aspect ~2.77:1; con w=14 → h ≈ 5mm
    _logo_footer_w = 14
    _logo_offset   = 0   # offset x aggiuntivo per il testo se logo presente
    if os.path.isfile(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=ML, y=FOOTER_Y + 1.5, w=_logo_footer_w)
            _logo_offset = _logo_footer_w + 2   # 16mm di spazio riservato al logo
        except Exception:
            pass

    # Testo footer — spostato a destra se logo presente
    pdf.set_xy(ML + _logo_offset, FOOTER_Y + 2.5)
    pdf.cell(
        CW - 25 - _logo_offset, 4,
        f"Fonte dati: BHAVE Platform -- MCM Engine  |  Generato il: {now_str}"
    )
    pdf.set_x(PW - MR - 25)
    pdf.cell(25, 4, f"Pagina {page_num} / {total_pages}", align="R")
