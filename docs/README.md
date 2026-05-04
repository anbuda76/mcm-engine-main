# MCM Engine — Documentazione Migrazione

## Panoramica
Migrazione dell'applicazione MCM Engine da **Streamlit** a **Flask + Tailwind CSS**.

- **Progetto originale**: `C:\Users\emanu\Desktop\MCM ENGINE\` (Streamlit — NON modificare)
- **Nuovo progetto**: `C:\Users\emanu\Desktop\MCM ENGINE\MCM_ENGINE_FLASK\`
- **Avvio Flask**: `venv\Scripts\python run.py` → `http://localhost:5001`

## Fasi di lavoro
| Fase | Descrizione | Stato | Doc |
|------|-------------|-------|-----|
| 0 | Setup struttura + copia src/ | ✅ Completata | FASE_0_1_Setup_e_Scheletro.md |
| 1 | Scheletro Flask + layout dark + Tailwind + Lucide | ✅ Completata | FASE_1b_Dark_Theme_Lucide.md |
| 2 | Modulo 1: Comportamento HCP (base) | ✅ Completata | FASE_2_Modulo1_Comportamento.md |
| 2b | Fix label canali uniformi + download Excel | ✅ Completata | FASE_2b_Fix_Labels_Download.md |
| 2c | UX Modulo 1: Avvia Analisi, OCV, tooltips, campione insufficiente | ✅ Completata | FASE_2c_UX_Modulo1.md |
| 2d | Funnel HCP Modulo 1: Funnel Matrix + Sankey + Best Path | ✅ Completata | FASE_2d_Funnel_HCP.md |
| 3 | Modulo 2: Performance vs Mercato (UX allineata + MIN_HCP) | ✅ Completata | FASE_3_Modulo2_Performance.md |
| 3b | Modulo 3: Trend Temporali — UX allineata | ✅ Completata | FASE_3b_Trend_UX.md |
| 4b | AI Agent base: ReAct + Tool Calling + SSE (4 tool per agente) | ✅ Completata | FASE_4b_AI_Assistant.md |
| 4c | AI Agent upgrade: +5 tool, prompt dataset-aware, streaming live | ✅ Completata | FASE_4c_AI_Agent_Upgrade.md |
| 5 | Auth, Upload Excel, Cache TTL | ✅ Completata | FASE_5_Auth_Upload_Cache.md |
| 6 | PDF Report Modulo 1 (4 pagine, dark, logo, anti-overflow) | ✅ Completata | FASE_6_PDF_Report.md |
| 7 | Test, go-live | ⏳ In attesa | — |

## Cartelle documentazione
- `docs/phases/` — log dettagliato di ogni fase completata
- `docs/README.md` — questo file (indice generale)

## Riferimenti rapidi
- **MIN_HCP** (soglia campione): `app/routes/modulo1.py` → `MIN_HCP = 20`
- **Canali standard**: `src/behavior/mappe/mappa_canali_labels.py` → `CANALI_MAP`
- **OCV engine**: `src/behavior/kpi_ocv_mix.py` → `ocv_delta()`, `ocv_mix_engine()`
- **Normalizzazione label**: `app/routes/modulo1.py` → `_normalizza_df()`, `_normalizza_mix_str()`
- **Funnel HCP**: `app/templates/modulo1/index.html` → `buildFunnelData()`, `renderFunnelMatrix()`, `renderSankey()`, `renderBestPath()`
- **AI Agents**: `app/ai/agent_registry.py` → `AGENTS`, `MAX_STEPS=4`, `execute_tool()`
- **PDF Report**: `app/reports/report_comportamento.py` → `genera_report(targets) → BytesIO`
- **num_predict Ollama**: minimo `2048` con `think=True` — sotto questa soglia il modello si tronca
