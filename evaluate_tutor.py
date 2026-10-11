"""Run controlled live conversations; teaching quality is scored by a human, not this script."""
import argparse
import getpass
import json
import os
from pathlib import Path

from core import guide, load_env_file, new_session, predict, update_problem
from exercises import EXERCISES
from runner import Runner
from tutor import Gemma

CASES = Path(__file__).with_name("conversation_evals.json")


def run_case(case, model):
    practice = case["mode"] == "practice"
    exercise = EXERCISES[case["exercise_id"]] if practice else None
    session = new_session(exercise)
    runner = Runner("trusted-local", allow_trusted=True) if practice else None
    rows = []
    if practice:
        # Only the bundled reviewed starter/harness is executed, never fixture-supplied code.
        predict(session, exercise, runner, model, case["prediction"], 5, case["explanation"])
        rows.append({"learner": "Initial prediction: " + case["prediction"],
                     "replies": session["messages"][1:], "execution": session["runs"],
                     "code": session["code"], "goal": exercise.spec,
                     "usable_live_reply": session["messages"][-1]["source"].startswith("Gemma")})
    else:
        update_problem(session, case.get("code", ""), case.get("goal", ""),
                       case.get("reported_output", ""), case.get("language", "Python"))
    for turn in case["turns"]:
        if not practice and ("code" in turn or "reported_output" in turn):
            update_problem(session, turn.get("code", session["code"]), session["goal"],
                           turn.get("reported_output", session["reported_output"]), session["language"])
        before = len(session["messages"])
        guide(session, exercise, runner, model, turn["message"])
        rows.append({"learner": turn["message"], "code_hash": session["code_hash"],
                     "code": session["code"], "goal": session.get("goal") if not practice else exercise.spec,
                     "reported_output": session.get("reported_output", ""),
                     "replies": session["messages"][before + 1:],
                     "usable_live_reply": session["messages"][-1]["source"].startswith("Gemma")})
    return {"id": case["id"], "title": case["title"], "mode": case["mode"],
            "language": session.get("language", "Python"),
            "requested_model": model.model, "rubric": case["rubric"],
            "human_review": {"status": "not_scored", "scores": None, "notes": ""},
            "turns": rows, "events": session["events"],
            "accepted_model_replies": session["model_calls"],
            "model_requests": session.get("model_requests", 0),
            "tutor_notes": session.get("tutor_notes", [])}


def main():
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case", default=None, help="Case ID; default is aliases")
    group.add_argument("--all", action="store_true", help="Explicitly run every conversation")
    group.add_argument("--list", action="store_true", help="List cases without model calls")
    parser.add_argument("--model", default="gemma-4-26b-a4b-it",
                        choices=["gemma-4-26b-a4b-it", "gemma-4-31b-it"])
    parser.add_argument("--output", type=Path, default=Path("eval_results/tutor-review.json"))
    args = parser.parse_args()
    cases = json.loads(CASES.read_text())
    if args.list:
        for case in cases:
            events = len(case["turns"]) + (case["mode"] == "practice")
            print(f"{case['id']}: {case['title']} ({events} events, at most {events * 2} model requests)")
        return 0
    selected = cases if args.all else [case for case in cases if case["id"] == (args.case or "aliases")]
    if not selected:
        parser.error("Unknown case ID; use --list")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or getpass.getpass("Google AI Studio API key (hidden; not saved): ")
    if not key:
        parser.error("An API key is required")
    model = Gemma(key=key, model=args.model)
    reports = []
    print("Live evaluation: generated replies will be printed. Review the rubric manually.", flush=True)
    for case in selected:
        print(f"\nRunning {case['id']}…", flush=True)
        report = run_case(case, model)
        reports.append(report)
        for turn in report["turns"]:
            print("Learner:", turn["learner"], flush=True)
            for response in turn["replies"]:
                print(response["source"] + ":", response["text"], flush=True)
        print("Rubric:", " | ".join(report["rubric"]), flush=True)
    output = {"teaching_quality": "not_scored; requires human review", "conversations": reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print("\nSaved review transcript:", args.output, flush=True)
    return 0 if all(turn["usable_live_reply"] for r in reports for turn in r["turns"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
