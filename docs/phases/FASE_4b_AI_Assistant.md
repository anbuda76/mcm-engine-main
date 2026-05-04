# FASE 4b — AI Agent Multi-Agente con ReAct + Tool Calling

**Data**: 6 marzo 2026
**Stato**: ✅ Completata — aggiornata da [FASE 4c](FASE_4c_AI_Agent_Upgrade.md)

> **Nota**: questa fase descrive l'implementazione base (4 tool per agente, loop bloccante, MAX_STEPS=6).
> I miglioramenti successivi (streaming live, +5 tool, prompt dataset-aware, MAX_STEPS=4) sono documentati in **FASE_4c_AI_Agent_Upgrade.md**.

---

## Obiettivo

Implementare un sistema di AI Agent specializzati con:
- **LLM locale via Ollama** (Qwen3:8b) — privacy-first, zero costi, zero API key
- **Pattern ReAct** (Reasoning + Acting): loop Think → Tool Call → Observation → Answer
- **Due agenti specializzati** con tool calling su dati reali MCM:
  - **HCP Behavior Agent** — analisi comportamento medici (penetrazione, ricordo, funnel, OCV)
  - **Market Performance Agent** — benchmark aziende, NPS, trend canali
- **Controllo business**: admin può abilitare/disabilitare agenti per utente
- **SSE Streaming** di eventi tipizzati con UI step-by-step

> **Nota**: questa fase include anche un chat conversazionale semplice con deepseek-r1
> (endpoint `/api/chat` legacy) e il context loader (`/api/context/<module>`).
> Il sistema agentico principale usa `/api/agent` con Qwen3:8b.

---

## Prerequisiti Utente (una-tantum)

```bash
# 1. Scarica e installa Ollama: https://ollama.ai
# 2. Scarica il modello (Qwen3 supporta tool calling + thinking nativo):
ollama pull qwen3:4b       # ~2.6GB — default attuale (~3GB RAM)
ollama pull qwen3:8b       # ~5.5GB — qualità superiore (richiede ~5.5GB RAM libera)
ollama pull qwen3:1.7b     # ~1.5GB — fallback per PC con poca RAM
# 3. Ollama parte automaticamente su http://localhost:11434
```

> **Nota RAM**: `DEFAULT_MODEL = "qwen3:4b"` in `agent_registry.py`.
> Cambiarlo in `qwen3:8b` se la macchina ha ≥8GB RAM disponibile per Ollama.

---

## File creati / modificati

### Nuovi file

| File | Descrizione |
|------|-------------|
| `app/ai/__init__.py` | Package init |
| `app/ai/prompts.py` | System prompt COMPORTAMENTO + PERFORMANCE |
| `app/ai/tools_comportamento.py` | 4 tool functions + TOOLS_SCHEMA + TOOL_REGISTRY |
| `app/ai/tools_performance.py` | 4 tool functions + TOOLS_SCHEMA + TOOL_REGISTRY |
| `app/ai/agent_registry.py` | AGENTS dict centralizzato + API pubblica |

### File modificati

| File | Modifica |
|------|----------|
| `app/models.py` | Aggiunta colonna `agents` (JSON) + `has_agent()` |
| `app/__init__.py` | Aggiunta `_migrate_db()` per ALTER TABLE idempotente |
| `app/routes/admin.py` | Gestione `agents` in `user_new`/`user_edit`, import AGENT_DEFS |
| `app/templates/admin/user_form.html` | Sezione checkbox "Agenti AI abilitati" |
| `app/routes/ai_assistant.py` | Aggiunta route `/api/agents` + `/api/agent` (ReAct loop) |
| `app/templates/ai_assistant/index.html` | Riscrittura completa: selector agenti + chat step-by-step |

---

## Architettura backend

### Registro Agenti (`app/ai/agent_registry.py`)

```python
DEFAULT_MODEL = "qwen3:4b"   # default attuale (qwen3:8b se RAM disponibile ≥8GB)
MAX_STEPS     = 4   # max iterazioni tool-call per sessione (aggiornato in FASE 4c)

AGENTS = {
    "comportamento": {
        "key":         "comportamento",
        "label":       "HCP Behavior Agent",
        "description": "Analisi del comportamento medici e del consumo dei canali multicanale",
        "icon":        "users-round",
        "color":       "accent",
        "model":       "qwen3:8b",
        "think":       True,          # Qwen3 thinking mode
        "system":      PROMPT_COMPORTAMENTO,
        "tools_schema":   TOOLS_COMPORTAMENTO,
        "tool_registry":  REGISTRY_COMPORTAMENTO,
        "starter_questions": [...],
    },
    "performance": { ... },   # struttura identica
}

# API pubblica:
def get_agent(key) -> dict | None
def execute_tool(agent_key, tool_name, args) -> dict    # dispatch sicuro + error handling
def agent_ui_meta(key) -> dict                          # esclude system/tools (non serializzabili)
def agents_for_user(user_agents) -> list[dict]          # filtra per permessi utente
```

### Loop ReAct (`/ai/api/agent`)

```
1. Ricevi: agent_key, message (obiettivo), history
2. Valida: agent esiste? utente ha permesso (has_agent)?
3. Costruisci messages: [system] + history[-8:] + [user_msg]
4. LOOP (max MAX_STEPS):
   a. ollama.chat(model, messages, tools=tools_schema, think=True)
   b. emit SSE "think" (se msg.thinking non vuoto)
   c. if no tool_calls → emit SSE "answer", BREAK
   d. for each tool_call:
        emit SSE "tool_call" (name, args)
        result = execute_tool(agent_key, name, args)
        emit SSE "observation" (tool, result)
        messages.append({"role": "tool", "content": JSON(result)})
5. Se loop esaurito → emit SSE "error"
6. emit "data: [DONE]"
```

### SSE Events tipizzati

| type | Campi aggiuntivi | Rendering UI |
|------|-----------------|--------------|
| `think` | `content` | 🧠 Pannello arancione collapsibile |
| `tool_call` | `name`, `args` | Badge teal inline + args compact |
| `observation` | `tool`, `result` | 📊 Pannello teal collapsibile con JSON |
| `answer` | `content` | Bubble bot principale (bianco) |
| `error` | `content` | Bubble warning + notice banner giallo |

### Tools disponibili

#### HCP Behavior Agent

| Tool | Parametri | Funzioni src/ |
|------|-----------|--------------|
| `get_comportamento_kpi` | `target?`, `top_n?` | `kpi_penetrazione` + `kpi_ricordo_canali` + `kpi_ingaggio_canali` |
| `get_funnel_hcp` | `target?` | penetrazione→ricordo→ingaggio + conversion rates |
| `get_ocv_mix` | `target?`, `max_combo?` | `ocv_mix_engine` → top 10 mix + best_mix |
| `list_specializzazioni` | — | `get_specializzazioni()` + HCP count per spec |

#### Market Performance Agent

| Tool | Parametri | Funzioni src/ |
|------|-----------|--------------|
| `list_aziende` | `target?` | value_counts su col_azienda |
| `get_performance_azienda` | `azienda`, `target?` | `kpi_nps_azienda` + `kpi_propensione_azienda` + `kpi_penetrazione_azienda` |
| `get_benchmark_canali` | `azienda`, `target?`, `top_n?` | penetrazione e ricordo vs mercato → gap per canale |
| `get_trend_azienda` | `azienda`, `target?` | `trend_engine` + YoY NPS variation |

**Nota firma critica**: `kpi_penetrazione_azienda(df_azienda, canali_perf)` — df già filtrato per azienda (legge `df["Azienda"].iloc[0]` internamente). NON passare col_az o azienda separatamente.

### Route API agentiche

| Route | Auth | Descrizione |
|-------|------|-------------|
| `GET  /ai/api/agents` | ✅ login_required | Lista agenti abilitati per current_user |
| `POST /ai/api/agent` | ✅ login_required | Loop ReAct SSE streaming |

---

## Architettura permessi agenti

### User model (`app/models.py`)

```python
_agents = db.Column("agents", db.Text, default="[]", nullable=False)

@property
def agents(self) -> list:    # parse JSON
@agents.setter               # dump JSON

def has_agent(self, agent_key: str) -> bool:
    if self.is_admin: return True
    return not self.agents or agent_key in self.agents
    # [] = tutti gli agenti (semantica coerente con targets/aziende)
```

### Migrazione DB (`app/__init__.py`)

```python
def _migrate_db(db):
    migrations = [
        "ALTER TABLE users ADD COLUMN agents TEXT NOT NULL DEFAULT '[]'",
    ]
    # eseguita ad ogni avvio, silenziosamente ignora se colonna esiste già
```

### Admin form (`user_form.html`)

Sezione "Agenti AI abilitati" con checkbox per ogni agente in `ALL_AGENTS`.
Checkbox non selezionato = agente disabilitato per l'utente.
Nessuna checkbox selezionata (default) = tutti gli agenti abilitati.

---

## Architettura frontend (`ai_assistant/index.html`)

### Stato 1 — Agent Selector

```
GET /ai/api/agents → renderAgentCards(agents)

┌──────────────────────────────────────────────┐
│ 🤖 Scegli un Agente AI                       │
│                                              │
│ ┌─────────────────┐  ┌─────────────────┐    │
│ │ 👤 HCP Behavior │  │ 📊 Market Perf  │    │
│ │ Agent           │  │ Agent           │    │
│ │ [starter q1]    │  │ [starter q1]    │    │
│ │ [starter q2]    │  │ [starter q2]    │    │
│ │ [Avvia chat →]  │  │ [Avvia chat →]  │    │
│ └─────────────────┘  └─────────────────┘    │
└──────────────────────────────────────────────┘
```

### Stato 2 — Chat Agent

```
┌──────────────────────────────────────────────┐
│ ← | 👤 HCP Behavior Agent                    │
│     Analisi comportamento medici...          │
│──────────────────────────────────────────────│
│  [Utente] Quale canale raggiunge più medici? │
│                                              │
│  [🧠 Ragionamento AI ▶]  ← collapsibile      │
│    Devo usare get_comportamento_kpi...       │
│                                              │
│  [⚙ get_comportamento_kpi {target: null}]   │
│                                              │
│  [📊 Dati ricevuti: get_comportamento_kpi ▶] │
│    { penetrazione: [...], ... }              │
│                                              │
│  [Bot] ISF Face-to-Face raggiunge il 78%... │
│──────────────────────────────────────────────│
│ [textarea input...]              [Invia →]   │
└──────────────────────────────────────────────┘
```

### Funzioni JS principali

| Funzione | Descrizione |
|----------|-------------|
| `loadAgents()` | GET /ai/api/agents → renderAgentCards |
| `renderAgentCards(agents)` | Costruisce HTML card per ogni agente |
| `selectAgent(key)` | Transizione a Stato 2, mostra chat |
| `startChatWith(e, key, btn)` | Starter question → pre-fill input → invia |
| `sendMessage()` | POST /ai/api/agent → gestisce SSE stream |
| `addAgentResponseContainer()` | Crea container risposta con typing indicator |
| `addThinkStep(body, content)` | Pannello arancione collapsibile |
| `addToolCallStep(body, name, args)` | Badge inline tool call |
| `addObservationStep(body, tool, result)` | Pannello teal collapsibile + JSON |
| `addAnswerBubble(body, content)` | Bubble risposta finale |
| `addErrorBubble(body, content)` | Warning bubble + notice |
| `goBackToSelector()` | Torna allo Stato 1, reset chat |

---

## Note implementative

- **Nessun duplicazione logica**: i tools chiamano direttamente le funzioni in `src/`
- **args come stringa JSON**: alcuni LLM restituiscono `function.arguments` come stringa — gestito con `json.loads()` con fallback `{}`
- **History multi-turno**: inviata al loop per conversazione coerente; max 4 turni (ridotto da 8 in FASE 4c per ridurre input tokens)
- **SSE flush**: `X-Accel-Buffering: no` per disabilitare buffering nginx/proxy

---

## Verifica end-to-end

```bash
# 1. Avviare Ollama (se non già servizio):
ollama serve

# 2. Verificare che Qwen3 sia installato:
ollama list   # deve mostrare qwen3:8b

# 3. Avviare Flask:
venv\Scripts\python run.py

# 4. Aprire http://localhost:5000/ai/
# 5. Dovrebbero comparire le card degli agenti (caricamento da /ai/api/agents)
# 6. Cliccare "HCP Behavior Agent" → chat si apre
# 7. Digitare "Quale canale raggiunge più medici?" → Invia
# 8. Verificare sequenza: think → tool_call → observation → answer
# 9. Verificare pannello "🧠 Ragionamento AI" espandibile
# 10. Admin: /admin/ → modifica utente → sezione "Agenti AI abilitati"
```
