"""One integrated learning session; the model never determines test verdicts."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid

from runner import revision
from tutor import InvalidResponse, ModelError, context_for, parse_decision


def now():
    return datetime.now(timezone.utc).isoformat()


def new_session(exercise):
    return {"schema_version": 1, "id": uuid.uuid4().hex, "exercise_id": exercise.id,
            "exercise_version": 1, "concept": exercise.concept,
            "started_at": now(), "updated_at": now(), "stage": "predict",
            "code": exercise.starter, "code_hash": revision(exercise.starter),
            "prediction": None, "confidence": None, "explanation": "",
            "initial_observation": None, "prediction_matches_execution": None,
            "messages": [], "runs": [], "events": [], "attempts": 0,
            "hint_level": 0, "hint_count": 0, "solution_viewed": False,
            "verified_hash": None, "outcome": "in_progress", "model_calls": 0,
            "model_unavailable_events": 0, "followup_status": "not_attempted",
            "transfer_prediction": None, "transfer_correct": None}


def message(session, text, source="Gemma", role="assistant"):
    session["messages"].append({"role": role, "text": text, "source": source})


def sync_code(session, code):
    if code == session["code"]:
        return False
    session.update(code=code, code_hash=revision(code), verified_hash=None,
                   outcome="in_progress", stage="guide")
    if "learner_code" in session:
        session["learner_code"] = code
    return True


def record_run(session, exercise, runner, case_id):
    result = runner.run(exercise, session["code"], case_id)
    session["runs"].append(result)
    session["events"].append({"type": "execution", "case_id": case_id,
                              "run_id": result["id"], "code_hash": session["code_hash"]})
    return result


def fallback_question(session, exercise):
    current = [r for r in session["runs"] if r["code_hash"] == session["code_hash"]]
    if current and current[-1]["status"] != "completed":
        return "The last run did not complete. What does the displayed error tell you about the next step?"
    if session["verified_hash"] == session["code_hash"]:
        return f"All {len(exercise.cases)} checked cases passed for this revision. What changed in your reasoning?"
    if current and current[-1]["case_id"] == "provided_empty" and not current[-1]["passed"]:
        return "Compare the returned list with the caller's basket. Which requirement does this result leave unmet?"
    if session["hint_level"] > 0:
        return exercise.hints[session["hint_level"]]
    if session["prediction_matches_execution"] is True:
        return "Your prediction matched execution. How does that behavior compare with the stated specification?"
    return "What difference do you notice between the observed result and the result you expected?"


def decide(session, exercise, model, event, actions, cases=(), budget=None):
    # Share the same budget across selection, optional repair and post-run feedback.
    # A formatting repair never creates an unbounded retry loop.
    budget = [2] if budget is None else budget
    context = context_for(session, exercise, event, list(actions), list(cases))
    source = "Exercise feedback · per-action request limit"
    if budget[0] <= 0:
        session["events"].append({"type": "model_budget_exhausted", "event": event})
    while budget[0] > 0:
        budget[0] -= 1
        session["model_requests"] = session.get("model_requests", 0) + 1
        try:
            raw, elapsed = model.decide(context)
            item = parse_decision(raw, context)
            session["model_calls"] += 1
            session["events"].append({"type": "model_decision", "action": item["action"],
                                      "case_id": item["case_id"], "evidence_ids": item["evidence_ids"],
                                      "model": model.model, "duration_ms": elapsed})
            message(session, item["message"], f"Gemma · {model.model}")
            return item
        except InvalidResponse as exc:
            session["model_unavailable_events"] += 1
            session["events"].append({"type": "model_response_rejected", "error": str(exc),
                                      "event": event, "will_retry": budget[0] > 0,
                                      "response_info": getattr(model, "last_response_info", {})})
            source = "Exercise hint · model response could not be used"
            if budget[0] > 0:
                # Re-request against the same evidence. Do not reuse the rejected
                # output as instructions or display it (it might reveal a solution).
                context = {**context, "response_retry": {
                    "reason": str(exc),
                    "instruction": "Return only one valid JSON object using the exact keys. No fence, prose, or extra fields. Keep message short. Use only allowed actions and evidence IDs."}}
        except ModelError as exc:
            session["model_unavailable_events"] += 1
            session["events"].append({"type": "model_unavailable", "error": str(exc), "event": event})
            source = "Exercise hint · live Gemma unavailable"
            break
    message(session, fallback_question(session, exercise), source)
    return None


def predict(session, exercise, runner, model, choice, confidence, explanation):
    if session["stage"] != "predict":
        return
    session.update(prediction=choice, confidence=confidence, explanation=explanation[:1500])
    result = record_run(session, exercise, runner, "prediction")
    if result["status"] != "completed":
        return  # User can retry after repairing the runner. No invented observation.
    session["initial_observation"] = result["actual"]
    session["prediction_matches_execution"] = (
        None if choice == "I'm not sure" else json.loads(choice) == result["actual"])
    session["stage"] = "guide"
    message(session, f"Prediction: {choice}. Confidence: {confidence}/5. {explanation}", "Learner", "user")
    decide(session, exercise, model, "prediction_observed", ("ask_question",))


def guide(session, exercise, runner, model, text=None, stronger=False):
    budget = [2]
    if text:
        message(session, text[:1500], "Learner", "user")
    if stronger:
        session["hint_level"] = min(2, session["hint_level"] + 1)
        session["hint_count"] += 1
    allowed = ["ask_question"]
    cases = [c.id for c in exercise.cases]
    if session["verified_hash"] == session["code_hash"]:
        allowed.append("recap")
    else:
        allowed.append("run_case")
    item = decide(session, exercise, model, "stronger_hint" if stronger else "learner_reply", allowed, cases, budget)
    if item and item["action"] == "run_case":
        record_run(session, exercise, runner, item["case_id"])
        decide(session, exercise, model, "selected_case_observed", ("ask_question",), budget=budget)


def check_correction(session, exercise, runner, model):
    budget = [2]
    session["attempts"] += 1
    session.update(verified_hash=None, outcome="in_progress", stage="guide")
    first = record_run(session, exercise, runner, exercise.cases[0].id)
    if first["status"] != "completed" or not first["passed"]:
        decide(session, exercise, model, "first_check_failed", ("ask_question",), budget=budget)
        return
    remaining = [c.id for c in exercise.cases[1:]]
    decision = decide(session, exercise, model, "choose_challenge", ("run_case",), remaining, budget)
    selected = decision["case_id"] if decision else remaining[0]
    if not decision:
        session["events"].append({"type": "controller_fallback", "case_id": selected})
    challenge = record_run(session, exercise, runner, selected)
    passed = challenge["status"] == "completed" and challenge["passed"]
    if passed:
        for case_id in remaining:
            if case_id != selected:
                result = record_run(session, exercise, runner, case_id)
                passed &= result["status"] == "completed" and result["passed"]
    if passed:
        session.update(verified_hash=session["code_hash"], stage="reflect",
                       outcome="checked_cases_passed_after_reveal" if session["solution_viewed"] else "checked_cases_passed")
    decide(session, exercise, model, "checks_observed", ("recap",) if passed else ("ask_question",), budget=budget)


def reveal(session):
    session["solution_viewed"] = True
    if session["verified_hash"] == session["code_hash"]:
        session["outcome"] = "checked_cases_passed_after_reveal"
    session["events"].append({"type": "solution_revealed"})


def record_transfer(session, exercise, choice, explanation=""):
    reflection = getattr(exercise, "reflection", None)
    if not reflection:
        return False
    choices = reflection["transfer_choices"] if isinstance(reflection, dict) else reflection.transfer_choices
    correct_idx = reflection["correct_choice_index"] if isinstance(reflection, dict) else reflection.correct_choice_index
    correct_choice = choices[correct_idx]
    is_correct = (choice == correct_choice)
    session["followup_status"] = "correct_on_prepared_question" if is_correct else "needs_review"
    session["transfer_prediction"] = choice
    session["transfer_correct"] = is_correct
    session["followup_answer"] = {
        "prediction": choice,
        "explanation": explanation[:1500] if explanation else "",
        "correct": is_correct,
    }
    session["reflection_response"] = session["followup_answer"]
    session["events"].append({
        "type": "transfer_check_submitted",
        "choice": choice,
        "correct": is_correct,
    })
    return is_correct


def save_notebook(session, directory):
    """One record per session, atomic replacement. No credentials or provider raw responses."""
    session["updated_at"] = now()
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f'{session["id"]}.json'
    name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder,
                                         prefix=".writing-", delete=False) as handle:
            name = handle.name
            json.dump(session, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, destination)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def load_notebook(directory):
    records = []
    for path in sorted(Path(directory).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            entry = json.loads(path.read_text())
            if entry.get("schema_version") == 1 and "id" in entry:
                records.append(entry)
        except (ValueError, OSError, AttributeError):
            continue
    return records[:100]


def list_saved_sessions(directory=None):
    """Safely inspect directory/*.json and return metadata list."""
    folder = Path(directory or os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
    if not folder.exists():
        return []
    items = []
    for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(entry, dict) and entry.get("schema_version") == 1 and "id" in entry:
                items.append({
                    "id": entry["id"],
                    "exercise_id": entry.get("exercise_id"),
                    "concept": entry.get("concept", entry.get("exercise_id")),
                    "stage": entry.get("stage", "predict"),
                    "started_at": entry.get("started_at"),
                    "updated_at": entry.get("updated_at"),
                    "code_hash": entry.get("code_hash"),
                    "outcome": entry.get("outcome", "in_progress"),
                })
        except (ValueError, OSError, AttributeError):
            continue
    return items[:100]


def load_session(session_id, directory=None):
    """Read data/<session_id>.json and return a fully restored session dict."""
    if not session_id or not isinstance(session_id, str):
        return None
    folder = Path(directory or os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
    path = folder / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None

    if not isinstance(data, dict) or data.get("schema_version") != 1 or "id" not in data:
        return None

    code = data.get("code", "")
    code_hash = revision(code)
    verified = data.get("verified_hash")
    # Invariant: verified_hash is only valid if it matches the current code hash
    verified_hash = verified if verified == code_hash else None

    session = {
        "schema_version": 1,
        "id": data["id"],
        "exercise_id": data.get("exercise_id"),
        "exercise_version": data.get("exercise_version", 1),
        "concept": data.get("concept", ""),
        "started_at": data.get("started_at", now()),
        "updated_at": data.get("updated_at", now()),
        "stage": data.get("stage", "predict"),
        "code": code,
        "learner_code": code,
        "code_hash": code_hash,
        "verified_hash": verified_hash,
        "prediction": data.get("prediction"),
        "confidence": data.get("confidence"),
        "explanation": data.get("explanation", ""),
        "learner_explanation": data.get("explanation", ""),
        "initial_observation": data.get("initial_observation"),
        "prediction_matches_execution": data.get("prediction_matches_execution"),
        "messages": list(data.get("messages", [])),
        "runs": list(data.get("runs", [])),
        "events": list(data.get("events", [])),
        "attempts": data.get("attempts", 0),
        "hint_level": data.get("hint_level", 0),
        "hint_count": data.get("hint_count", 0),
        "solution_viewed": bool(data.get("solution_viewed", False)),
        "solution_revealed": bool(data.get("solution_viewed", False)),
        "outcome": data.get("outcome", "in_progress"),
        "model_calls": data.get("model_calls", 0),
        "model_unavailable_events": data.get("model_unavailable_events", 0),
        "followup_status": data.get("followup_status", "not_attempted"),
        "followup_answer": data.get("followup_answer"),
        "reflection_response": data.get("followup_answer"),
        "transfer_prediction": data.get("transfer_prediction"),
        "transfer_correct": data.get("transfer_correct"),
    }
    return session

