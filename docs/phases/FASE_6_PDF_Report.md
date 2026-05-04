# FASE 6 — PDF Report Modulo 1 (Comportamento HCP)

**Data**: marzo 2026
**Stato**: ✅ Completata

---

## Obiettivo

Aggiungere al Modulo 1 la generazione di un report PDF professionale scaricabile con:
- 4 pagine in dark theme (identico alla piattaforma)
- Grafici Plotly generati server-side come PNG
- Commenti strategici auto-generati (data-driven, nessun LLM)
- Download diretto dal browser via `send_file()`

---

## Stack tecnico

| Componente | Libreria | Note |
|-----------|---------|------|
| Composizione PDF | **FPDF2 ≥2.7.9** | Puro Python, Windows-compatible, nessun dipendenza sistema |
| Font | Helvetica (built-in) | Latin-1 only — usare `_safe_text()` per caratteri speciali |
| Grafici | **Plotly + Kaleido ≥0.2.1** | Chart → PNG bytes, stessa libreria del frontend |
| Commenti | Template data-driven | Threshold-based, no LLM call |

```
requirements.txt:
fpdf2>=2.7.9
kaleido>=0.2.1
```

---

## File creati

| File | Responsabilità |
|------|---------------|
| `app/reports/__init__.py` | Package marker |
| `app/reports/pdf_utils.py` | Costanti colori, LOGO_PATH, helper: `draw_header_band()`, `draw_kpi_box()`, `draw_highlight_box()`, `draw_section_band()`, `add_footer()`, `_safe_text()` |
| `app/reports/charts.py` | Funzioni Plotly→PNG: `chart_barre_kpi()`, `chart_scatter_mappa()`, `chart_ocv_mix()` |
| `app/reports/commenti.py` | Commenti data-driven: `insight_cover()`, `commento_penetrazione()`, `commento_ricordo()`, `commento_ingaggio()`, `commento_mappa()`, `commento_funnel()`, `commento_ocv()` |
| `app/reports/report_comportamento.py` | Orchestratore: `genera_report(targets) → BytesIO` |

## File modificati

| File | Modifica |
|------|----------|
| `app/routes/modulo1.py` | Route `GET/POST /modulo1/export/pdf` con `send_file()` |
| `app/templates/modulo1/index.html` | Bottone "Scarica PDF" nel tab Download |
| `requirements.txt` | Aggiunto fpdf2 e kaleido |

---

## Struttura report (4 pagine)

### Pagina 1 — Cover + Executive Summary
- Header band navy→teal con logo Bhave (w=38mm)
- Titolo "Summary Multichannel Monitoring®" (® superscript simulato a y-2mm)
- Target badge + n. HCP analizzati + data generazione
- 3 KPI box: Penetrazione Media % | Ricordo Medio % | Ingaggio Medio %
- Top 3 canali per penetrazione
- Insight principale auto-generato (6 paragrafi data-driven)

### Pagina 2 — KPI Generali
- 3 grafici barre orizzontali (top 8 canali): Penetrazione | Ricordo | Ingaggio
- Commento strategico per ogni KPI (threshold-based)
- Nota metodologica ancorata a `FOOTER_Y - 25`

### Pagina 3 — Mappa Canali + Funnel HCP
- Scatter plot: asse X = Penetrazione, asse Y = Utilità, size = Ingaggio
- 4 quadranti: Alto Valore / Da Sviluppare / Quick Win / Secondari
- Tabella Funnel 8 canali: Canale | Penetrazione | Ricordo | Ingaggio | Conv%
- Commenti comportamentali

### Pagina 4 — OCV (Omnichannel Value)
- Barre OCV delta: verde se OCV>0 (sinergia), rosso se OCV<0 (saturazione)
- Tabella "Mix di Canali più Utilizzati nel Funnel HCP" (sorted per N HCP desc, top 8)
- Best Mix highlight box (verde teal)
- Raccomandazione strategica multicanale
- Note metodologiche complete

---

## Colori dark theme PDF

```python
COLORS = {
    "bg_page":    (13, 17, 23),    # #0D1117  sfondo pagina
    "surface_800":(22, 27, 39),    # #161B27  card principale
    "surface_700":(28, 35, 51),    # #1C2333  card secondaria
    "surface_600":(33, 41, 61),    # #21293D  card chiara
    "teal":       (0, 168, 150),   # #00A896  accent principale
    "teal_mid":   (2, 128, 144),   # #028090  accent medio
    "navy":       (30, 39, 97),    # #1E2761  navy header
    "green_ok":   (2, 195, 154),   # #02C39A  positivo
    "red_ko":     (229, 62, 62),   # #E53E3E  negativo
    "orange":     (247, 127, 0),   # #F77F00  warning
    "white":      (255, 255, 255),
    "white_70":   (179, 179, 179),
    "white_40":   (102, 102, 102),
}
```

---

## Regole anti-overflow pagina 2 (CRITICO)

La pagina 2 ha 3 grafici a barre consecutivi. Senza guardie, traboccano nel footer.

```python
TOP_N = 8          # max canali per grafico (non 10!)
NOTA_Y = 260       # FOOTER_Y - 25 mm — ancora nota metodologica
GUARD_MM = 20      # margine sicurezza

# Prima del loop grafici:
for df_kpi, ... in sections:
    y_cur = pdf.get_y()
    if y_cur > NOTA_Y - GUARD_MM: break          # guard pre-loop

    img_bytes = _safe_chart(...)
    img_h_mm = CW * img_h_px / img_w_px
    if y_cur + img_h_mm + GUARD_MM > NOTA_Y: break  # guard post-stima

    pdf.image(...)

pdf.set_y(NOTA_Y)  # ancora fissa nota metodologica
```

Formula altezza chart barre: `height = max(150, 22 * n + 40)` pixels
(NON 28px per barra — produce grafici troppo alti)

---

## Logo Bhave

- **File**: `app/static/images/logo-bhave.png` (147×53px RGBA, aspect ratio ~2.77:1)
- **Header cover**: x=155mm, y=13mm, w=38mm → auto h~13.7mm
- **Footer ogni pagina**: w=14mm → auto h~5mm; testo offset +16mm
- **Fallback**: se file assente, `pdf.image()` skippato silenziosamente

```python
_REPORTS_DIR = os.path.dirname(__file__)   # app/reports/
LOGO_PATH = os.path.normpath(
    os.path.join(_REPORTS_DIR, "..", "static", "images", "logo-bhave.png")
)
```

---

## Gestione font Latin-1 (CRITICO)

Helvetica built-in di FPDF2 supporta solo Latin-1. I testi in italiano contengono
caratteri UTF-8 (à, è, ì, ò, ù, –, ®, ...).

```python
_UNICODE_MAP = {
    '\u2013': '-', '\u2014': '--', '\u2019': "'",
    '\u00e0': 'a', '\u00e8': 'e', '\u00ec': 'i',
    '\u00f2': 'o', '\u00f9': 'u', '\u00c9': 'E',
    # ® (U+00AE) è valido Latin-1 → NON rimappare
}

def _safe_text(s: str) -> str:
    for u, r in _UNICODE_MAP.items():
        s = s.replace(u, r)
    return s.encode('latin-1', errors='ignore').decode('latin-1')
```

**® superscript**: FPDF2 non ha superscript nativo. Simulato con cella separata a y-2mm:
```python
pdf.set_font("Helvetica", "", 9)
pdf.set_xy(x_dopo_titolo, y_titolo - 2)   # y-2mm = effetto superscript
pdf.cell(5, 5, "\u00ae")
```

---

## Route download

```python
# app/routes/modulo1.py
@modulo1_bp.route("/export/pdf", methods=["GET", "POST"])
@login_required
def export_pdf():
    targets = request.args.getlist("target") or \
              (request.get_json(silent=True) or {}).get("target", [])
    from app.reports.report_comportamento import genera_report
    buf = genera_report(targets)
    label = "_".join(targets) if targets else "tutti"
    return send_file(buf, as_attachment=True,
                     download_name=f"MCM_Report_Comportamento_{label}.pdf",
                     mimetype="application/pdf")
```

---

## Bug noti e fix

| Bug | Fix |
|-----|-----|
| Grafici pagina 2 si sovrappongono | `top_n=8` + formula `22px×n+40` + dual guard |
| `draw_highlight_box` non ritorna y corretto | Usa sempre il return value: `y = draw_highlight_box(...)` — NON hardcodare `+28` |
| Scatter pagina 3 overflow | Guard pre-render: `if y + img_h_mm + 10 > FOOTER_Y - 80` |
| Font Unicode → UnicodeEncodeError | `_safe_text()` con mappatura + `encode('latin-1', errors='ignore')` |
| ® non visualizzato | U+00AE è Latin-1 valido → non rimappare in `_UNICODE_MAP` |

---

## Verifica post-implementazione

```bash
# 1. pip install fpdf2 kaleido
# 2. venv\Scripts\python run.py → http://localhost:5001
# 3. Login → Modulo 1 → selezionare un target → tab Download
# 4. Click "Scarica PDF" → verifica download nel browser
# 5. Aprire PDF e verificare:
#    - Pag 1: cover con target, KPI box numerici reali, insight
#    - Pag 2: 3 grafici a barre NON sovrapposti, commenti sotto
#    - Pag 3: scatter mappa + tabella funnel
#    - Pag 4: OCV delta + "Mix di Canali più Utilizzati" + best mix box
#    - Ogni pagina: footer con logo Bhave + data generazione
```
