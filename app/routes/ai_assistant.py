"""
app/routes/ai_assistant.py
──────────────────────────
Blueprint AI Assistant — Chat conversazionale con dati HCP via Ollama (locale)

Route HTML:
  GET  /ai/                   → pagina chat

Route API JSON:
  POST /ai/api/chat           → SSE streaming con modello reasoning (deepseek-r1)
  GET  /ai/api/context/<mod>  → carica KPI riassuntivi dal modulo selezionato
  GET  /ai/api/models         → lista modelli Ollama disponibili

Modelli supportati (Ollama locale):
  deepseek-r1:7b   — reasoning, 4.7GB RAM  (default)
  deepseek-r1:14b  — reasoning, 9GB RAM
  llama3.2         — general chat, 2GB RAM
"""

import sys, os, io, json
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.data_cache import get_data, get_specializzazioni
from app.ai.agent_registry import (
    get_agent, execute_tool, agents_for_user,
    MAX_STEPS, DEFAULT_MODEL as AGENT_DEFAULT_MODEL,
)
from src.behavior.mappe.mappa_canali_labels import CANALI_MAP
from src.behavior.kpi_penetrazione import kpi_penetrazione
from src.behavior.kpi_ricordo      import kpi_ricordo_canali
from src.behavior.kpi_ingaggio     import kpi_ingaggio_canali
from src.behavior.kpi_nps_canali   import kpi_nps_canali

ai_bp = Blueprint("ai", __name__)

# Modello di default chat legacy (deepseek-r1)
DEFAULT_MODEL = "deepseek-r1:7b"


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _filtra(df, col, vals):
    if not vals or not col or col not in df.columns:
        return df
    return df[df[col].isin(vals)].copy()


def _safe_json(df):
    import json
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _norm_canale(df):
    if df is None or df.empty or "Canale" not in df.columns:
        return df
    df = df.copy()
    df["Canale"] = df["Canale"].map(CANALI_MAP).fillna(df["Canale"])
    return df


def _build_system_prompt(ctx: dict) -> str:
    """
    Costruisce il system prompt per il modello AI.
    Se ctx è fornito, include i dati KPI del modulo selezionato.
    """
    base = """Sei MCM Assistant, un esperto analista di multichannel marketing (MCM) per l'industria farmaceutica.
Hai accesso ai dati HCP (Healthcare Professionals) della piattaforma MCM Engine — BHAVE Platform.

Il tuo compito è analizzare i dati di comportamento, performance e trend dei medici/HCP
in risposta alle attività di marketing dei canali pharma (ISF, Email, Webinar, Congressi, ecc.).

REGOLE FONDAMENTALI:
- Rispondi SEMPRE in italiano, in modo professionale ma chiaro
- Sii preciso: cita i valori numerici specifici presenti nel contesto
- Massimo 5-6 frasi per risposta, salvo richiesta di analisi approfondita
- Se i dati non sono disponibili nel contesto, dillo chiaramente
- Usa terminologia pharma/HCP appropriata (penetrazione, ricordo, ingaggio, NPS, OCV)

GLOSSARIO KPI:
- Penetrazione (%): % HCP raggiunti dal canale rispetto al totale HCP nel segmento
- Ricordo (%): % HCP esposti che ricordano il messaggio del canale
- Ingaggio (%): % HCP attivamente coinvolti/engaged dal canale
- Propensione (0-10): media della propensione al consiglio del farmaco
- NPS (%): Net Promoter Score = % Promotori - % Detrattori (scala -100 a +100)
- OCV (%): Omnichannel Value — incremento del ricordo grazie alla combinazione di canali"""

    if ctx:
        base += f"\n\nDATI ANALISI CORRENTE:\n{json.dumps(ctx, ensure_ascii=False, indent=2)}"

    return base


# ──────────────────────────────────────────────────────────────
# ROUTE HTML
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/")
def index():
    return render_template(
        "ai_assistant/index.html",
        active_page="ai",
    )


# ──────────────────────────────────────────────────────────────
# API: Chat SSE streaming con reasoning model
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/api/chat", methods=["POST"])
def chat():
    """
    SSE endpoint per chat con modello reasoning.

    Body JSON:
      { "message": "...", "context": {...}, "model": "deepseek-r1:7b", "history": [...] }

    Risposta SSE (text/event-stream):
      data: {"text": "chunk..."}
      data: [DONE]
      data: {"error": "..."}  (in caso di errore)
    """
    req     = request.get_json(silent=True) or {}
    msg     = req.get("message", "").strip()
    ctx     = req.get("context", {})
    model   = req.get("model", DEFAULT_MODEL)
    history = req.get("history", [])  # conversazione precedente

    if not msg:
        return jsonify({"error": "Messaggio vuoto"}), 400

    system_prompt = _build_system_prompt(ctx)

    # Costruisci messaggi per Ollama: system + history + nuovo messaggio
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-8:]:  # max 8 turni di storia
        role    = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": msg})

    def generate():
        try:
            import ollama
            stream = ollama.chat(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                text = chunk["message"]["content"]
                if text:
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

        except Exception as e:
            err_msg = str(e)
            err_low = err_msg.lower()
            # Messaggio user-friendly per i casi comuni
            if "not found" in err_low or "404" in err_msg or "pull" in err_low:
                err_msg = (
                    f"Modello '{model}' non installato. "
                    f"Esegui nel terminale: ollama pull {model}"
                )
            elif "connection refused" in err_low or "connect" in err_low or "errno 10061" in err_low:
                err_msg = (
                    "Ollama non è raggiungibile. "
                    "Assicurati che Ollama sia installato e avviato (ollama serve). "
                    f"Modello richiesto: {model}"
                )
            yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────────────────────
# API: Context — carica KPI riassuntivi dal modulo selezionato
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/api/context/<module>")
def get_context(module):
    """
    Calcola un riassunto KPI compatto dal modulo selezionato.
    Usato dal frontend per passare contesto automatico all'AI.

    Parametri query:
      target=Cardiologia&target=Oncologia  → filtro specializzazione (opzionale)
      azienda=Pfizer                       → filtro azienda (per modulo2 e trend)

    Risposta JSON:
      { "module": "modulo1", "n_hcp": 87, "top_canali": [...], "medie": {...}, "label": "..." }
    """
    targets = request.args.getlist("target")
    azienda = request.args.get("azienda", "")

    data    = get_data()
    cols    = data["columns"]
    col_tgt = cols.get("col_target")
    df_beh  = _filtra(data["df_beh"],  col_tgt, targets)
    df_perf = _filtra(data["df_perf"], col_tgt, targets)

    try:
        # ── MODULO 1 — Comportamento HCP ──────────────────────
        if module == "modulo1":
            n_hcp = int(len(df_beh))
            if n_hcp < 5:
                return jsonify({"error": "Campione troppo piccolo", "n_hcp": n_hcp})

            df_pen  = _norm_canale(kpi_penetrazione(df_beh, cols["canali_11"]))
            df_ric  = _norm_canale(kpi_ricordo_canali(df_perf, cols["canali_perf"]))
            df_ing  = _norm_canale(kpi_ingaggio_canali(df_perf, cols["canali_perf"]))

            # Top 8 canali per penetrazione
            top_pen = (
                df_pen.sort_values("Penetrazione (%)", ascending=False)
                      .head(8)[["Canale", "Penetrazione (%)"]]
                      .to_dict("records")
                if not df_pen.empty else []
            )

            # Top 5 canali per ricordo
            top_ric = (
                df_ric.sort_values("Ricordo (%)", ascending=False)
                      .head(5)[["Canale", "Ricordo (%)"]]
                      .to_dict("records")
                if not df_ric.empty else []
            )

            pen_media = round(float(df_pen["Penetrazione (%)"].mean()), 1) if not df_pen.empty else 0
            ric_media = round(float(df_ric["Ricordo (%)"].mean()),      1) if not df_ric.empty else 0
            ing_media = round(float(df_ing.attrs.get("media_ingaggio", 0)), 1)

            filtri_label = ", ".join(targets) if targets else "tutti i segmenti"

            return jsonify({
                "module":     "Comportamento HCP",
                "filtri":     filtri_label,
                "n_hcp":      n_hcp,
                "medie":      {"penetrazione": pen_media, "ricordo": ric_media, "ingaggio": ing_media},
                "top_canali_penetrazione": top_pen,
                "top_canali_ricordo":      top_ric,
                "label": f"Comportamento HCP — {filtri_label} ({n_hcp} HCP)",
            })

        # ── MODULO 2 — Performance vs Mercato ─────────────────
        elif module == "modulo2":
            col_az = cols.get("col_azienda")
            aziende = data["df_perf"][col_az].dropna().unique().tolist() if col_az else []

            # Filtra per azienda se specificata
            df_az = df_perf
            if azienda and col_az and col_az in df_perf.columns:
                df_az = df_perf[df_perf[col_az] == azienda]

            n_hcp_az  = int(len(df_az))
            n_hcp_tot = int(len(df_perf))

            from src.performance.kpi_penetrazione_azienda import kpi_penetrazione_azienda
            from src.performance.kpi_ricordo_azienda      import kpi_ricordo_azienda

            df_pen_az = _norm_canale(kpi_penetrazione_azienda(df_az, cols["canali_perf"], col_az, azienda))
            df_ric_az = _norm_canale(kpi_ricordo_azienda(df_az,      cols["canali_perf"], col_az, azienda))

            top_pen = (
                df_pen_az.sort_values("Penetrazione (%)", ascending=False)
                         .head(5)[["Canale", "Penetrazione (%)"]]
                         .to_dict("records")
                if not df_pen_az.empty else []
            )

            filtri_label = f"{azienda or 'tutte aziende'}"
            if targets:
                filtri_label += f" — {', '.join(targets)}"

            return jsonify({
                "module":     "Performance vs Mercato",
                "azienda":    azienda or "(tutte)",
                "filtri":     filtri_label,
                "n_hcp":      n_hcp_az,
                "n_hcp_mercato": n_hcp_tot,
                "aziende_disponibili": aziende[:10],
                "top_canali_penetrazione": top_pen,
                "label": f"Performance — {filtri_label} ({n_hcp_az} HCP)",
            })

        # ── MODULO 3 — Trend Temporali ─────────────────────────
        elif module == "trend":
            col_az   = cols.get("col_azienda")
            col_anno = "Anno"

            anni = []
            if col_anno in df_perf.columns:
                anni = sorted(df_perf[col_anno].dropna().astype(str).unique().tolist())

            df_az = df_perf
            if azienda and col_az and col_az in df_perf.columns:
                df_az = df_perf[df_perf[col_az] == azienda]

            # KPI per ogni anno disponibile (riassunto compatto)
            trend_summary = {}
            for anno in anni:
                df_anno = df_az[df_az[col_anno].astype(str) == anno] if col_anno in df_az.columns else df_az
                n = int(len(df_anno))
                if n < 5:
                    trend_summary[anno] = {"valido": False, "n_hcp": n}
                    continue

                df_pen = _norm_canale(kpi_penetrazione(df_anno, cols["canali_11"]))
                pen_m  = round(float(df_pen["Penetrazione (%)"].mean()), 1) if not df_pen.empty else 0

                df_ric = _norm_canale(kpi_ricordo_canali(df_anno, cols["canali_perf"]))
                ric_m  = round(float(df_ric["Ricordo (%)"].mean()), 1) if not df_ric.empty else 0

                trend_summary[anno] = {
                    "valido":       True,
                    "n_hcp":        n,
                    "pen_media":    pen_m,
                    "ric_media":    ric_m,
                }

            filtri_label = f"{azienda or 'dataset'}"
            if targets:
                filtri_label += f" — {', '.join(targets)}"

            return jsonify({
                "module":    "Trend Temporali",
                "azienda":   azienda or "(tutte)",
                "anni":      anni,
                "filtri":    filtri_label,
                "trend_per_anno": trend_summary,
                "label": f"Trend — {filtri_label} (anni: {', '.join(anni)})",
            })

        else:
            return jsonify({"error": f"Modulo '{module}' non riconosciuto"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────
# API: Lista modelli Ollama disponibili
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/api/models")
def list_models():
    """
    Ritorna lista dei modelli Ollama installati sulla macchina.
    Se Ollama non è raggiungibile, ritorna lista di default.
    """
    try:
        import ollama
        models_resp = ollama.list()
        models = [m["model"] for m in models_resp.get("models", [])]
        return jsonify({"models": models, "ollama_online": True})
    except Exception:
        return jsonify({
            "models":        [DEFAULT_MODEL, "deepseek-r1:14b", "llama3.2"],
            "ollama_online": False,
            "message":       "Ollama non raggiungibile — avvia con: ollama serve",
        })


# ══════════════════════════════════════════════════════════════
# SISTEMA AGENTICO — Agenti specializzati con tool calling
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# API: Lista agenti abilitati per l'utente corrente
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/api/agents")
@login_required
def list_agents():
    """
    Restituisce gli agenti AI abilitati per current_user.
    Usato dal frontend per costruire il selettore agenti.
    """
    user_agent_keys = current_user.agents if not current_user.is_admin else []
    available = agents_for_user(user_agent_keys)
    return jsonify({"agents": available})


# ──────────────────────────────────────────────────────────────
# API: Loop agente ReAct con tool calling — SSE streaming
# ──────────────────────────────────────────────────────────────
@ai_bp.route("/api/agent", methods=["POST"])
@login_required
def run_agent():
    """
    Esegue il loop ReAct di un agente specializzato con tool calling via Ollama.

    Body JSON:
      {
        "agent":   "comportamento" | "performance",
        "message": "obiettivo / domanda dell'utente",
        "history": [{"role": "user"|"assistant", "content": "..."}]  // opzionale
      }

    SSE stream — eventi tipizzati:
      data: {"type": "think",       "content": "ragionamento interno..."}
      data: {"type": "tool_call",   "name": "get_comportamento_kpi", "args": {...}}
      data: {"type": "observation", "tool": "get_comportamento_kpi", "result": {...}}
      data: {"type": "answer",      "content": "risposta finale..."}
      data: {"type": "error",       "content": "messaggio errore"}
      data: [DONE]
    """
    body      = request.get_json(silent=True) or {}
    agent_key = body.get("agent", "").strip()
    objective = body.get("message", "").strip()
    history   = body.get("history", [])

    # Validazione
    if not agent_key:
        return jsonify({"error": "Specifica il campo 'agent'."}), 400
    if not objective:
        return jsonify({"error": "Messaggio vuoto."}), 400

    agent = get_agent(agent_key)
    if not agent:
        return jsonify({"error": f"Agente '{agent_key}' non trovato."}), 400

    if not current_user.has_agent(agent_key):
        return jsonify({"error": "Agente non abilitato per questo account."}), 403

    def _sse(event_type: str, **kwargs) -> str:
        payload = {"type": event_type, **kwargs}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _err_message(exc: Exception, model: str) -> str:
        msg = str(exc).lower()
        if "connection refused" in msg or "connect" in msg or "errno 10061" in msg:
            return (
                f"Ollama non raggiungibile. "
                f"Avvia il servizio con: ollama serve"
            )
        if "not found" in msg or "404" in msg or "pull" in msg:
            return (
                f"Modello '{model}' non installato. "
                f"Esegui nel terminale: ollama pull {model}"
            )
        return str(exc)

    def generate():
        import ollama

        model = agent["model"]

        # Costruisci history — max 4 turni (ridotto per velocità)
        messages = [{"role": "system", "content": agent["system"]}]
        for h in history[-4:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": objective})

        step = 0
        while step < MAX_STEPS:
            step += 1

            # ── Chiamata LLM con STREAMING ────────────────────
            try:
                stream = ollama.chat(
                    model=model,
                    messages=messages,
                    tools=agent["tools_schema"],
                    think=agent.get("think", False),
                    options={"temperature": 0.4, "num_predict": 4096},
                    stream=True,
                )
            except Exception as exc:
                yield _sse("error", content=_err_message(exc, model))
                break

            # Accumula risposta streamata
            full_thinking = []
            full_content  = []
            tool_calls    = []
            has_thinking  = False
            has_content   = False

            try:
                for chunk in stream:
                    msg = chunk.message

                    # ── Stream thinking live ───────────────────
                    t = getattr(msg, "thinking", None) or ""
                    if t:
                        full_thinking.append(t)
                        has_thinking = True
                        yield _sse("think_chunk", content=t)

                    # ── Stream content live (risposta finale) ──
                    c = msg.content or ""
                    if c:
                        full_content.append(c)
                        has_content = True
                        yield _sse("answer_chunk", content=c)

                    # ── Tool calls nell'ultimo chunk ───────────
                    if msg.tool_calls:
                        tool_calls = msg.tool_calls

            except Exception as exc:
                yield _sse("error", content=_err_message(exc, model))
                break

            thinking = "".join(full_thinking)
            content  = "".join(full_content)

            # Chiudi think card
            if has_thinking:
                yield _sse("think_end", total_chars=len(thinking))

            # ── Risposta finale (nessun tool call) ────────────
            if not tool_calls:
                if has_content:
                    # Risposta già streamata token per token
                    yield _sse("answer_done")
                else:
                    yield _sse("answer", content=content or "—")
                break

            # ── Ci sono tool calls: annulla answer_chunk emessi
            if has_content:
                yield _sse("cancel_answer")

            # Serializza il messaggio assistant nella history
            messages.append({
                "role":       "assistant",
                "content":    content,
                "tool_calls": [
                    {
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments or {},
                        }
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = tc.function.arguments or {}
                # Alcuni modelli restituiscono args come stringa JSON
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except json.JSONDecodeError:
                        fn_args = {}

                # Emetti tool_call
                yield _sse("tool_call", name=fn_name, args=fn_args)

                # Esegui tool
                result = execute_tool(agent_key, fn_name, fn_args)

                # Emetti observation
                yield _sse("observation", tool=fn_name, result=result)

                # Aggiungi risultato alla history
                messages.append({
                    "role":    "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                })

        else:
            # Loop esaurito senza risposta finale
            yield _sse(
                "error",
                content=f"Raggiunto il limite di {MAX_STEPS} step senza risposta. "
                        "Prova a riformulare la domanda in modo più specifico."
            )

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
