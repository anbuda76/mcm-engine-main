# FASE 2d — Funnel HCP: Customer Journey Visualization

**Data**: 4 marzo 2026
**Stato**: ✅ Completata

---

## Obiettivo

Aggiungere al Modulo 1 una nuova tab **"Funnel HCP"** che mostri il percorso del medico
attraverso gli stadi del funnel di marketing (Reach → Ricordo → Ingaggio → Alta Propensione),
combinando tre visualizzazioni complementari.

---

## File modificati

| File | Tipo modifica |
|------|--------------|
| `app/templates/modulo1/index.html` | Tab button + HTML panel + JS funnel functions |

**Nessun file backend modificato** — tutti i calcoli sono JS-side su dati già caricati.

---

## Architettura: Zero API aggiuntive

Il Funnel usa esclusivamente dati già presenti in memoria dopo `loadAll()`:

| Sorgente dati | Utilizzo |
|---|---|
| `kpiData.penetrazione` | N_exposed per canale (pen_pct × n_hcp) |
| `kpiData.ricordo` | N_recall per canale (ric_pct × n_hcp) |
| `kpiData.ingaggio` | N_engaged per canale (ing_pct × n_hcp) |
| `kpiData.nps` | N_prop_high: Promoters+Passives (% con score ≥7) |
| `kpiData.n_hcp` | Base totale HCP analizzati |
| `ocvData.top10_freq` | Best Path cards (mix OCV per frequenza) |

### Calcoli funnel (JS)

```javascript
N_exposed   = round(n_hcp × pen_pct / 100)
N_recall    = round(n_hcp × ric_pct / 100)
N_engaged   = round(n_hcp × ing_pct / 100)
N_prop_high = round(N_exposed × (Promoters% + Passives%) / 100)
```

`Promoters% + Passives%` viene da `kpiData.nps` per canale → rappresenta la quota
di HCP esposti con propensione ≥7 (NPS: Promotori score 9-10 + Passivi score 7-8).

---

## Struttura Tab Funnel HCP

```
[Intro card — descrizione customer journey + legenda colori]
[Funnel Matrix — stacked horizontal bar 4 stadi × tutti i canali]
[Sankey Flow — Top 8 canali × Ricordo × Ingaggio × Propensione]
[Best Path — 6 cards mix OCV per frequenza HCP]
```

---

## Funzioni JavaScript aggiunte

### `hexToRgba(hex, alpha)`
Converte colori hex (es. `#00A896`) in `rgba(0,168,150,alpha)`.
Necessario per i link Sankey semi-trasparenti.

### `buildFunnelData()`
Costruisce array di oggetti `{ canale, N_exposed, N_recall, N_engaged, N_prop_high }`
unendo i lookup map da penetrazione, ricordo, ingaggio, nps.
Filtra canali con `N_exposed === 0`.

### `renderFunnelMatrix(rows)`
**Stacked horizontal bar** — 4 segmenti per canale:

| Segmento | Valore | Colore |
|---|---|---|
| Alta Propensione ≥7 | `N_prop_high` | `C.success` (#02C39A) |
| Ingaggiati (escl. alta prop.) | `N_engaged - N_prop_high` | `C.warning` (#F77F00) |
| Ricordano (non ingaggiati) | `N_recall - N_engaged` | `C.blue` (#60a5fa) |
| Solo raggiunti | `N_exposed - N_recall` | `rgba(255,255,255,0.11)` |

Sort: **ascending** (`a.N_exposed - b.N_exposed`) → canale con più reach **in cima**.

### `renderSankey(rows)`
**Plotly Sankey** con 14 nodi:

```
Nodi 0-7:  Top 8 canali per N_exposed (colori PALETTE)
Nodo 8:    "Non ricordano" (grigio)
Nodo 9:    "Ricordano" (blu)
Nodo 10:   "Non ingaggiati" (grigio)
Nodo 11:   "Ingaggiati" (warning)
Nodo 12:   "Bassa Propensione" (grigio)
Nodo 13:   "Alta Propensione ≥7" (success)
```

Links:
- Ogni canale i → Ricordano (N_recall_i, colore PALETTE semi-trasparente)
- Ogni canale i → Non ricordano (N_exposed_i - N_recall_i, grigio 5%)
- Ricordano → Ingaggiati (totale aggregato top-8)
- Ricordano → Non ingaggiati
- Ingaggiati → Alta Propensione (totale aggregato)
- Ingaggiati → Bassa Propensione

### `renderBestPath()`
Grid di 6 cards da `ocvData.top10_freq`.
Ogni card mostra: rank, badge canali, N medici, OCV%, Business Action.

### `renderFunnel()`
Master function con flag `funnelRendered`:
```javascript
function renderFunnel() {
  if (funnelRendered) return; // non ri-renderizza con stessi dati
  const rows = buildFunnelData();
  if (!rows.length) return;
  renderFunnelMatrix(rows);
  renderSankey(rows);
  renderBestPath();
  funnelRendered = true;
}
```

---

## Pattern Lazy Load

Il tab Funnel è **lazy**: non si renderizza al caricamento della pagina ma
**solo al primo click** sul tab, quando i div sono già visibili nel DOM.

```javascript
// In DOMContentLoaded:
document.querySelector('[data-tab="funnel"]').addEventListener('click', () => {
  if (kpiData && !kpiData.error && !kpiData.insufficient_data) {
    setTimeout(renderFunnel, 0); // defer → Plotly misura dimensioni DOM correttamente
  }
});
```

Il flag `funnelRendered` viene **resettato a `false`** in `loadAll()` dopo `showResults()`,
così a ogni nuova analisi il funnel si ri-renderizza con i dati aggiornati.

---

## HTML IDs aggiunti

| ID | Tipo | Contenuto |
|----|------|-----------|
| `#tab-funnel` | `div.tab-panel` | Panel principale tab |
| `#chart-funnel-matrix` | `div` | Plotly Funnel Matrix (540px) |
| `#chart-funnel-sankey` | `div` | Plotly Sankey (500px) |
| `#funnel-best-path` | `div.grid` | Container cards Best Path |

---

## Prossimo: continuare FASE 3 — Modulo 2 Performance vs Mercato
