"""Own-code workspace and shared chat rendering."""
import streamlit as st
from core import associate_reported_output, guide, sync_code, update_problem
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
        for field in ["goal", "language", "reported_output", "learner_notes"]:
            state[f"{field}_{sid}"] = session.get(field, "Python" if field == "language" else "")


def sync_widgets(session, state):
    sid = session["id"]
    code = state.get(f"editor_{sid}", session["code"])
    if session.get("mode") == "own_code":
        return update_problem(session, code, state.get(f"goal_{sid}", session.get("goal", "")),
                              state.get(f"reported_output_{sid}", session.get("reported_output", "")),
                              state.get(f"language_{sid}", session.get("language", "Python")),
                              state.get(f"learner_notes_{sid}", session.get("learner_notes", "")))
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


def render_own_code(session, model, persist):
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
        with st.expander("Error or output you observed"):
            st.text_area("Paste the error or output", height=140, max_chars=4000,
                         key=f"reported_output_{sid}")
            st.caption("This is your reported output. The app does not run code in this workspace.")
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
        st.caption("You can ask about a concept without pasting code. Guidance here is code analysis, not an execution verdict.")

    with right:
        st.subheader("Talk it through")
        if not session["messages"]:
            st.info("Ask a question, describe a bug, or explain your approach. The duck can explain concepts, trace your reasoning, and give hints while leaving the final edit to you.")
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
                persist(session)
            st.rerun()
    with st.expander("Session details"):
        st.caption("Model events and response validation. Own-code sessions do not execute submissions.")
        st.json(session["events"][-20:])
