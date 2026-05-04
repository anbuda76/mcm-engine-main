# FASE 2b — Fix: Label Canali Uniformi + Download Excel

**Data**: 26 febbraio 2026
**Stato**: ✅ Completata

---

## Bug risolti

### Bug 1 — Label canali non uniformi nei grafici

**Problema**: I KPI calcolati su `df_perf` (Ricordo, Ingaggio, Propensione, NPS) restituivano i nomi raw delle colonne Excel (`Q9_15 da App tematiche`) invece dei nomi standard (`APP Smartphone`).

**Causa**: `kpi_ricordo_canali()`, `kpi_ingaggio_canali()`, `kpi_propensione_canali()`, `kpi_nps_canali()` non applicano la normalizzazione `CANALI_MAP` — a differenza di `kpi_penetrazione()` che la applica già nel `src/`.

**Soluzione**: Aggiunto `_normalizza_df()` nel blueprint `modulo1.py` come layer di normalizzazione lato server, **senza modificare i file `src/`**:

```python
def _normalizza_df(df):
    """Applica CANALI_MAP a qualsiasi DataFrame con colonna 'Canale'."""
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    if "Canale_std" not in df.columns:
        df["Canale_std"] = df["Canale"].map(CANALI_MAP)
    df["Canale"] = df["Canale_std"].fillna(df["Canale"])
    return df
```

Applicato a: `df_ric`, `df_ing`, `df_prop`, `df_nps`, `df_pen`, `df_util`, `df_fasce` **prima** di `_safe_json()`.

**Attenzione**: `crea_mappa_canali()` deve ricevere i DF **originali** (non normalizzati) perché usa internamente `Canale_std` per il merge. Passando DF già normalizzati (dove `Canale` = nome standard) il merge fallisce silenziosamente.

---

### Bug 2 — Download Excel non funzionava

**Problema**: Il `fetch` blob con `URL.revokeObjectURL()` chiamato immediatamente causava l'annullamento del download prima che il browser lo avesse completato.

**Soluzione**: Sostituito il meccanismo con:
1. Endpoint `export` esteso a `GET` con query params `?target=X&target=Y`
2. JS usa un `<iframe>` hidden: il browser gestisce il download nativamente senza bloccare la pagina

```javascript
const iframe = document.createElement('iframe');
iframe.style.display = 'none';
iframe.src = '/modulo1/export?' + params.toString();
document.body.appendChild(iframe);
setTimeout(() => document.body.removeChild(iframe), 3000);
```

---

## Risultati test finali

```
penetrazione : [ISF Faccia a Faccia]    OK
ricordo      : [APP Smartphone]         OK
ingaggio     : [APP Messaggistica]      OK
propensione  : [APP Messaggistica]      OK
nps          : [Pubblicità cartacee]    OK
utilita      : [ISF Faccia a Faccia]    OK
utilita_fasce: [ISF Faccia a Faccia]    OK
Mappa canali : 20 canali                OK
Export Excel : 68.838 bytes (PK magic)  OK
```

---

## Principio architetturale stabilito

> **`CANALI_MAP` è la fonte di verità unica per i nomi canale.**
> La normalizzazione avviene **nel blueprint** (layer route), non nei file `src/`.
> I file `src/` rimangono invariati e riutilizzabili anche senza Flask.
> Tutti i moduli futuri (Modulo 2, Trend) useranno lo stesso helper `_normalizza_df()`.
