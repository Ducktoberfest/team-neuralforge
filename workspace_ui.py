"""Own-code workspace and shared chat rendering."""
import streamlit as st
from core import (associate_reported_output, guide, guide_challenge, guide_tiered,
                  record_own_prediction, record_own_run, sync_code, update_problem)
from runner import Runner
from sound_effects import play_sound
from tutor import reported_output_is_current

LANGUAGES = ["Python", "JavaScript", "TypeScript", "C", "C++", "Java", "SQL", "Other"]


def workspace_scope(session):
    return "own_code" if session.get("mode") == "own_code" else "practice:" + session["exercise_id"]


def session_title(session):
    if session.get("mode") == "own_code":
        return (session.get("goal", "").splitlines() or [""])[0][:65] or "Your code · " + session.get("language", "Python")
    return session.get("concept", session.get("exercise_id", "Practice"))


def hydrate_widgets(session, state):
    sid = session["id"]
    state[f"editor_{sid}"] = session["code"]
    if session.get("mode") == "own_code":
        for field in ["goal", "language", "reported_output", "learner_notes", "prediction", "explanation"]:
            state[f"{field}_{sid}"] = session.get(field, "Python" if field == "language" else "")
        state[f"confidence_{sid}"] = int(session.get("confidence") or 3)
        state[f"test_input_{sid}"] = ""


def sync_widgets(session, state):
    sid = session["id"]
    code = state.get(f"editor_{sid}", session["code"])
    if session.get("mode") == "own_code":
        changed = update_problem(session, code, state.get(f"goal_{sid}", session.get("goal", "")),
                                 state.get(f"reported_output_{sid}", session.get("reported_output", "")),
                                 state.get(f"language_{sid}", session.get("language", "Python")),
                                 state.get(f"learner_notes_{sid}", session.get("learner_notes", "")))
        if f"prediction_{sid}" in state:
            pred = state.get(f"prediction_{sid}")
            conf = state.get(f"confidence_{sid}")
            expl = state.get(f"explanation_{sid}")
            if pred != session.get("prediction") or conf != session.get("confidence") or expl != session.get("explanation"):
                session.update(prediction=pred, confidence=conf, explanation=expl)
                changed = True
        return changed
    return sync_code(session, code)


def render_history(session):
    for entry in session["messages"][-16:]:
        with st.chat_message(entry["role"], avatar="🦆" if entry["role"] == "assistant" else None):
            source = entry.get("source", "Learner")
            if source.startswith("Gemma · "):
                model = source.split(" · ", 1)[1]
                label = {"gemma-4-26b-a4b-it": "Gemma 26B", "gemma-4-31b-it": "Gemma 31B"}.get(model, model)
                st.caption("Duck · " + label)
            else:
                st.caption(source)
            st.markdown(entry["text"])


def render_own_code(session, model, persist, runner=None):
    sid = session["id"]
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.subheader("Your code")
        if f"editor_{sid}" not in st.session_state:
            hydrate_widgets(session, st.session_state)
        st.selectbox("Language", LANGUAGES, key=f"language_{sid}")
        st.text_area("Your code", height=310, max_chars=20000, key=f"editor_{sid}",
                     placeholder="Paste the part you want to understand or debug.", label_visibility="collapsed")
        st.text_area("What should happen?", height=95, max_chars=3000, key=f"goal_{sid}",
                     placeholder="Describe your goal, assignment requirements, or the behavior you want.")

        # 1. Diagnostic Pre-Run Prediction
        with st.expander("🔮 Diagnostic Prediction (Commit before running)", expanded=bool(not session.get("prediction"))):
            st.caption("Commit to an expectation before running code to sharpen your mental model.")
            st.text_input("What do you predict will happen when this code runs with your test input?",
                          key=f"prediction_{sid}",
                          placeholder="e.g. It should return [1, 2] / throw TypeError / loop indefinitely")
            st.slider("Confidence in your prediction", 1, 5, key=f"confidence_{sid}",
                      help="1 = Guess, 5 = Absolutely certain")
            st.text_area("Why do you expect this outcome?", height=75, key=f"explanation_{sid}",
                         placeholder="Explain the language rule, invariant, or assumption you are relying on.")
            if st.button("Record prediction", key=f"record_prediction_{sid}"):
                record_own_prediction(session,
                                      st.session_state.get(f"prediction_{sid}", ""),
                                      st.session_state.get(f"confidence_{sid}", 3),
                                      st.session_state.get(f"explanation_{sid}", ""))
                play_sound("submit")
                persist(session)
                st.success("Diagnostic prediction recorded!")
                st.rerun()

        # 2. Direct Sandboxed Execution for Python
        is_python = st.session_state.get(f"language_{sid}", session.get("language", "Python")) == "Python"
        if is_python:
            st.markdown("#### ⚡ Sandboxed Execution")
            st.text_input("Test input / call snippet (optional)", key=f"test_input_{sid}",
                          placeholder="e.g. add(1, 2) or leave blank to run snippet as-is")
            run_c1, run_c2 = st.columns([1, 1])
            with run_c1:
                run_sandbox = st.button("▶️ Run Code in Sandbox", key=f"run_sandbox_{sid}", use_container_width=True)
            with run_c2:
                mark_solved = st.button("🎉 Mark as Solved", key=f"mark_solved_{sid}", use_container_width=True)

            if run_sandbox:
                if runner is None:
                    runner = Runner("trusted-local", allow_trusted=True, timeout=2)
                test_call = st.session_state.get(f"test_input_{sid}", "").strip()
                script_code = f"actual = {test_call}\nprint(repr(actual))" if test_call else ""
                result = record_own_run(session, runner=runner, script=script_code)
                if session.get("reported_output"):
                    st.session_state[f"reported_output_{sid}"] = session["reported_output"]
                if result.get("status") in {"error", "syntax_error", "timeout", "execution_error"}:
                    play_sound("quack")
                else:
                    play_sound("submit")
                persist(session)
                st.rerun()

            if mark_solved:
                session["verified_hash"] = session["code_hash"]
                session["outcome"] = "solved"
                session.setdefault("events", []).append({
                    "type": "learner_marked_solved",
                    "code_hash": session["code_hash"]
                })
                play_sound("fanfare")
                persist(session)
                st.rerun()

            current_runs = [r for r in session.get("runs", []) if r.get("code_hash") == session["code_hash"]]
            if current_runs:
                latest = current_runs[-1]
                status_badge = "✅ Completed" if latest.get("status") == "completed" else f"⚠️ {latest.get('status')}"
                with st.expander(f"Runtime Evidence ({status_badge})", expanded=True):
                    if latest.get("stdout"):
                        st.caption("Standard Output:")
                        st.code(latest["stdout"], language="text")
                    if latest.get("error"):
                        st.caption("Error / Exception:")
                        st.error(latest["error"])
                    if latest.get("traceback"):
                        with st.expander("Traceback", expanded=False):
                            st.code(latest["traceback"], language="python")
                    st.caption(f"Status: {latest.get('status')} · Duration: {latest.get('duration_ms', 0)}ms · Revision: {latest.get('code_hash')}")

        with st.expander("Error or output you observed"):
            st.text_area("Paste the error or output", height=140, max_chars=4000,
                         key=f"reported_output_{sid}")
            st.caption("This is your reported output. Sandboxed execution above automatically captures live runtime output.")
            confirm = st.button("I reproduced this with the current code", key=f"confirm_output_{sid}",
                                disabled=not bool(st.session_state.get(f"reported_output_{sid}")))
        with st.expander("What I understand so far"):
            st.text_area("Your learning notes", height=100, max_chars=2000,
                         key=f"learner_notes_{sid}", placeholder="Add an insight or correct the duck's interpretation.")
            if session.get("tutor_notes"):
                st.caption("Duck's working notes · tentative interpretations of your replies")
                for note in session["tutor_notes"][-4:]:
                    st.write(note["text"])
        changed = sync_widgets(session, st.session_state)
        if confirm:
            associate_reported_output(session)
            changed = True
        if changed:
            persist(session)
        if session.get("reported_output") and not reported_output_is_current(session):
            st.caption("The pasted output belongs to an earlier code version or language. Update it, or confirm you reproduced it above.")
        st.caption("You can ask about a concept without pasting code. Guidance here is Socratic code analysis.")

    with right:
        st.subheader("Talk it through")
        if not session["messages"]:
            st.info("Ask a question, describe a bug, or choose a tiered hint. The duck helps you analyze runtime evidence and test edge cases.")
        render_history(session)
        assistant = next((m for m in reversed(session["messages"]) if m["role"] == "assistant"), None)
        if assistant and assistant.get("code_hash") != session["code_hash"]:
            st.caption("The code changed since the last reply. Your next message will use this version.")
        if assistant and assistant.get("source", "").startswith("Local guidance"):
            errors = [e for e in session["events"] if e["type"] in {"model_unavailable", "model_response_rejected"}]
            if errors:
                st.warning(errors[-1]["error"])
            if st.button("Retry live tutoring", key=f"own_retry_{sid}"):
                with st.spinner("The duck is considering your code…"):
                    guide(session, None, None, model)
                    persist(session)
                st.rerun()

        # 3. Structured 3-Tier Progressive Hint Controls & Challenge Probes
        st.markdown("##### 💡 Socratic Hint Controls")
        t_col0, t_col1, t_col2 = st.columns(3)
        with t_col0:
            if st.button("🔍 Tier 0: Probe", key=f"hint_tier0_{sid}", use_container_width=True,
                         help="Targeted Socratic question directing attention to runtime evidence"):
                with st.spinner("Preparing probe…"):
                    guide_tiered(session, model, tier=0)
                    play_sound("hint")
                    persist(session)
                st.rerun()
        with t_col1:
            if st.button("🧠 Tier 1: Model", key=f"hint_tier1_{sid}", use_container_width=True,
                         help="Explains the underlying language mechanism without referencing the fix"):
                with st.spinner("Analyzing mental model…"):
                    guide_tiered(session, model, tier=1)
                    play_sound("hint")
                    persist(session)
                st.rerun()
        with t_col2:
            if st.button("📍 Tier 2: Location", key=f"hint_tier2_{sid}", use_container_width=True,
                         help="Pinpoints specific line or variable interaction causing discrepancy"):
                with st.spinner("Locating discrepancy…"):
                    guide_tiered(session, model, tier=2)
                    play_sound("hint")
                    persist(session)
                st.rerun()

        if st.button("🎯 Ask Duck for a Challenge Case", key=f"own_challenge_{sid}", use_container_width=True,
                     help="Asks Gemma for a targeted edge-case counterexample to test your code"):
            with st.spinner("The duck is devising an edge-case challenge…"):
                guide_challenge(session, model)
                play_sound("hint")
                persist(session)
            st.rerun()

        prompt = st.chat_input("Ask the duck, or explain what you tried…", key=f"own_chat_{sid}", max_chars=3000)
        if prompt:
            with st.spinner("The duck is considering your question…"):
                guide(session, None, None, model, prompt)
                persist(session)
            st.rerun()
        if session["messages"] and st.button("Give me a clearer hint", key=f"own_hint_{sid}",
                                            disabled=session["hint_level"] >= 2):
            with st.spinner("Finding a more concrete clue…"):
                guide(session, None, None, model, stronger=True)
                play_sound("hint")
                persist(session)
            st.rerun()
    with st.expander("Session details"):
        st.caption("Model events and response validation.")
        st.json(session["events"][-20:])
