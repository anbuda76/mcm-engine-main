# FASE 2c — UX Miglioramenti Modulo 1: Comportamento HCP

**Data**: 4 marzo 2026
**Stato**: ✅ Completata

---

## Obiettivo

Migliorare l'esperienza utente del Modulo 1 con: pattern "Avvia Analisi", riorganizzazione
KPI summary, miglioramento sezione OCV, tooltips informativi, gestione campioni piccoli.

---

## Modifiche implementate

### 1. Header con pattern "Avvia Analisi"

**Prima**: caricamento automatico al mount della pagina.
**Dopo**: filtri → pulsante "Avvia Analisi" → analisi su richiesta.

Struttura header:
```
[icona] Comportamento HCP per Canale
        [descrizione 20 canali, segmenta per specializzazione]
        [filtro Specializzazione] [Area Terapeutica — coming soon] [spacer]
        [btn Avvia Analisi]  [hint / status bar]
        [badge X HCP — in alto a destra]
```

3 stati pagina (gestiti via JS):
| ID elemento | Quando visibile |
|-------------|----------------|
| `#empty-state` | Prima della prima analisi |
| `#insufficient-state` | Campione < 20 HCP |
| `#tab-container` + grafici | Analisi OK |

---

### 2. KPI Summary Bar riorganizzata

Ordine cambiato: rimossa "HCP Analizzati", aggiunta "Media Propensione":

| # | Metrica | Elemento | Fonte |
|---|---------|----------|-------|
| 1 | Media Penetrazione | `#sum-pen` | media `Penetrazione (%)` |
| 2 | Media Ingaggio | `#sum-ing` | `media_ingaggio` da attrs DataFrame |
| 3 | Media Propensione | `#sum-prop` | media `Probabilità media consiglio` |
| 4 | Top Canale | `#sum-top` | canale con max Penetrazione |

---

### 3. Rimozione grafico Q2 (Distribuzione Comunicazione Aziendale)

Grafico donut Q2 rimosso dalla Tab KPI. Grafico "Utilità Fasce" promosso a full width.

---

### 4. Sort grafici — regola definitiva

Plotly horizontal bars: indice 0 = **bottom** del grafico.
**Regola**: sort JS **ascendente** (`a - b`) → il valore MAX è l'ultimo array → appare IN CIMA.

```javascript
// CORRETTO — max in cima per barre orizzontali Plotly
const rows = [...data].sort((a, b) => a['Metrica (%)'] - b['Metrica (%)']);
```

---

### 5. Tooltips sui titoli dei grafici (`.chart-info`)

Pattern CSS-only aggiunto in `custom.css`:

```html
<div class="chart-title">
  <i data-lucide="signal" class="w-3.5 h-3.5 text-accent"></i>
  Titolo Grafico
  <span class="chart-info">
    <i data-lucide="info"></i>
    <span class="tip">Testo descrittivo tooltip...</span>
  </span>
  <span class="ml-auto badge badge-muted">Q11a</span>
</div>
```

CSS in `custom.css`: `.chart-info` con `position:relative`, `.tip` con `position:absolute;
top:calc(100%+8px); opacity:0; visibility:hidden` → visibile su hover.

Applicato a **tutti i grafici** di Tab 1 (KPI), Tab 2 (Mappe), Tab 3 (OCV).

---

### 6. Sezione OCV completamente ridisegnata

**Rimosso**: Lift Curve (grafico area ricordo vs n. canali)
**Rimosso**: grafico Q2 da Tab KPI

**Aggiunto**: Top 10 per Frequenza (N HCP) — nuovo chart e colonna in `api_ocv()`

#### Struttura Tab OCV
```
[4 KPI cards: Recall 1ch | Recall ≥3ch | Δ OCV | Best Mix Action]
[Best Combo card — full width — con nome mix normalizzato]
[Top10 OCV %  (chart) | Top10 Frequenza N Medici (chart)]
[Tabella top 10 per N HCP — ordine frequenza]
```

#### Backend OCV (`modulo1.py`)
```python
# Normalizzazione Channel Mix: Q9_xx → nomi leggibili
def _normalizza_mix_str(mix_str: str) -> str:
    parts = str(mix_str).split(" + ")
    return " + ".join(CANALI_MAP.get(p.strip(), p.strip()) for p in parts)

# In api_ocv():
if not df_mix.empty:
    df_mix["Channel Mix"] = df_mix["Channel Mix"].apply(_normalizza_mix_str)
top10_ocv  = df_mix.head(10)
top10_freq = df_mix.sort_values("N HCP", ascending=False).head(10)
return jsonify({"delta": delta, "mix": _safe_json(top10_ocv),
                "top10_freq": _safe_json(top10_freq), "best": best})
```

#### Chiavi delta OCV (attenzione JS)
```javascript
const d = ocv.delta || {};
d['Recall 1 Channel']    // NON d.recall_single
d['Recall ≥3 Channels']  // NON d.recall_multi
d['OCV Delta (%)']       // NON d.delta_pp
```

---

### 7. Gestione campione insufficiente

**Soglia**: `MIN_HCP = 20` in `modulo1.py`

**Backend** (`api_kpi()`):
```python
n_beh  = int(len(df_beh))
n_perf = int(len(df_perf))
if n_beh < MIN_HCP or n_perf < MIN_HCP:
    return jsonify({"insufficient_data": True, "n_hcp": n_beh, "n_perf": n_perf})
```

**Frontend** (`loadAll()`):
```javascript
if (kpiData.insufficient_data) {
  showInsufficientData(kpiData.n_hcp, targets);
  return; // nessun grafico renderizzato
}
```

**Pannello `#insufficient-state`**:
- Icona `clock` arancione (`text-warning`)
- Titolo: "Dati in aggiornamento incrementale"
- Badge: "X medici rilevati"
- Nota: "Soglia minima per l'analisi: 20 HCP"
- Status bar: icona `alert-triangle` arancione, testo "Campione insufficiente · SPEC"

---

### 8. Bug fix KeyError nei KPI con lista vuota

**Root cause**: `pd.DataFrame([]).sort_values("ColName")` → `KeyError` se lista risultati vuota.

**File corretti** (tutti con stesso pattern):

| File | Guard aggiunto |
|------|---------------|
| `kpi_nps_canali.py` | `if not results: return pd.DataFrame(columns=[...])` |
| `kpi_utilita.py` | `if not risultati: return pd.DataFrame(columns=[...])` |
| `kpi_utilita_fasce.py` | `if not risultati: return pd.DataFrame(columns=[...])` |
| `kpi_ricordo.py` | `if not risultati: return pd.DataFrame(columns=[...])` |
| `kpi_ingaggio.py` | `if not risultati: return empty (con attrs["media_ingaggio"]=0.0)` |
| `kpi_propensione.py` | `if not risultati: return pd.DataFrame(columns=[...])` |

Nota: `kpi_nps_canali.py` usa anche `na_position="last"` nel sort per gestire NPS=None.

---

## File modificati in questa fase

| File | Tipo modifica |
|------|--------------|
| `app/templates/modulo1/index.html` | Refactor completo header, KPI bar, Tab OCV, JS |
| `app/routes/modulo1.py` | MIN_HCP, api_kpi early-exit, api_ocv top10_freq + normalizzazione |
| `app/static/css/custom.css` | Aggiunta classe `.chart-info` con tooltip CSS |
| `src/behavior/kpi_nps_canali.py` | Guard lista vuota + na_position |
| `src/behavior/kpi_utilita.py` | Guard lista vuota |
| `src/behavior/kpi_utilita_fasce.py` | Guard lista vuota |
| `src/behavior/kpi_ricordo.py` | Guard lista vuota |
| `src/behavior/kpi_ingaggio.py` | Guard lista vuota + attrs empty |
| `src/behavior/kpi_propensione.py` | Guard lista vuota |

---

## Prossimo: FASE 3 — Modulo 2 Performance vs Mercato
