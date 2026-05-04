# FASE 2 — Modulo 1: Comportamento HCP

**Data**: 26 febbraio 2026
**Stato**: ✅ Completata

---

## File creati / modificati

| File | Tipo | Descrizione |
|------|------|-------------|
| `app/data_cache.py` | Nuovo | Cache in-memory thread-safe per DataFrame Excel |
| `app/routes/modulo1.py` | Nuovo | Blueprint completo con 5 route |
| `app/templates/modulo1/index.html` | Nuovo | UI a 4 tab con grafici Plotly dark |
| `src/**/__init__.py` | Nuovi (x10) | Aggiunti package Python mancanti |

---

## Architettura dati corretta (scoperta in debug)

| KPI | DataFrame sorgente | Motivo |
|-----|-------------------|--------|
| Penetrazione, Utilità, Q2 | `df_beh` (Comportamento HCP) | Q11a, Q6, Q2 sono nel file Comportamento |
| Ricordo, Ingaggio, Propensione, NPS, OCV | `df_perf` (Performance Channel) | Q9, Q10, Q13, Q16 sono nel file Performance |

Entrambi i DataFrame vengono filtrati per `col_target` (Specializzazione).

---

## Nomi funzioni reali (vs nomi ipotizzati)

| Modulo Python | Nome funzione corretto |
|---------------|----------------------|
| `kpi_ricordo` | `kpi_ricordo_canali()` |
| `kpi_ingaggio` | `kpi_ingaggio_canali()` |
| `kpi_propensione` | `kpi_propensione_canali()` |
| `kpi_penetrazione` | `kpi_penetrazione()` ✓ |
| `kpi_utilita` | `kpi_utilita()` ✓ |
| `kpi_nps_canali` | `kpi_nps_canali()` ✓ |

---

## Route API implementate

| Route | Metodo | Input | Output |
|-------|--------|-------|--------|
| `/modulo1/` | GET | — | HTML pagina principale |
| `/modulo1/api/meta` | GET | — | Specializzazioni, lista 20 canali |
| `/modulo1/api/kpi` | POST | `{target:[...]}` | 8 KPI + n_hcp + media_ingaggio |
| `/modulo1/api/mappa` | POST | `{target:[...]}` | 20 canali con 4 metriche (scatter) |
| `/modulo1/api/ocv` | POST | `{target:[...]}` | delta + lift curve + mix engine + best |
| `/modulo1/export` | POST | `{target:[...]}` | Excel 9 sheet |

---

## Canali normalizzati via mappa_canali_labels

La `CANALI_MAP` (20 canali) è la fonte di verità unica per tutti i nomi canale. Ogni KPI espone `Canale_std` oltre al nome raw della colonna. Il JavaScript del frontend usa sempre `Canale_std` se disponibile.

---

## Test reali con dati Excel

```
HCP totali: 30.717
Top 3 canali penetrazione:
  ISF Faccia a Faccia: 71.3%
  Sito web prodotto:   37.5%
  Email da ISF:        33.3%
Ricordo: 20 canali
Media ingaggio: 48.1%
Mappa canali: 20 voci
--- TUTTI I TEST PASSATI ---
```

---

## UI — 4 Tab implementate

| Tab | Grafici |
|-----|---------|
| KPI Canali | Penetrazione, Utilità, Ricordo (stacked), Ingaggio (stacked), Propensione (colori NPS), NPS (divergente), Utilità Fasce (stacked), Q2 (donut) |
| Mappe | Scatter Utilità vs Penetrazione, Scatter Ingaggio vs Utilità — con mediane e legenda quadranti |
| OCV | KPI cards (delta, best mix, action), Lift Curve (area), Top 10 OCV (bar), Tabella completa |
| Download | Export Excel 9 sheet con badge info |

---

## Prossimo: FASE 3 — Modulo 2 Performance
