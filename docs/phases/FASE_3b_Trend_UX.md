# FASE 3b — Modulo 3 Trend Temporali: UX Allineata

**Data**: 4 marzo 2026
**Stato**: ✅ Completata

---

## Obiettivo

Allineare il Modulo 3 (Trend Temporali) ai pattern UX di Modulo 1 (Comportamento HCP)
e Modulo 2 (Performance vs Mercato):
- Pattern "Avvia Analisi" con 3 stati pagina
- `MIN_HCP` soglia campione con pannello informativo
- Tooltips `.chart-info` su tutti i grafici
- Sort corretto per barre orizzontali Plotly
- `DOMContentLoaded` init pattern
- Rimozione `alert()` — feedback via status bar inline

---

## File modificati

| File | Tipo modifica |
|------|--------------|
| `app/routes/trend.py` | Aggiunta `MIN_HCP = 20` + check campione insufficiente in `api_kpi()` |
| `app/templates/trend/index.html` | Riscrittura completa — tutti i pattern UX applicati |

---

## Modifiche backend (`trend.py`)

### 1. Aggiunta costante `MIN_HCP`
```python
MIN_HCP = 20  # Soglia minima HCP (coerente con Modulo 1 e 2)
```

### 2. Check campione insufficiente in `api_kpi()`
Aggiunto dopo `df_trend = df_prf.copy()`:
```python
if col_az and col_az in df_trend.columns:
    n_az = int((df_trend[col_az] == azienda).sum())
    if n_az < MIN_HCP:
        return jsonify({
            "insufficient_data": True,
            "n_hcp_az": n_az,
            "azienda":  azienda,
        })
```

---

## Modifiche frontend (`trend/index.html`)

### 1. Header upgraded
**Prima**: titolo semplice con anni + n_canali su una riga.

**Dopo**: header con icona, descrizione ricca, anni/canali evidenziati, badge HCP a destra.

```
[icona trending-up] Trend Temporali per Azienda
                    [descrizione anni disponibili, N canali]
                                              [badge azienda]
[Azienda Focus] [Prodotti] [Specializzazione]
[btn Calcola Trend] [hint / status bar]
```

### 2. Pattern 3 stati pagina
| ID elemento | Quando visibile |
|-------------|----------------|
| `#empty-state` | Prima della prima analisi |
| `#insufficient-state` | Campione < 20 HCP per l'azienda |
| `#tab-container` + grafici | Analisi OK |

**Tab bar**: ora `class="tab-bar hidden"` → appare solo dopo prima analisi.

### 3. Funzioni di stato aggiunte
```javascript
function showResults()                         // nasconde empty/insuf, mostra tab bar
function showInsufficientData(nHcp, azienda)   // mostra pannello warning
function setLoadStatus(text, isOk = true)      // hint→status (check-circle/alert-triangle)
```

### 4. Sort bar chart — fix critico
**Problema**: `renderCanaliAnno()` usava sort **discendente** (`b-a`) per le barre orizzontali
Plotly, che le posizionava in ordine invertito (il valore più alto appariva in basso).

**Fix**: sort **ascendente** (`a-b`) → il valore MAX appare IN CIMA.

```javascript
// PRIMA (errato — max in basso):
const pen = [...].sort((a,b) => (b['Penetrazione (%)'] - a['Penetrazione (%)']));

// DOPO (corretto — max in cima):
const pen = [...].sort((a,b) => (a['Penetrazione (%)'] || 0) - (b['Penetrazione (%)'] || 0));
```

Stessa correzione per il bar chart Ricordo.

### 5. Tooltips `.chart-info` su tutti i grafici

| Grafico | Tooltip |
|---------|---------|
| Penetrazione nel Tempo | "Evoluzione anno per anno della penetrazione media..." |
| Ricordo nel Tempo | "Evoluzione del ricordo medio..." |
| Ingaggio nel Tempo | "Evoluzione dell'engagement medio..." |
| Propensione nel Tempo | "Evoluzione della propensione media al consiglio (0–10)..." |
| NPS nel Tempo | "Net Promoter Score nel tempo: % Promotori meno % Detrattori..." |
| Penetrazione per Canale | "% di HCP raggiunti dall'azienda tramite ogni canale..." |
| Ricordo per Canale | "% di HCP esposti al canale che ricordano..." |
| Heatmap | "Mappa visuale dell'intensità di penetrazione per ogni canale nel tempo..." |

### 6. `DOMContentLoaded` — init consolidato
**Prima**: event listeners aggiunti direttamente in esecuzione (senza wrapper).

**Dopo**: tutti i listener dentro `DOMContentLoaded`:
```javascript
document.addEventListener('DOMContentLoaded', () => {
  initTabs('tab-container');
  lucide.createIcons();
  document.getElementById('btn-load').addEventListener('click', loadData);
  document.getElementById('btn-export').addEventListener('click', downloadExcel);
  document.getElementById('sel-azienda').addEventListener('change', function() {...});
  // Lazy re-render canali su tab click
  document.querySelectorAll('[data-tab="canali"]').forEach(btn => {...});
});
```

### 7. Rimozione `alert()` — feedback inline
**Prima**: `alert("Seleziona un'azienda focus.")`, `alert('Errore: ' + data.error)`, etc.

**Dopo**: `setLoadStatus(text, isOk)` + `console.error()` per logging.

### 8. Download Excel — pulsante allineato
**Prima**: `bg-blue-600` → **Dopo**: `bg-accent` (coerente con Modulo 1/2)

---

## Struttura HTML aggiunta

```
#insufficient-state   — kpi-card warning (clock icon, dati in aggiornamento)
#empty-state          — kpi-card blue (trending-up icon, 6 placeholder icons)
#insuf-badge          — badge warning con "N HCP — Azienda"
#load-hint            — testo guida pre-analisi
#load-status          — status bar (hidden → visibile dopo analisi)
#load-status-icon     — icona dinamica (check-circle / alert-triangle)
#load-status-text     — testo status
```

---

## Note architetturali

- `trend_engine.py` e tutti i file `kpi_*_azienda.py` **non modificati** — logica business intatta
- `export_trend_xls.py` **non modificato**
- Tutte le chiamate API identiche — solo frontend cambiato

---

## Prossimo: completare FASE 3 — Modulo 2 Performance vs Mercato
