"""Run with: python -m streamlit run app.py"""
import hashlib
import json
import os
from pathlib import Path

import streamlit as st

from core import (check_correction, guide, list_saved_sessions, load_notebook,
                  load_session, new_session, predict, record_transfer, reveal, save_notebook, sync_code)
from exercises import EXERCISES
from runner import Runner
from sound_effects import queue_sound, render_audio_sidebar, render_pending_sound
from tutor import Gemma, ModelError, context_for, parse_decision

def inject_custom_styles():
    # Native Streamlit theming owns widget colors, focus rings, menus and alerts.
    # Keep custom CSS scoped to our own markup and the code editor.
    st.markdown("""<style>
/* Preserve Streamlit's native top clearance for its toolbar. */
.block-container { max-width: 1280px; padding-bottom: 2rem; }
.duck-header-bar { display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 10px; padding: 12px 16px; border-radius: 12px;
    background: #161b22; border: 1px solid #30363d; margin-bottom: 18px; }
.duck-header-left, .duck-header-right { display: flex; align-items: center; gap: 10px;
    flex-wrap: wrap; }
.duck-logo { font-size: 1.4rem; }
.duck-title { font-weight: 700; color: #e6edf3; font-size: 1.1rem; }
.duck-edition { background: #173e2c; color: #7ee787; padding: 3px 9px;
    border-radius: 12px; font-size: .75rem; }
.duck-team { color: #8b949e; font-size: .82rem; }
.duck-version { color: #7ee787; font-size: .8rem; }
.eyebrow { color: #8b949e; font-size: .72rem; letter-spacing: .1em; margin-bottom: 4px; }
.hero-note { color: #aeb8c5; margin-bottom: 12px; }
.stage-stepper { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 20px; }
.stepper-pill { font-size: .78rem; font-weight: 600; padding: 7px 12px;
    border-radius: 20px; background: #161b22; border: 1px solid #30363d; color: #8b949e; }
.stepper-pill.active { background: #172c45; border-color: #58a6ff; color: #9acbff; }
.duck-badge { padding: 3px 9px; border-radius: 8px; font-size: .72rem; font-weight: 600;
    display: inline-flex; align-items: center; margin-right: 6px; vertical-align: middle; }
.badge-predict { background: #172c45; color: #9acbff; }
.badge-investigate { background: #382d12; color: #f2d276; }
.badge-check { background: #173e2c; color: #8ddcae; }
.badge-reflect { background: #302443; color: #d2b4ff; }
.badge-offline { background: #382d12; color: #f2d276; }
textarea[aria-label="Python editor"] {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    line-height: 1.6; tab-size: 4; }
@media (max-width: 640px) {
    .duck-header-right { display: none; }
    .duck-edition { font-size: .7rem; }
    .stepper-pill { padding: 5px 9px; }
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


def restore_session(session_id):
    """Callbacks run before widgets render, so restored code wins over stale input."""
    loaded = load_session(session_id, DATA_DIR)
    if not loaded or loaded.get("exercise_id") not in EXERCISES:
        st.session_state["resume_error"] = "This saved session could not be restored."
        return
    previous = st.session_state.get("session")
    if previous and previous["id"] != session_id:
        pending_code = st.session_state.get(f"editor_{previous['id']}")
        if pending_code is not None:
            sync_code(previous, pending_code)
        persist(previous)
    st.session_state["session"] = loaded
    st.session_state[f"editor_{loaded['id']}"] = loaded["code"]
    st.session_state["_pending_exercise"] = loaded["exercise_id"]
    st.session_state.pop("resume_error", None)


def connection_signature(model):
    # In-memory identity only. The key and this digest never enter the notebook.
    config = [model.provider, model.model, model.base_url, model.key or ""]
    return hashlib.sha256(json.dumps(config).encode()).hexdigest()


def test_connection(model, exercise):
    result = {"signature": connection_signature(model), "model": model.model}
    context = context_for(st.session_state.session, exercise, "connection_check", ["ask_question"], [])
    try:
        raw, latency = model.decide(context)
        response = parse_decision(raw, context)
        result.update(ok=True, latency_ms=latency, message=response["message"],
                      response_info=model.last_response_info)
    except ModelError as exc:
        result.update(ok=False, error=str(exc))
    st.session_state["connection_result"] = result


def retry_connection_with_26b():
    st.session_state["_pending_model"] = "gemma-4-26b-a4b-it"
    st.session_state["_retry_connection"] = True



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
                "gemma-4-26b-a4b-it": "Gemma 26B · default",
                "gemma-4-31b-it": "Gemma 31B · optional",
            }
            model_name = st.selectbox(
                "Gemma model",
                ["gemma-4-26b-a4b-it", "gemma-4-31b-it"],
                index=0,
                format_func=lambda m: MODEL_LABELS.get(m, m),
                key="gemma_model_select",
                help="26B is the demo default. 31B remains available, with a longer request timeout."
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
        requested_check = st.button("Test Gemma connection", key="test_connection",
                                    use_container_width=True)
        queued_check = st.session_state.pop("_retry_connection", False)
        if requested_check or queued_check:
            with st.spinner(f"Checking {model.model}…"):
                test_connection(model, exercise)
        connection = st.session_state.get("connection_result")
        if connection and connection["signature"] == connection_signature(model):
            if connection["ok"]:
                info = connection.get("response_info", {})
                returned = info.get("response_model") or connection["model"]
                st.success(f"Last check passed · {returned} · {connection['latency_ms'] / 1000:.1f}s")
                st.caption("This records the last test; it does not guarantee the next request will succeed.")
                with st.expander("Connection test response"):
                    st.write(connection["message"])
            else:
                st.warning(connection["error"])
                if provider == "google" and model.model == "gemma-4-31b-it":
                    st.button("Switch to Gemma 26B & Retry", key="sidebar_switch_26b",
                              on_click=retry_connection_with_26b, use_container_width=True)
        else:
            st.caption("Connection not checked for these settings.")
        st.caption(f"Request timeout: {model.timeout}s. Exercise hints remain available if the model fails.")
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
            st.button("Load Session", key="load_session_btn", use_container_width=True,
                      on_click=restore_session, args=(chosen_sid,))
    st.divider()
    render_audio_sidebar()

render_pending_sound()

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
    <span class="duck-version">v0.2.3</span>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">DEBUGGING, WITH UNDERSTANDING</div>', unsafe_allow_html=True)
st.title("Think it through with DuckTutor.")
st.markdown('<div class="hero-note">Predict what happens. Follow the evidence. Make the correction yours.</div>', unsafe_allow_html=True)
if st.session_state.get("save_error"):
    st.error(st.session_state.save_error)
if st.session_state.get("resume_error"):
    st.error(st.session_state.resume_error)

learn, notebook = st.tabs(["Learning session", "My notebook"])

with learn:
    st.subheader(exercise.title)
    st.write(exercise.spec)

    cur_stage = session["stage"]
    p_act = "active" if cur_stage == "predict" else ""
    i_act = "active" if cur_stage == "guide" and session.get("attempts", 0) == 0 else ""
    c_act = "active" if cur_stage == "guide" and session.get("attempts", 0) > 0 else ""
    r_act = "active" if cur_stage == "reflect" else ""

    st.markdown(f"""<div class="stage-stepper">
      <span class="stepper-pill {p_act}">01 Predict</span>
      <span style="color: #484f58; display: flex; align-items: center;">→</span>
      <span class="stepper-pill {i_act}">02 Investigate</span>
      <span style="color: #484f58; display: flex; align-items: center;">→</span>
      <span class="stepper-pill {c_act}">03 Check</span>
      <span style="color: #484f58; display: flex; align-items: center;">→</span>
      <span class="stepper-pill {r_act}">04 Reflect</span>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        if session["stage"] == "predict":
            st.markdown('#### <span class="duck-badge badge-predict">01 Predict</span> Starter code', unsafe_allow_html=True)
            st.code(exercise.starter, language="python")
            st.caption("Make a prediction first. The editor opens after execution.")
        else:
            st.markdown('#### <span class="duck-badge badge-check">03 Check</span> Python editor & verification', unsafe_allow_html=True)
            editor_key = f"editor_{sid}"
            if editor_key not in st.session_state:
                st.session_state[editor_key] = session["code"]
            code = st.text_area("Python editor", height=235, max_chars=20000,
                                key=editor_key, label_visibility="collapsed")
            if sync_code(session, code):
                persist(session)
            st.caption("Edit your code, then check it against the exercise cases.")
            if st.button("Check my correction", type="primary", disabled=not can_run,
                         use_container_width=True, key="check_correction"):
                with st.spinner("Checking code and investigating the result…"):
                    check_correction(session, exercise, runner, model)
                    if session.get("verified_hash") and session.get("verified_hash") == session.get("code_hash"):
                        queue_sound("success")
                    else:
                        queue_sound("retry")
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
            st.caption("Your prediction matched the original execution. Compare that behavior with the stated specification." if matched is True else
                       "Prediction differed from the original execution." if matched is False else
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
                        st.write("Required by the specification for this check")
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
                        queue_sound("curious")
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
                    st.write(entry["text"])
            recent_errors = [e for e in session["events"] if e["type"] in {"model_unavailable", "model_response_rejected"}]
            if session["messages"] and session["messages"][-1]["source"].startswith("Exercise hint") and recent_errors:
                last_err = recent_errors[-1]["error"]
                is_31b = provider == "google" and model.model == "gemma-4-31b-it"
                is_server_err = any(code in last_err for code in ("500", "502", "503", "504"))
                st.warning(last_err)
                if is_31b and is_server_err:
                    if st.button("Switch to Gemma 26B & Retry", key=f"switch_26b_{sid}", type="primary", use_container_width=True):
                        st.session_state["_pending_model"] = "gemma-4-26b-a4b-it"
                        model_26b = Gemma(key=key, model="gemma-4-26b-a4b-it", provider=provider, base_url=endpoint)
                        with st.spinner("Retrying with Gemma 26B…"):
                            guide(session, exercise, runner, model_26b)
                            persist(session)
                        st.rerun()
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
                        queue_sound("hint")
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
                if session.get("followup_status") == "correct_on_prepared_question":
                    queue_sound("success")
                else:
                    queue_sound("retry")
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
                st.button("Resume this session", key=f"resume_{entry['id']}",
                          use_container_width=True, on_click=restore_session,
                          args=(entry["id"],))
