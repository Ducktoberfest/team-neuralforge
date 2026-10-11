"""One integrated learning session; the model never determines test verdicts."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid

from runner import revision
from tutor import InvalidResponse, ModelError, context_for, parse_decision


def load_env_file(path=None, override=False):
    """Load key-value pairs from a .env file into os.environ.

    Standard-library only: ignores comments (#) and empty lines, strips quotes.
    Does not overwrite existing non-empty system environment variables unless missing or override=True.
    Returns the dictionary of loaded variables.
    """
    if path is None:
        path = Path(__file__).resolve().parent / ".env"
    else:
        path = Path(path)
    loaded = {}
    if not path.is_file():
        return loaded
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return loaded
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and ((val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))):
            val = val[1:-1]
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = val
            loaded[key] = val
        else:
            loaded[key] = os.environ[key]
    return loaded


def now():
    return datetime.now(timezone.utc).isoformat()


def new_session(exercise=None):
    own_code = exercise is None
    code = "" if own_code else exercise.starter
    return {"schema_version": 1, "id": uuid.uuid4().hex,
            "mode": "own_code" if own_code else "practice",
            "exercise_id": "own_code" if own_code else exercise.id,
            "exercise_version": 1, "concept": "Your code" if own_code else exercise.concept,
            "started_at": now(), "updated_at": now(), "stage": "guide" if own_code else "predict",
            "code": code, "code_hash": revision(code),
            "language": "Python", "goal": "", "reported_output": "",
            "reported_output_code_hash": None, "reported_output_language": None,
            "learner_notes": "", "tutor_notes": [],
            "prediction": None, "confidence": None, "explanation": "",
            "initial_observation": None, "prediction_matches_execution": None,
            "messages": [], "runs": [], "events": [], "attempts": 0,
            "hint_level": 0, "hint_count": 0, "solution_viewed": False,
            "verified_hash": None, "outcome": "in_progress", "model_calls": 0,
            "model_unavailable_events": 0, "followup_status": "not_attempted",
            "transfer_prediction": None, "transfer_correct": None}


def message(session, text, source="Gemma", role="assistant"):
    session["messages"].append({"role": role, "text": text, "source": source,
                                "code_hash": session["code_hash"]})


def update_problem(session, code, goal, reported_output, language, learner_notes=""):
    """Keep reported output attached to the revision/language when it was supplied."""
    before = (session["code"], session.get("goal"), session.get("reported_output"),
              session.get("language"), session.get("learner_notes"))
    sync_code(session, code[:20000])
    session.update(goal=goal[:3000], language=language, learner_notes=learner_notes[:2000])
    if reported_output != session.get("reported_output", ""):
        session["reported_output"] = reported_output[:4000]
        associate_reported_output(session)
    return before != (session["code"], session["goal"], session["reported_output"],
                      session["language"], session["learner_notes"])


def associate_reported_output(session):
    session["reported_output_code_hash"] = session["code_hash"] if session.get("reported_output") else None
    session["reported_output_language"] = session.get("language", "Python") if session.get("reported_output") else None


def sync_code(session, code):
    if code == session["code"]:
        return False
    session.update(code=code, code_hash=revision(code), verified_hash=None,
                   outcome="in_progress", stage="guide")
    if "learner_code" in session:
        session["learner_code"] = code
    session.setdefault("events", []).append({
        "type": "code_revision",
        "code_hash": session["code_hash"],
    })
    return True


def record_run(session, exercise, runner, case_id):
    result = runner.run(exercise, session["code"], case_id)
    session["runs"].append(result)
    session["events"].append({"type": "execution", "case_id": case_id,
                              "run_id": result["id"], "code_hash": session["code_hash"]})
    return result


def record_own_prediction(session, prediction, confidence, explanation=""):
    """Record diagnostic pre-run prediction and confidence in own-code session."""
    session.update(prediction=prediction, confidence=confidence, explanation=explanation[:1500])
    session.setdefault("events", []).append({
        "type": "diagnostic_prediction",
        "code_hash": session["code_hash"],
        "prediction": prediction,
        "confidence": confidence,
        "explanation": explanation[:1500],
    })
    return session


def record_own_run(session, runner=None, code=None, script=""):
    """Execute own code in the sandbox and capture results as evidence."""
    if code is not None:
        sync_code(session, code)
    if not runner:
        from runner import Runner
        runner = Runner("trusted-local", allow_trusted=True, timeout=2)
    result = runner.run_custom(session["code"], script=script)
    session.setdefault("runs", []).append(result)
    session["attempts"] = session.get("attempts", 0) + 1
    session.setdefault("events", []).append({
        "type": "own_execution",
        "run_id": result["id"],
        "code_hash": session["code_hash"],
        "status": result["status"],
    })
    captured = result.get("stdout", "")
    if result.get("error"):
        captured = (captured + "\n" if captured else "") + result["error"]
    if captured.strip():
        session["reported_output"] = captured.strip()[:4000]
        associate_reported_output(session)
    return result


def guide_tiered(session, model, tier: int = 0):
    """Deliver a structured Socratic hint according to the selected tier.
    Tier 0 (Probe): Asks a targeted Socratic question directing attention to runtime evidence.
    Tier 1 (Mental Model): Explains the underlying language mechanism without referencing the fix.
    Tier 2 (Location): Points out the specific line or variable interaction causing discrepancy.
    """
    session["hint_level"] = max(0, min(2, tier))
    session["hint_count"] += 1
    tier_names = {0: "Probe", 1: "Mental Model", 2: "Location"}
    name = tier_names.get(session["hint_level"], "Hint")
    message(session, f"Requested Tier {session['hint_level']} Hint ({name})", "Learner", "user")
    budget = [2]
    allowed = ["ask_question", "explain_concept", "give_hint", "recap"]
    return decide(session, None, model, f"tiered_hint_{session['hint_level']}", allowed, budget=budget)


def guide_challenge(session, model):
    """Ask Gemma for a targeted edge-case counterexample or challenge case."""
    message(session, "Can you provide a challenge test case or edge-case input to test my code?", "Learner", "user")
    budget = [2]
    allowed = ["ask_question", "explain_concept", "give_hint"]
    item = decide(session, None, model, "challenge_case_request", allowed, budget=budget)
    if item:
        session["challenge_case"] = item["message"]
    return item


def fallback_question(session, exercise):
    if session.get("mode") == "own_code":
        tier = session.get("hint_level", 0)
        if tier == 1:
            return ("Consider how the programming language handles evaluation and scope here. "
                    "Does each operation produce a new value or modify existing data? "
                    "Reflect on how this applies to your code.")
        elif tier == 2:
            return ("Look closely at the line where your key variable is assigned or modified. "
                    "What is its exact value right before the unexpected outcome occurs?")
        current_runs = [r for r in session.get("runs", []) if r.get("code_hash") == session["code_hash"]]
        if current_runs and current_runs[-1].get("status") in {"error", "syntax_error"}:
            return f"The latest execution produced an error: {current_runs[-1].get('error')}. What does this traceback tell you about the problem?"
        if session.get("prediction"):
            return f"You predicted: '{session.get('prediction')}'. How does that compare with what actually happened when the code ran?"
        return ("The live tutor could not respond. You can still save your code and reasoning. "
                "For debugging, identify one input that exposes the issue and compare the result "
                "with what you wanted. Retry the live tutor when the connection is available.")
    current = [r for r in session["runs"] if r["code_hash"] == session["code_hash"]]
    if current and current[-1]["status"] != "completed":
        return "The last run did not complete. What does the displayed error tell you about the next step?"
    if session["verified_hash"] == session["code_hash"]:
        return f"All {len(exercise.cases)} checked cases passed for this revision. What changed in your reasoning?"
    if current and current[-1]["case_id"] == "provided_empty" and not current[-1]["passed"]:
        return "Compare the returned list with the caller's basket. Which requirement does this result leave unmet?"
    failed = [r["case_id"] for r in session["runs"] if r["code_hash"] == session["code_hash"] and not r["passed"]]
    if "separate_cells" in failed:
        return "What happens to the inner lists when an outer list is copied with list() or .copy()?"
    if "consecutive_calls" in failed:
        return "What happens to variable lookup when an assignment appears inside an inner function?"
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
                                      "model": model.model, "duration_ms": elapsed,
                                      "response_info": getattr(model, "last_response_info", {})})
            message(session, item["message"], f"Gemma · {model.model}")
            note = item.get("learning_note")
            if note:
                notes = session.setdefault("tutor_notes", [])
                if not notes or notes[-1]["text"] != note:
                    notes.append({"text": note, "code_hash": session["code_hash"],
                                  "source": "model interpretation"})
                session["tutor_notes"] = notes[-6:]
            return item
        except InvalidResponse as exc:
            session["model_unavailable_events"] += 1
            session["events"].append({"type": "model_response_rejected", "error": str(exc),
                                      "event": event, "model": model.model, "will_retry": budget[0] > 0,
                                      "response_info": getattr(model, "last_response_info", {})})
            source = "Exercise hint · model response could not be used"
            if budget[0] > 0:
                # Re-request against the same evidence. Do not reuse the rejected
                # output as instructions or display it (it might reveal a solution).
                context = {**context, "response_retry": {
                    "reason": str(exc),
                    "instruction": "Correct the stated validation issue. Return one JSON object with required keys action, message, case_id, evidence_ids, and optionally learning_note. Use only allowed actions and evidence IDs; give a new explanation or clue instead of repeating a question."}}
        except ModelError as exc:
            session["model_unavailable_events"] += 1
            session["events"].append({"type": "model_unavailable", "error": str(exc),
                                      "event": event, "model": model.model})
            source = "Exercise hint · live Gemma unavailable"
            break
    if session.get("mode") == "own_code":
        source = {"Exercise hint · live Gemma unavailable": "Local guidance · model unavailable",
                  "Exercise hint · model response could not be used": "Local guidance · response not usable"}.get(
                      source, "Local guidance · request limit")
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
    parsed_choice = None
    if choice != "I'm not sure":
        try:
            parsed_choice = json.loads(choice)
        except (json.JSONDecodeError, TypeError):
            parsed_choice = choice
    session["prediction_matches_execution"] = (
        None if choice == "I'm not sure" else parsed_choice == result["actual"])
    session["stage"] = "guide"
    message(session, f"Prediction: {choice}. Confidence: {confidence}/5. {explanation}", "Learner", "user")
    decide(session, exercise, model, "prediction_observed", ("ask_question", "explain_concept", "give_hint"))


def guide(session, exercise, runner, model, text=None, stronger=False):
    budget = [2]
    if text:
        message(session, text[:3000], "Learner", "user")
    if stronger:
        session["hint_level"] = min(2, session["hint_level"] + 1)
        session["hint_count"] += 1
    allowed = ["ask_question", "explain_concept", "give_hint"]
    if session.get("mode") == "own_code":
        allowed.append("recap")
        return decide(session, None, model, "stronger_hint" if stronger else "learner_reply", allowed, budget=budget)
    cases = [c.id for c in exercise.cases]
    if session["verified_hash"] == session["code_hash"]:
        allowed.append("recap")
    else:
        allowed.append("run_case")
    item = decide(session, exercise, model, "stronger_hint" if stronger else "learner_reply", allowed, cases, budget)
    if item and item["action"] == "run_case":
        record_run(session, exercise, runner, item["case_id"])
        decide(session, exercise, model, "selected_case_observed", ("ask_question", "explain_concept", "give_hint"), budget=budget)


def check_correction(session, exercise, runner, model):
    budget = [2]
    session["attempts"] += 1
    session.update(verified_hash=None, outcome="in_progress", stage="guide")
    first = record_run(session, exercise, runner, exercise.cases[0].id)
    if first["status"] != "completed" or not first["passed"]:
        decide(session, exercise, model, "first_check_failed", ("ask_question", "explain_concept", "give_hint"), budget=budget)
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
    decide(session, exercise, model, "checks_observed", ("recap",) if passed else ("ask_question", "explain_concept", "give_hint"), budget=budget)


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
                    "mode": entry.get("mode", "practice"),
                    "goal": entry.get("goal", ""),
                    "language": entry.get("language", "Python"),
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
        "mode": data.get("mode", "practice"),
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
        "model_requests": data.get("model_requests", 0),
        "language": data.get("language", "Python"),
        "goal": data.get("goal", ""),
        "reported_output": data.get("reported_output", ""),
        "reported_output_code_hash": data.get("reported_output_code_hash"),
        "reported_output_language": data.get("reported_output_language"),
        "learner_notes": data.get("learner_notes", ""),
        "tutor_notes": data.get("tutor_notes", []),
        "challenge_case": data.get("challenge_case"),
    }
    return session

