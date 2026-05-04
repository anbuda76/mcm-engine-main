# FASE 3 — Modulo 2: Performance vs Mercato

**Data**: 26 febbraio 2026
**Stato**: ✅ Completata

---

## File creati / modificati

| File | Tipo | Descrizione |
|------|------|-------------|
| `app/routes/modulo2.py` | Nuovo | Blueprint completo con 6 route |
| `app/templates/modulo2/index.html` | Nuovo | UI a 4 tab con grafici Plotly dark |
| `src/performance/__init__.py` | Nuovo | Package Python mancante |
| `src/performance/compare/__init__.py` | Nuovo | Package Python mancante |
| `src/performance/mercato/__init__.py` | Nuovo | Package Python mancante |
| `src/performance/market_definition/__init__.py` | Nuovo | Package Python mancante |

---

## Route API implementate

| Route | Metodo | Input | Output |
|-------|--------|-------|--------|
| `/modulo2/` | GET | — | HTML pagina principale |
| `/modulo2/api/meta` | GET | — | Aziende (1647), specializzazioni, 20 canali |
| `/modulo2/api/kpi` | POST | `{azienda, competitors[], target[]}` | Tutti i KPI (pen/ric/ing/prop/nps × az/comp/merc) |
| `/modulo2/api/compare` | POST | `{azienda, competitors[], target[]}` | Tabellone 5 KPI × 3 soggetti |
| `/modulo2/api/canali` | POST | `{azienda, competitors[], target[]}` | 20 canali enhanced (NPS/Prop esposti) |
| `/modulo2/export` | GET/POST | query params o JSON body | Excel multi-sheet |

---

## Bug risolti durante lo sviluppo

### Bug 1 — Ingaggio None nel tabellone
**Causa**: `compare_all_kpi` cerca `"Ingaggio totale (%)"` ma `kpi_ingaggio_azienda/mercato` produce `"Ingaggio (%)"`.
**Fix**: Aggiunto `_add_ingaggio_totale()` nel blueprint che crea il campo alias dopo `_norm_canale()`.

### Bug 2 — KeyError `'ISF Faccia a Faccia'` in compare_channels_enhanced
**Causa**: `compare_channels_enhanced` usa internamente `df_focus[df_focus[canale].notna()]` dove `canale` è il nome normalizzato, ma le colonne del DataFrame sono raw (`Q9_x`).
**Fix**: `_calc_all()` ora mantiene sia le versioni raw (`_raw`) che normalizzate. `api_canali` passa i df raw a `compare_channels_enhanced`, poi normalizza il risultato finale.

### Bug 3 — Propensione/NPS None per Azienda e Mercato
**Causa**: `kpi_propensione_azienda/mercato` restituiscono `dict`, ma `compare_all_kpi.safe_value()` si aspetta un `pd.DataFrame`.
**Fix**: `api_compare` converte i dict in DataFrame 1 riga con `_dict_to_df()` prima di passarli a `compare_all_kpi`.

---

## Principio architetturale confermato

> **Regola `_raw` per compare_channels_enhanced**: la funzione accede a `df_focus[raw_column_name]` — NON deve ricevere df normalizzati.
> Stesso principio di `crea_mappa_canali` in Modulo 1.
>
> **Regola `_dict_to_df`**: le funzioni `kpi_prop_azienda/mercato` ritornano `dict`. Per funzioni che si aspettano `DataFrame`, usare `_dict_to_df()` nel blueprint.

---

## Test reali con dati Excel (PFIZER vs MENARINI, SANOFI)

```
kpi        : [OK] status=200  pen_az=20 righe  n_hcp_az=3569
compare    : [OK] status=200  righe=5  None=nessuno
  Penetrazione (%)        AZ= 18.46  COMP= 13.30  MERC= 15.17
  Ricordo (%)             AZ= 49.04  COMP= 44.88  MERC= 47.41
  Ingaggio (%)            AZ= 39.94  COMP= 38.12  MERC= 38.93
  Propensione media       AZ=  7.45  COMP=  7.66  MERC=  7.57
  NPS                     AZ=  3.20  COMP=  8.50  MERC=  6.00
canali     : [OK] status=200  righe=20
export     : [OK] status=200  size=21,226 bytes  PK=True (valid XLSX)
--- TUTTI I TEST PASSATI ---
```

---

## UI — 4 Tab implementate

| Tab | Contenuto |
|-----|-----------|
| KPI Comparativi | Bar chart Penetrazione/Ricordo/Ingaggio per Azienda/Mercato + grouped bar Competitor |
| Tabellone | Radar comparativo 5 KPI (scala 0-100 omogenea) + tabella con Δ vs Mercato |
| Canali Enhanced | Scatter NPS vs Penetrazione per canale + bar Focus vs Mercato + tabella 20 canali × 13 metriche |
| Download | Export Excel con sheet per ogni KPI × soggetto |

---

## Prossimo: FASE 4 — Modulo 3 Trend Temporali
