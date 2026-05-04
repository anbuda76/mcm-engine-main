# FASE 0 + FASE 1 — Setup Struttura e Scheletro Flask

**Data completamento**: 26 febbraio 2026
**Stato**: ✅ Completata

---

## Cosa è stato fatto

### FASE 0 — Setup progetto
- [x] Creata struttura directory `MCM_ENGINE_FLASK/` completa
- [x] Copiato `src/` integralmente (37 file Python — logica di business invariata)
- [x] Copiato `data_raw/` (2 file Excel)
- [x] Rimossi file `*.txt` spurii da `src/`
- [x] Creato `requirements.txt` con dipendenze Flask
- [x] Creato `.gitignore` e `.env.example`
- [x] Creato `config/__init__.py` (DevelopmentConfig / ProductionConfig)
- [x] Creato `venv/` Flask e installate dipendenze
- [x] **Verifica**: `from app import create_app` → OK, 6 route registrate

### FASE 1 — Scheletro Flask
- [x] `app/__init__.py` — Application Factory pattern
- [x] `app/routes/dashboard.py` — Blueprint `/`
- [x] `app/routes/modulo1.py` — Blueprint `/modulo1`
- [x] `app/routes/modulo2.py` — Blueprint `/modulo2`
- [x] `app/routes/trend.py` — Blueprint `/trend`
- [x] `app/routes/api.py` — Blueprint `/api` con `/api/health`
- [x] `run.py` — Entry point Flask
- [x] `app/templates/base.html` — Layout master con sidebar Tailwind
- [x] Template placeholder per: dashboard, modulo1, modulo2, trend
- [x] `app/static/css/custom.css` — CSS personalizzato
- [x] `app/static/js/main.js` — JS globale (tabs, Plotly render, fetch helper)

---

## Struttura file creata

```
MCM_ENGINE_FLASK/
├── app/
│   ├── __init__.py              ✅ Application Factory
│   ├── routes/
│   │   ├── __init__.py          ✅
│   │   ├── dashboard.py         ✅ Route /
│   │   ├── modulo1.py           ✅ Route /modulo1
│   │   ├── modulo2.py           ✅ Route /modulo2
│   │   ├── trend.py             ✅ Route /trend
│   │   └── api.py               ✅ Route /api
│   ├── static/
│   │   ├── css/custom.css       ✅
│   │   └── js/main.js           ✅
│   └── templates/
│       ├── base.html            ✅ Layout master + sidebar
│       ├── dashboard/index.html ✅
│       ├── modulo1/index.html   ✅ (placeholder)
│       ├── modulo2/index.html   ✅ (placeholder)
│       └── trend/index.html     ✅ (placeholder)
├── config/__init__.py           ✅
├── data_raw/                    ✅ (2 Excel copiati)
├── docs/                        ✅ Documentazione
├── src/                         ✅ (37 file Python, invariati)
├── tests/                       ✅ (vuoto, da popolare)
├── venv/                        ✅ Flask installato
├── .env.example                 ✅
├── .gitignore                   ✅
├── requirements.txt             ✅
└── run.py                       ✅
```

---

## Decisioni tecniche prese

| Decisione | Scelta | Motivo |
|-----------|--------|--------|
| Tailwind | CDN per sviluppo | Evita step Node.js iniziale, si migra a build dopo |
| Grafici | Plotly.js (non Chart.js) | Riuso logica Python già in Plotly |
| Caching | In-memory dict Python | Sufficiente per 1-5 utenti, semplice |
| `src/` | Copiato invariato | Zero riscrittura logica di business |

---

## Come avviare

```bash
cd "C:\Users\emanu\Desktop\MCM ENGINE\MCM_ENGINE_FLASK"
venv\Scripts\python run.py
# → http://localhost:5000
```

---

## Prossimo step: FASE 2 — Modulo 1 Comportamento

Implementare i KPI di Comportamento HCP con API endpoints e grafici Plotly interattivi.
