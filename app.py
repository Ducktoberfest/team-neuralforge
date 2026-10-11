"""Run with: python -m streamlit run app.py"""
import json
import os
from pathlib import Path

import streamlit as st

from core import (check_correction, guide, list_saved_sessions, load_notebook,
                  load_session, new_session, predict, reveal, save_notebook, sync_code)
from exercises import EXERCISES
from runner import Runner
from tutor import Gemma, ModelError, context_for, parse_decision

st.set_page_config(page_title="DuckTutor · Think it through", page_icon="🦆", layout="wide")
st.markdown("""<style>
.block-container {max-width:1280px;padding-top:2rem;}
h1,h2,h3 {letter-spacing:-.035em;}
div[data-testid="stMetric"] {border:1px solid #e5e1d8;border-radius:12px;padding:12px;}
div[data-testid="stTextArea"] textarea {font-family:ui-monospace,SFMono-Regular,monospace;font-size:14px;}
div[data-testid="stChatMessage"] {border:1px solid #e5e1d8;border-radius:14px;}
.eyebrow {color:#667064;font-size:12px;letter-spacing:.14em;font-weight:700;}
.hero-note {color:#687069;font-size:17px;margin-bottom:22px;}
</style>""", unsafe_allow_html=True)

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
            model_name = st.selectbox("Gemma model", ["gemma-4-26b-a4b-it", "gemma-4-31b-it"],
                                      index=0, help="gemma-4-26b-a4b-it is the recommended default model.")
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
                st.error(str(exc))
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
st.markdown('<div class="eyebrow">DEBUGGING, WITH UNDERSTANDING</div>', unsafe_allow_html=True)
st.title("Think it through with DuckTutor.")
st.markdown('<div class="hero-note">Predict what happens. Follow the evidence. Make the correction yours.</div>', unsafe_allow_html=True)
if st.session_state.get("save_error"):
    st.error(st.session_state.save_error)

learn, notebook = st.tabs(["Learning session", "My notebook"])

with learn:
    st.subheader(exercise.title)
    st.write(exercise.spec)
    st.caption("01 Predict   →   02 Investigate   →   03 Check your correction   →   04 Reflect")
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("#### Your code")
        if session["stage"] == "predict":
            st.code(exercise.starter, language="python")
            st.caption("Make a prediction first. The editor opens after execution.")
        else:
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
            st.markdown("#### Before we run it…")
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
            st.markdown("#### Investigate with the duck")
            for entry in session["messages"][-10:]:
                with st.chat_message(entry["role"], avatar="🦆" if entry["role"] == "assistant" else None):
                    st.caption(entry["source"])
                    st.text(entry["text"])
            recent_errors = [e for e in session["events"] if e["type"] in {"model_unavailable", "model_response_rejected"}]
            if session["messages"] and session["messages"][-1]["source"].startswith("Exercise hint") and recent_errors:
                st.warning(recent_errors[-1]["error"])
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

    if session["stage"] == "reflect" and exercise.id == "basket":
        with st.expander("Try a related example", expanded=session["followup_status"] == "not_attempted"):
            st.code("first = [1]\nsecond = first\nsecond.append(2)\nprint(first)", language="python")
            with st.form(f"transfer_{sid}"):
                followup = st.radio("What is printed?", ["[1]", "[1, 2]", "[2]"], index=None)
                reason = st.text_input("Explain your prediction")
                submit_followup = st.form_submit_button("Record my answer")
            if submit_followup and followup:
                session["followup_status"] = "correct_on_prepared_question" if followup == "[1, 2]" else "needs_review"
                session["followup_answer"] = {"prediction": followup, "explanation": reason[:1500]}
                persist(session)
                st.rerun()
            if session["followup_status"] != "not_attempted":
                st.info("The checked answer is [1, 2]: both names refer to the same list. This records one follow-up response, not mastery.")

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
            st.write(f'Outcome: {entry.get("outcome", "in_progress").replace("_", " ")}')
            st.caption(f'Solution viewed: {entry.get("solution_viewed", False)} · Follow-up: {entry.get("followup_status", "not_attempted")}')
            st.caption(f'Validated live model decisions: {entry.get("model_calls", 0)} · Model unavailable/invalid responses: {entry.get("model_unavailable_events", 0)}')
            if entry["id"] != sid:
                if st.button("Resume this session", key=f"resume_{entry['id']}", use_container_width=True):
                    loaded = load_session(entry["id"], DATA_DIR)
                    if loaded:
                        st.session_state["session"] = loaded
                        st.session_state["_pending_exercise"] = loaded["exercise_id"]
                        st.rerun()
