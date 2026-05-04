# FASE 4c — AI Agent Upgrade: Nuovi Tool, Prompt Dataset-Aware, Streaming Live

**Data**: 17 marzo 2026
**Stato**: ✅ Completata

---

## Obiettivo

Migliorare la qualità e la velocità di risposta degli agenti AI specializzati:

1. **Contestualizzazione dataset**: aggiungere ai system prompt la struttura completa del dataset MCM (variabili Q, 20 canali, formule KPI) per ridurre le iterazioni di reasoning
2. **Nuovi tool**: aggiungere 5 nuovi strumenti analitici (utilità Q6, gap analisi, what-if simulazioni, attributi Q15)
3. **Streaming live**: passare da `ollama.chat()` bloccante a `stream=True` nel loop ReAct per ridurre il TTFB da ~310s a ~0.5s
4. **Parametri Ollama ottimizzati**: temperature, num_predict, MAX_STEPS, history window

---

## Risultati benchmark

| Metrica | Prima | Dopo |
|---------|-------|------|
| TTFB (time to first byte) | ~310 s | 0.52 s |
| Primi token visibili | Dopo risposta completa | Entro ~1-2 s |
| MAX_STEPS | 6 | 4 |
| History window | 8 turni | 4 turni |
| temperature | 0.6 | 0.4 |
| num_predict | nessun cap | 2048 |

---

## File modificati

| File | Modifica |
|------|----------|
| `app/ai/prompts.py` | Riscrittura completa entrambi i prompt |
| `app/ai/tools_comportamento.py` | +3 tool nuovi + schema + registry |
| `app/ai/tools_performance.py` | +2 tool nuovi + schema + registry |
| `app/ai/agent_registry.py` | MAX_STEPS=4, starter_questions aggiornate |
| `app/routes/ai_assistant.py` | Loop ReAct con stream=True, nuovi SSE events |
| `app/templates/ai_assistant/index.html` | JS live streaming (think_chunk, answer_chunk, ...) |

---

## Miglioramenti system prompt (`app/ai/prompts.py`)

Entrambi i prompt ora includono:

### `PROMPT_COMPORTAMENTO`
```
## STRUTTURA DATASET
- Q11a_1..20: penetrazione canali (testo/NaN)
- Q6_1..20: utilità (scala 1-7)
- Q3_1..13: attitudini digitali (scala 1-10)
- Q17_1..8: trust azienda (scala 1-10)

20 canali MCM:
1=Opuscoli posta | 2=ISF f2f | 3=ISF tel | 4=ISF webcall | 5=Email ISF
6=Portali login | 7=Riviste ADV | 8=Riviste articoli | 9=SMS | 10=Email az.
11=Newsletter | 12=Sito prodotto | 13=Riviste digitali | 14=Social | 15=APP tem.
16=APP msg | 17=Webinar | 18=FAD online | 19=Congressi naz ECM | 20=Congressi int ECM

## DECISION TREE (keyword → tool)
"penetrazione","ricordo","ingaggio" → get_comportamento_kpi
"funnel","conversione","dove perdo" → get_funnel_hcp
"OCV","mix ottimale","multicanale"  → get_ocv_mix
"utilità","preferiscono","Q6"       → get_utilita_canali
"opportunità","gap","frizione"      → get_gap_analisi
"cosa succederebbe se","simula"     → whatif_penetrazione
"quali target","specializzazioni"   → list_specializzazioni
```

### `PROMPT_PERFORMANCE`
```
## STRUTTURA DATASET
- Q9_1..20: esposizione canali per azienda (numerico/NaN)
- Q10: ricordo comunicazione (1/NaN)
- Q13_1..N: rilevanza contenuti (scala 1-5)
- Q15_1..5: attributi relazionali (scala 1-10)
  Q15_1=Chiarezza | Q15_2=Credibilita | Q15_3=Rilevanza Topic
  Q15_4=Innovazione | Q15_5=Affidabilita

## DECISION TREE
"NPS","propensione","panoramica"      → get_performance_azienda
"benchmark","gap","confronto mercato" → get_benchmark_canali
"trend","evoluzione","storico"        → get_trend_azienda
"attributi","percezione","Q15"        → get_attributi_azienda
"cosa succederebbe se","potenziale"   → whatif_benchmark_gap
```

---

## Nuovi tool

### HCP Behavior Agent — 3 nuovi tool

#### `get_utilita_canali(target?)`
- **Fonte**: Q6_1..20 (scala 1–7)
- **Output**: top canali per utilità media, classificati in alta (≥6) / media (4–6) / bassa (<4)
- **Trigger**: domande su "utilità", "preferiscono", "quality of channel"

```python
def tool_get_utilita_canali(target: list = None) -> dict:
    # kpi_utilita(df_beh, canali_utilita)
    # Returns: top_canali_utilita (sorted desc), media_utilita_overall, scala info
```

#### `get_gap_analisi(target?)`
- **Formula**: Gap = Utilità_media − (Penetrazione% / 10)
- **Classificazione**: Gap > +1.5 = OPPORTUNITA' | Gap < -1.5 = FRIZIONE
- **Output**: tutti_canali (con gap), opportunita_nascoste, frizioni list
- **Trigger**: "opportunità", "gap", "frizione", "potenziale non espresso"

#### `whatif_penetrazione(canale, delta_pp, target?)`
- **Simulazione lineare**: `hcp_aggiuntivi = (delta_pp/100) × n_hcp`
- **Include**: recall_delta (stimato da tasso_ricordo_attuale), feasibility da Q6
- **Avvertenza**: sempre inclusa — "SIMULAZIONE LINEARE, non predittiva"
- **Trigger**: "cosa succederebbe se", "simula", "what if", "e se aumentassimo"

---

### Market Performance Agent — 2 nuovi tool

#### `get_attributi_azienda(azienda, target?)`
- **Fonti**: Q13_* (rilevanza contenuti 1–5) + Q15_1..5 (attributi 1–10)
- **Output**: rilevanza_contenuti (media Q13), attributi_q15 (5 dimensioni), gap_vs_mercato per attributo
- **Identifica**: attributo_top e attributo_bottom per confronto vs benchmark
- **Trigger**: "attributi", "percezione", "credibilità", "chiarezza", "Q15"

#### `whatif_benchmark_gap(azienda, target?, top_n?)`
- **Logica**: per ogni canale dove azienda < benchmark → calcola hcp_potenziali, recall_stima, priorità
- **Priorità**: Alta (gap>10pp) / Media (gap>5pp) / Bassa (gap≤5pp)
- **Output**: opportunita_per_canale, totale_hcp_potenziali, totale_recall_potenziale
- **Trigger**: "colmassimo il gap", "se investissimo", "dove investire", "potenziale"

---

## Streaming ReAct loop (`app/routes/ai_assistant.py`)

### Vecchio flusso (bloccante)
```
ollama.chat() → attende 10-20s → emette tutti gli SSE in un colpo
Utente: vede pallini per 10-20s, poi tutto compare insieme
```

### Nuovo flusso (streaming)
```python
stream = ollama.chat(model, messages, tools=tools_schema,
                     think=True, options={"temperature": 0.4, "num_predict": 2048},
                     stream=True)

for chunk in stream:
    t = chunk.message.thinking  →  yield SSE "think_chunk"   # live ogni token
    c = chunk.message.content   →  yield SSE "answer_chunk"  # live ogni token
    if chunk.message.tool_calls →  tool_calls = ...

# dopo stream chiuso:
yield SSE "think_end"    # chiude/collassa la think card
yield SSE "answer_done"  # finalizza answer bubble
# oppure:
yield SSE "cancel_answer" + processa tool_calls normalmente
```

### CRITICO — num_predict
Con `think=True`, il modello genera **thinking + output** nello stesso budget token.
- `num_predict=600` → truncation durante thinking → output `"—"` (bug noto)
- `num_predict=2048` → sufficiente per thinking (~800) + tool call (~100) + risposta (~400)
- **Non scendere sotto 2048 con think=True**

---

## Nuovi SSE events

| Event | Campi | Rendering UI |
|-------|-------|--------------|
| `think_chunk` | `content` | Appende testo alla think card live (aperta) |
| `think_end` | `total_chars` | Aggiorna contatore chars, collassa automaticamente |
| `answer_chunk` | `content` | Appende testo alla answer bubble live |
| `answer_done` | — | Finalizza answer bubble (testo già completo) |
| `cancel_answer` | — | Rimuove answer bubble parziale (tool calls in arrivo) |

> I vecchi eventi `think` e `answer` (non-streaming) restano come fallback per compatibilità.

---

## JS live streaming (`app/templates/ai_assistant/index.html`)

### Stato globale aggiunto
```javascript
let liveThinkCard = null;   // card think aperta in streaming
let liveThinkBody = null;   // .step-body della think card live
let liveThinkText = '';     // testo thinking accumulato
let liveAnswerEl  = null;   // bubble answer in streaming
let liveAnswerText = '';    // testo risposta accumulato
```

### Funzioni chiave
```javascript
resetLiveState()            // chiamato all'inizio di ogni sendMessage()
initLiveThinkCard(body)     // crea think card vuota (aperta, visibile)
appendThinkChunk(body, t)   // aggiunge chunk di testo alla think card
finalizeThinkCard(n)        // aggiorna char count, collassa automaticamente
initLiveAnswer(body)        // crea answer bubble vuota
appendAnswerChunk(body, c)  // aggiunge chunk di testo all'answer bubble
finalizeAnswer()            // cleanup stato live
cancelAnswer(body)          // rimuove bubble parziale + ripristina typing
```

---

## Bug risolti in questa fase

| Bug | Causa | Fix |
|-----|-------|-----|
| `IndentationError` tools_comportamento.py riga 574 | `]` prematuro in TOOLS_SCHEMA — nuovi tool schema erano fuori dalla lista | Rimosso `]` prematuro |
| Stesso bug in tools_performance.py riga 649 | Idem | Fix identico |
| Output `"—"` con think=True | `num_predict=600` troppo basso, LLM troncato durante thinking | Impostato `num_predict=2048` |
| App non ripartiva dopo fix | `.pyc` stale in `__pycache__` | `shutil.rmtree('__pycache__')` + restart |

---

## Verifica end-to-end

```bash
# 1. Avvia Ollama:
ollama serve

# 2. Avvia Flask:
venv\Scripts\python run.py

# 3. Apri http://localhost:5001/ai/
# 4. Seleziona "HCP Behavior Agent"
# 5. Domanda: "Quale canale raggiunge più medici tra i Cardiologi?"
# Verifica:
#   - Think card appare entro ~1-2s e il testo scorre live
#   - Think card si collassa automaticamente dopo il tool call
#   - Tool call card appare
#   - Dati ricevuti card appare
#   - Risposta finale streamma token per token
#   - Risposta in italiano con valori numerici reali

# 6. Domanda: "Quali canali hanno alta utilità ma bassa penetrazione?"
#   → deve usare get_gap_analisi

# 7. Domanda: "Cosa succederebbe se aumentassimo del 20% la penetrazione dell'ISF?"
#   → deve usare whatif_penetrazione

# 8. Seleziona "Market Performance Agent"
# 9. Domanda: "Come vengono percepiti gli attributi relazionali di Pfizer?"
#   → deve usare get_attributi_azienda
```
