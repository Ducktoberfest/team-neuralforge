"""Run with: python -m streamlit run app.py"""
import json
import os
from pathlib import Path

import streamlit as st

from core import (check_correction, guide, list_saved_sessions, load_notebook,
                  load_session, new_session, predict, record_transfer, reveal, save_notebook, sync_code)
from exercises import EXERCISES
from runner import Runner
from tutor import Gemma, ModelError, context_for, parse_decision

def inject_custom_styles():
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Typography & Base Layout */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.block-container {
    max-width: 1280px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    letter-spacing: -0.035em;
    font-weight: 600;
}

/* Monospace: Code blocks, editor inputs, preformatted text */
code, pre, pre code, .stCode, textarea[aria-label="Python editor"], .stTextArea textarea, .duck-mono {
    font-family: 'JetBrains Mono', 'Fira Code', Menlo, Monaco, Consolas, monospace !important;
}

/* Editor & Textarea styling */
textarea[aria-label="Python editor"], .stTextArea textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13.5px !important;
    border: 1px solid #30363d !important;
    line-height: 1.55 !important;
    tab-size: 4 !important;
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}

textarea[aria-label="Python editor"]:focus, .stTextArea textarea:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 1px #58a6ff !important;
}

/* Code blocks */
div[data-testid="stCodeBlock"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}

/* Sleek Cards & Glassmorphism */
div[data-testid="stChatMessage"] {
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    background-color: #161b22 !important;
}

div[data-testid="stExpander"] {
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    background-color: #161b22 !important;
}

div[data-testid="stMetric"] {
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    background-color: #161b22 !important;
    padding: 12px;
}

.eyebrow {
    color: #8b949e;
    font-size: 11px;
    letter-spacing: 0.14em;
    font-weight: 700;
}

.hero-note {
    color: #8b949e;
    font-size: 16px;
    margin-bottom: 20px;
}

/* Pill Badges & Stage Indicators */
.duck-badge {
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    margin-right: 6px;
    vertical-align: middle;
}

.badge-predict {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.35);
}

.badge-investigate {
    background: rgba(234, 179, 8, 0.15);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.35);
}

.badge-check {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

.badge-reflect {
    background: rgba(139, 92, 246, 0.15);
    color: #a78bfa;
    border: 1px solid rgba(139, 92, 246, 0.35);
}

.badge-offline {
    background: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.25);
}

/* Custom Header Bar */
.duck-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 18px;
    border-radius: 10px;
    background: #161b22;
    border: 1px solid #30363d;
    margin-bottom: 24px;
}

.duck-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
}

.duck-header-right {
    display: flex;
    align-items: center;
    gap: 10px;
}

.duck-logo {
    font-size: 1.25rem;
}

.duck-title {
    font-weight: 700;
    font-size: 1.05rem;
    color: #f0f6fc;
    letter-spacing: -0.02em;
}

.duck-edition {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 9999px;
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
    letter-spacing: 0.02em;
}

.duck-team {
    font-size: 0.8rem;
    color: #8b949e;
}

.duck-version {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem;
    padding: 2px 6px;
    border-radius: 4px;
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
</style>""", unsafe_allow_html=True)


st.set_page_config(page_title="DuckTutor · Think it through", page_icon="🦆", layout="wide")
inject_custom_styles()

DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent / "data")))


def persist(session):
    try:
        save_notebook(session, DATA_DIR)
        st.session_state.pop("save_error", None)
    except OSError:
        st.session_state["save_error"] = "Notebook could not be saved to disk. Export this session before closing."


with st.sidebar:
    st.markdown("## 🦆 DuckTutor")
    st.caption("A small question. A better understanding.")
    if "_pending_exercise" in st.session_state:
        st.session_state["exercise_select"] = st.session_state.pop("_pending_exercise")
    if "_pending_model" in st.session_state:
        st.session_state["gemma_model_select"] = st.session_state.pop("_pending_model")
    chosen = st.selectbox("Exercise", list(EXERCISES), format_func=lambda k: EXERCISES[k].title,
                          key="exercise_select")
    exercise = EXERCISES[chosen]
    if "session" not in st.session_state or st.session_state.session["exercise_id"] != chosen:
        if "session" in st.session_state:
            persist(st.session_state.session)
        st.session_state.session = new_session(exercise)
    if st.button("Start a new session", use_container_width=True):
        persist(st.session_state.session)
        st.session_state.session = new_session(exercise)
        st.rerun()
    with st.expander("Connection settings", expanded=not bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))):
        provider = st.selectbox("Model provider", ["google", "ollama"],
                                format_func=lambda x: "Hosted Gemma" if x == "google" else "Local Ollama")
        if provider == "google":
            MODEL_LABELS = {
                "gemma-4-26b-a4b-it": "gemma-4-26b-a4b-it (Recommended · Fast & Stable)",
                "gemma-4-31b-it": "gemma-4-31b-it (Experimental · Upstream 500 Issues)",
            }
            model_name = st.selectbox(
                "Gemma model",
                ["gemma-4-26b-a4b-it", "gemma-4-31b-it"],
                index=0,
                format_func=lambda m: MODEL_LABELS.get(m, m),
                key="gemma_model_select",
                help="gemma-4-26b-a4b-it is the recommended default model."
            )
            key = st.text_input("Google AI Studio API key", type="password", key="api_key",
                                help="Optional when GEMINI_API_KEY is set. Kept in this browser session, never in the notebook.")
            endpoint = "http://127.0.0.1:11434"
            st.caption("Code and conversation context are sent to Google for inference.")
        else:
            model_name = st.text_input("Installed Ollama model", value="gemma4:12b-it-q4_K_M")
            endpoint = st.text_input("Ollama endpoint", value="http://127.0.0.1:11434")
            key = None
            st.caption("Requires an already downloaded model and running Ollama service.")
        model = Gemma(key=key, model=model_name, provider=provider, base_url=endpoint)
        if st.button("Test Gemma connection", use_container_width=True):
            context = context_for(st.session_state.session, exercise, "connection_check", ["ask_question"], [])
            try:
                with st.spinner("Asking Gemma a short question…"):
                    raw, latency = model.decide(context)
                    response = parse_decision(raw, context)
                st.success(f"Live response · {latency / 1000:.1f}s")
                st.text(response["message"])
            except ModelError as exc:
                err_msg = str(exc)
                if ("31b" in str(model.model).lower() or "31b" in str(model_name).lower()) and ("500" in err_msg or "503" in err_msg):
                    st.warning("Gemma 31B encountered an upstream server error (HTTP 500). Switch to Gemma 26B for stable responses.")
                    if st.button("Switch to Gemma 26B & Retry", key="sidebar_switch_26b"):
                        st.session_state["_pending_model"] = "gemma-4-26b-a4b-it"
                        st.rerun()
                else:
                    st.error(err_msg)
    st.divider()
    mode_label = st.selectbox("Python execution", ["Trusted local demo", "Docker container"])
    trusted = False
    if mode_label == "Trusted local demo":
        trusted = st.checkbox("I am running only code I trust", key="trusted_code")
        st.caption("For your own exercise edits. This is not a sandbox: code can access files on your computer. Keep this app local.")
        mode = "trusted-local"
    else:
        mode = "docker"
        st.caption("Requires Docker running and python:3.12-slim already pulled.")
    runner = Runner(mode=mode, allow_trusted=trusted)
    can_run = mode == "docker" or trusted
    st.divider()
    st.caption("Prototype · Python exercises · one local learner")
    st.caption("Gemma guides. Python checks. You make the edit.")
    saved_sessions = list_saved_sessions(DATA_DIR)
    if saved_sessions:
        with st.expander("Resume saved session"):
            session_opts = {
                s["id"]: f"{EXERCISES[s['exercise_id']].title if s.get('exercise_id') in EXERCISES else s.get('exercise_id')} · {s.get('updated_at', '')[:16]}"
                for s in saved_sessions
            }
            chosen_sid = st.selectbox("Select saved session", list(session_opts.keys()),
                                      format_func=lambda sid: session_opts[sid],
                                      key="resume_session_select")
            if st.button("Load Session", key="load_session_btn", use_container_width=True):
                loaded = load_session(chosen_sid, DATA_DIR)
                if loaded:
                    st.session_state["session"] = loaded
                    st.session_state["_pending_exercise"] = loaded["exercise_id"]
                    st.rerun()

session = st.session_state.session
sid = session["id"]

st.markdown("""<div class="duck-header-bar">
  <div class="duck-header-left">
    <span class="duck-logo">🦆</span>
    <span class="duck-title">DuckTutor</span>
    <span class="duck-edition">Ducktoberfest 2026</span>
  </div>
  <div class="duck-header-right">
    <span class="duck-team">Team NeuralForge</span>
    <span class="duck-version">v0.2.0</span>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">DEBUGGING, WITH UNDERSTANDING</div>', unsafe_allow_html=True)
st.title("Think it through with DuckTutor.")
st.markdown('<div class="hero-note">Predict what happens. Follow the evidence. Make the correction yours.</div>', unsafe_allow_html=True)
if st.session_state.get("save_error"):
    st.error(st.session_state.save_error)

learn, notebook = st.tabs(["Learning session", "My notebook"])

with learn:
    st.subheader(exercise.title)
    st.write(exercise.spec)

    cur_stage = session["stage"]
    p_active = cur_stage == "predict"
    i_active = cur_stage == "guide" and session.get("attempts", 0) == 0
    c_active = cur_stage == "guide" and session.get("attempts", 0) > 0
    r_active = cur_stage == "reflect"
    p_style = "opacity: 1; box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);" if p_active else "opacity: 0.45;"
    i_style = "opacity: 1; box-shadow: 0 0 10px rgba(234, 179, 8, 0.4);" if i_active else "opacity: 0.45;"
    c_style = "opacity: 1; box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);" if c_active else "opacity: 0.45;"
    r_style = "opacity: 1; box-shadow: 0 0 10px rgba(139, 92, 246, 0.4);" if r_active else "opacity: 0.45;"

    st.markdown(f"""<div style="display: flex; align-items: center; gap: 8px; margin: 10px 0 20px 0; flex-wrap: wrap;">
      <span class="duck-badge badge-predict" style="{p_style}">01 Predict</span>
      <span style="color: #484f58;">→</span>
      <span class="duck-badge badge-investigate" style="{i_style}">02 Investigate</span>
      <span style="color: #484f58;">→</span>
      <span class="duck-badge badge-check" style="{c_style}">03 Check</span>
      <span style="color: #484f58;">→</span>
      <span class="duck-badge badge-reflect" style="{r_style}">04 Reflect</span>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        if session["stage"] == "predict":
            st.markdown('#### <span class="duck-badge badge-predict">01 Predict</span> Starter code', unsafe_allow_html=True)
            st.code(exercise.starter, language="python")
            st.caption("Make a prediction first. The editor opens after execution.")
        else:
            st.markdown('#### <span class="duck-badge badge-check">03 Check</span> Python editor & verification', unsafe_allow_html=True)
            code = st.text_area("Python editor", value=session["code"], height=235, max_chars=20000,
                                key=f"editor_{sid}", label_visibility="collapsed")
            if sync_code(session, code):
                persist(session)
            st.caption(f'Current revision: {session["code_hash"]}')
            if st.button("Check my correction", type="primary", disabled=not can_run,
                         use_container_width=True, key="check_correction"):
                with st.spinner("Checking code and investigating the result…"):
                    check_correction(session, exercise, runner, model)
                    persist(session)
                st.rerun()
            if session["verified_hash"] == session["code_hash"]:
                st.success(f"Passed all {len(exercise.cases)} checked cases for this revision.")
                st.caption("This verifies the listed cases, not general correctness.")
            with st.expander("Need to see the solution?"):
                st.caption("Viewing it is recorded in your notebook. It does not mark the code as passed.")
                if st.button("Show explanation and solution", key="reveal_solution"):
                    reveal(session)
                    persist(session)
                    st.rerun()
                if session["solution_viewed"]:
                    st.code(exercise.solution, language="python")
                    st.write(exercise.explanation)

        if session["initial_observation"] is not None:
            st.markdown("#### Prediction meets execution")
            a, b = st.columns(2)
            with a:
                st.caption(f'YOUR PREDICTION · confidence {session["confidence"]}/5')
                st.code(session["prediction"], language="python")
            with b:
                st.caption("OBSERVED OUTPUT · original code")
                st.code(json.dumps(session["initial_observation"], ensure_ascii=False), language="python")
            matched = session["prediction_matches_execution"]
            st.caption("Prediction matched execution." if matched is True else
                       "Prediction differed from execution." if matched is False else
                       "You chose to explore without a prediction.")

        latest = {}
        for result in session["runs"]:
            if result["code_hash"] == session["code_hash"] and result["case_id"] != "prediction":
                latest[result["case_id"]] = result
        if latest:
            st.markdown("#### Execution evidence")
            for result in latest.values():
                status = "PASS" if result["passed"] else "FAIL" if result["status"] == "completed" else result["status"].upper()
                with st.expander(f'{status} · {result["title"]}', expanded=not result["passed"]):
                    st.caption(f'Case: {result["case_id"]} · revision {result["code_hash"]} · {result["duration_ms"]} ms')
                    if result["status"] == "completed":
                        st.write("Observed")
                        st.json(result["actual"])
                        st.write("Expected for this check")
                        st.json(result["expected"])
                    else:
                        st.error(result.get("error", "Execution could not complete."))
                    if result.get("stdout"):
                        st.code(result["stdout"], language="text")
                    if result.get("output_truncated"):
                        st.caption("Printed output was truncated.")

    with right:
        if session["stage"] == "predict":
            st.markdown('#### <span class="duck-badge badge-predict">01 Predict</span> Diagnostic probe', unsafe_allow_html=True)
            st.code(exercise.prediction_code, language="python")
            with st.form(f"prediction_{sid}"):
                choice = st.radio("What will the final print show?", exercise.choices, index=None)
                confidence = st.slider("How confident are you?", 1, 5, 3,
                                       help="1 = unsure, 5 = very confident. This changes the guidance.")
                explanation = st.text_area("What makes you think so?", max_chars=1500,
                                           placeholder="Tell the duck how you reasoned about it.")
                submit = st.form_submit_button("Predict & run", type="primary", disabled=not can_run,
                                               use_container_width=True)
            if submit:
                if choice is None:
                    st.warning("Choose a prediction or 'I'm not sure'.")
                else:
                    with st.spinner("Running Python and asking Gemma…"):
                        predict(session, exercise, runner, model, choice, confidence, explanation)
                        persist(session)
                    st.rerun()
            if session["runs"] and session["runs"][-1]["status"] != "completed":
                st.error(session["runs"][-1].get("error", "Execution is unavailable."))
        else:
            st.markdown('#### <span class="duck-badge badge-investigate">02 Investigate</span> Dialogue with the duck', unsafe_allow_html=True)
            for entry in session["messages"][-10:]:
                with st.chat_message(entry["role"], avatar="🦆" if entry["role"] == "assistant" else None):
                    if entry.get("source", "").startswith("Exercise hint"):
                        st.markdown(f'<span class="duck-badge badge-offline">{entry["source"]}</span>', unsafe_allow_html=True)
                    else:
                        st.caption(entry["source"])
                    st.text(entry["text"])
            recent_errors = [e for e in session["events"] if e["type"] in {"model_unavailable", "model_response_rejected"}]
            if session["messages"] and session["messages"][-1]["source"].startswith("Exercise hint") and recent_errors:
                last_err = recent_errors[-1]["error"]
                is_31b = ("31b" in str(model.model).lower() or "31b" in str(model_name).lower() or "31b" in last_err.lower())
                is_server_err = ("500" in last_err or "503" in last_err or "internal error" in last_err.lower())
                if is_31b and is_server_err:
                    st.warning("Gemma 31B encountered an upstream server error (HTTP 500). Switch to Gemma 26B for stable responses.")
                    if st.button("Switch to Gemma 26B & Retry", key=f"switch_26b_{sid}", type="primary", use_container_width=True):
                        st.session_state["_pending_model"] = "gemma-4-26b-a4b-it"
                        model_26b = Gemma(key=key, model="gemma-4-26b-a4b-it", provider=provider, base_url=endpoint)
                        with st.spinner("Retrying with Gemma 26B…"):
                            guide(session, exercise, runner, model_26b)
                            persist(session)
                        st.rerun()
                else:
                    st.warning(last_err)
            with st.form(f"reply_{sid}", clear_on_submit=True):
                reply = st.text_area("Your reasoning or question", max_chars=1500, height=90)
                send = st.form_submit_button("Discuss with the duck", disabled=not can_run,
                                             use_container_width=True)
            if send and reply.strip():
                with st.spinner("Gemma is considering your code and reasoning…"):
                    guide(session, exercise, runner, model, reply)
                    persist(session)
                st.rerun()
            one, two = st.columns(2)
            with one:
                if st.button("A stronger hint", disabled=not can_run or session["hint_level"] >= 2,
                             use_container_width=True):
                    with st.spinner("Choosing a hint…"):
                        guide(session, exercise, runner, model, stronger=True)
                        persist(session)
                    st.rerun()
            with two:
                if st.button("Retry live guidance", disabled=not can_run, use_container_width=True):
                    with st.spinner("Contacting Gemma…"):
                        guide(session, exercise, runner, model)
                        persist(session)
                    st.rerun()
            st.caption(f'Hint level {session["hint_level"]}/2 · {session["attempts"]} correction attempt(s)')

    if session["stage"] == "reflect" and getattr(exercise, "reflection", None):
        refl = exercise.reflection
        st.markdown('#### <span class="duck-badge badge-reflect">04 Reflect</span> Mental model transfer', unsafe_allow_html=True)
        with st.expander("Transfer Check · Apply what you learned", expanded=session.get("followup_status", "not_attempted") == "not_attempted"):
            st.caption(f"Test your mental model of **{exercise.concept}** on a new example:")
            st.code(refl.transfer_snippet, language="python")
            with st.form(f"transfer_{sid}"):
                followup = st.radio(refl.transfer_prompt, refl.transfer_choices, index=None, key=f"transfer_choice_{sid}")
                reason = st.text_input("Explain your reasoning (optional)")
                submit_followup = st.form_submit_button("Submit Transfer Prediction")
            if submit_followup and followup:
                record_transfer(session, exercise, followup, reason)
                persist(session)
                st.rerun()
            if session.get("followup_status") != "not_attempted":
                correct_answer = refl.transfer_choices[refl.correct_choice_index]
                if session.get("followup_status") == "correct_on_prepared_question":
                    st.success(f"🎯 **Spot on!** You correctly predicted `{correct_answer}`.")
                    st.info(refl.explanation)
                else:
                    st.warning(f"🤔 **Not quite.** The correct output is `{correct_answer}`.")
                    st.info(f"Notice the connection to your earlier bug: {refl.explanation}")

    with st.expander("What actually happened"):
        st.caption("Recorded model decisions and real execution events. No simulated agent activity.")
        st.json(session["events"][-25:])

with notebook:
    st.subheader("A record of your reasoning")
    st.write("Predictions, corrections and checked outcomes are saved automatically on this computer.")
    current_export = json.dumps(session, ensure_ascii=False, indent=2)
    st.download_button("Export current session", current_export,
                       file_name=f'ducktutor-{session["exercise_id"]}-{sid[:8]}.json', mime="application/json")
    records = load_notebook(DATA_DIR)
    if not records:
        st.info("Complete a prediction to create your first entry.")
    for entry in records:
        title = EXERCISES.get(entry.get("exercise_id"))
        with st.expander(f'{title.title if title else entry.get("exercise_id")} · {entry.get("updated_at", "")[:16]}',
                         expanded=entry["id"] == sid):
            st.write(f'**Concept:** {entry.get("concept", "")}')
            st.write(f'Prediction: {entry.get("prediction")} · Confidence: {entry.get("confidence")}/5')
            st.write(f'Observed: {json.dumps(entry.get("initial_observation"), ensure_ascii=False)}')
            st.write(f'Correction attempts: {entry.get("attempts", 0)} · Stronger hints requested: {entry.get("hint_count", 0)}')
            if entry.get("transfer_prediction"):
                transfer_label = "correct" if entry.get("transfer_correct") else "needs review"
                st.caption(f'Solution viewed: {entry.get("solution_viewed", False)} · Transfer check: {entry.get("transfer_prediction")} ({transfer_label})')
            else:
                st.caption(f'Solution viewed: {entry.get("solution_viewed", False)} · Follow-up: {entry.get("followup_status", "not_attempted")}')
            st.caption(f'Validated live model decisions: {entry.get("model_calls", 0)} · Model unavailable/invalid responses: {entry.get("model_unavailable_events", 0)}')
            if entry["id"] != sid:
                if st.button("Resume this session", key=f"resume_{entry['id']}", use_container_width=True):
                    loaded = load_session(entry["id"], DATA_DIR)
                    if loaded:
                        st.session_state["session"] = loaded
                        st.session_state["_pending_exercise"] = loaded["exercise_id"]
                        st.rerun()
