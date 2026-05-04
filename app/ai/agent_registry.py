"""
app/ai/agent_registry.py
─────────────────────────
Registro centrale degli agenti AI specializzati MCM Engine.

Definisce:
  - AGENTS        → dizionario di tutti gli agenti disponibili
  - MAX_STEPS     → numero massimo di tool call per sessione
  - get_agent()   → accesso per chiave
  - execute_tool()→ dispatch sicuro tool_name → funzione Python
  - agent_ui_meta()→ metadati UI (senza tools_schema/registry/system)
"""

from app.ai.prompts import PROMPT_COMPORTAMENTO, PROMPT_PERFORMANCE

from app.ai.tools_comportamento import (
    TOOLS_SCHEMA  as TOOLS_COMPORTAMENTO,
    TOOL_REGISTRY as REGISTRY_COMPORTAMENTO,
)
from app.ai.tools_performance import (
    TOOLS_SCHEMA  as TOOLS_PERFORMANCE,
    TOOL_REGISTRY as REGISTRY_PERFORMANCE,
)

# ── Configurazione globale ────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen3:4b"   # modello Ollama di default
MAX_STEPS     = 4            # max iterazioni tool-call per singola sessione (3 bastano nel 95% dei casi)


# ── Registro agenti ──────────────────────────────────────────────────────────

AGENTS: dict[str, dict] = {

    "comportamento": {
        # Metadati UI
        "key":         "comportamento",
        "label":       "HCP Behavior Agent",
        "description": "Analisi del comportamento medici e del consumo dei canali multicanale",
        "icon":        "users-round",
        "color":       "accent",           # teal — coerente col colore Modulo 1

        # Modello e reasoning
        "model":       DEFAULT_MODEL,
        "think":       True,               # attiva Qwen3 thinking mode

        # Dominio operativo (solo info)
        "dominio":     "Comportamento HCP: penetrazione, ricordo, ingaggio, funnel, OCV",
        "dati":        ["df_beh", "df_perf"],

        # Prompt + tools (usati dal loop agente)
        "system":         PROMPT_COMPORTAMENTO,
        "tools_schema":   TOOLS_COMPORTAMENTO,
        "tool_registry":  REGISTRY_COMPORTAMENTO,

        # Domande suggerite mostrate nella UI
        "starter_questions": [
            "Quale canale raggiunge più medici?",
            "Quali canali hanno alta utilità ma bassa penetrazione?",
            "Qual è il mix di canali ottimale per i Cardiologi?",
            "Dove perdo i medici nel funnel di comunicazione?",
            "Cosa succederebbe se aumentassimo del 15% la penetrazione ISF?",
        ],
    },

    "performance": {
        # Metadati UI
        "key":         "performance",
        "label":       "Market Performance Agent",
        "description": "Benchmark aziende, trend temporali e analisi competitiva",
        "icon":        "bar-chart-3",
        "color":       "secondary",        # viola — coerente col colore Modulo 2

        # Modello e reasoning
        "model":       DEFAULT_MODEL,
        "think":       True,

        # Dominio operativo
        "dominio":     "Performance aziende: NPS, propensione, benchmark canali, trend",
        "dati":        ["df_perf"],

        # Prompt + tools
        "system":         PROMPT_PERFORMANCE,
        "tools_schema":   TOOLS_PERFORMANCE,
        "tool_registry":  REGISTRY_PERFORMANCE,

        # Domande suggerite
        "starter_questions": [
            "Quali aziende sono disponibili nel dataset?",
            "Come performa Pfizer rispetto al mercato?",
            "Su quali canali siamo sotto benchmark?",
            "Come vengono percepiti gli attributi relazionali di questa azienda?",
            "Se colmassimo il gap sui canali sotto benchmark, quanti medici raggiungeremmo in più?",
        ],
    },
}

ALL_AGENT_KEYS: list[str] = list(AGENTS.keys())

# Campi da escludere nell'output UI (contengono oggetti non serializzabili)
_UI_EXCLUDE = {"tools_schema", "tool_registry", "system"}


# ── API pubblica ─────────────────────────────────────────────────────────────

def get_agent(key: str) -> dict | None:
    """Restituisce la definizione completa dell'agente, o None se non esiste."""
    return AGENTS.get(key)


def execute_tool(agent_key: str, tool_name: str, args: dict) -> dict:
    """
    Esegue un tool dell'agente specificato con i parametri forniti.

    Restituisce sempre un dict JSON-serializzabile.
    In caso di errore: {"errore": "messaggio descrittivo"}
    """
    agent = AGENTS.get(agent_key)
    if not agent:
        return {"errore": f"Agente '{agent_key}' non registrato. "
                          f"Agenti disponibili: {ALL_AGENT_KEYS}"}

    registry = agent["tool_registry"]
    if tool_name not in registry:
        tools_disp = list(registry.keys())
        return {"errore": f"Tool '{tool_name}' non disponibile per '{agent_key}'. "
                          f"Tool disponibili: {tools_disp}"}

    try:
        return registry[tool_name](**args)
    except TypeError as e:
        return {"errore": f"Parametri errati per '{tool_name}': {e}. "
                          "Controlla i tipi e i nomi dei parametri."}
    except Exception as e:
        return {"errore": f"Errore durante l'esecuzione di '{tool_name}': {e}"}


def agent_ui_meta(key: str) -> dict:
    """
    Restituisce solo i metadati UI dell'agente (senza system prompt, tools_schema, registry).
    Usato dalle route Flask per rispondere al frontend.
    """
    agent = AGENTS.get(key)
    if not agent:
        return {}
    return {k: v for k, v in agent.items() if k not in _UI_EXCLUDE}


def agents_for_user(user_agents: list[str]) -> list[dict]:
    """
    Restituisce la lista di metadati UI degli agenti abilitati per un utente.

    user_agents: valore di User.agents (lista chiavi). Lista vuota = tutti.
    """
    if not user_agents:
        # Lista vuota = accesso a tutti gli agenti (semantica coerente con modules/targets)
        keys = ALL_AGENT_KEYS
    else:
        keys = [k for k in ALL_AGENT_KEYS if k in user_agents]

    return [agent_ui_meta(k) for k in keys]
