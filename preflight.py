"""Test an actual execution-to-Gemma round trip without launching the UI."""
import argparse
import getpass
import json
import os
import sys

from core import new_session
from exercises import BASKET
from runner import Runner
from tutor import Gemma, ModelError, context_for, parse_decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-local", action="store_true", help="Run the bundled reviewed example in a local child process (not a sandbox).")
    parser.add_argument("--provider", choices=["google", "ollama"], default="google")
    parser.add_argument("--model", default="gemma-4-26b-a4b-it",
                        help="Gemma model to use (default: gemma-4-26b-a4b-it)")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.provider == "google" and not key:
        key = getpass.getpass("Google AI Studio API key (hidden; not saved): ")
    runner = Runner("trusted-local" if args.trusted_local else "docker", allow_trusted=args.trusted_local)
    observed = runner.run(BASKET, BASKET.starter, "prediction")
    print("Runner:", observed["status"])
    if observed["status"] != "completed":
        print(observed.get("error", "Execution did not complete."))
        return 1
    print("Observed second call:", json.dumps(observed["actual"]))
    session = new_session(BASKET)
    session.update(prediction='["banana"]', confidence=5,
                   explanation="I think each omitted basket is a new list.",
                   initial_observation=observed["actual"], prediction_matches_execution=False,
                   runs=[observed])
    context = context_for(session, BASKET, "prediction_observed", ["ask_question"], [])
    if args.provider == "google" and "31b" in args.model.lower():
        print("Note: Google AI Studio currently experiences intermittent HTTP 500 errors on gemma-4-31b-it. If the request fails, use gemma-4-26b-a4b-it.")
    model = Gemma(key=key, model=args.model, provider=args.provider, base_url=args.ollama_url)
    try:
        raw, elapsed = model.decide(context)
        decision = parse_decision(raw, context)
    except ModelError as exc:
        print("Gemma preflight failed:", str(exc))
        return 2
    print(f"Live {args.model} response: {elapsed / 1000:.2f}s")
    print(decision["message"])
    print("Valid action:", decision["action"])
    print("Review manually: did it respond to the evidence, ask a useful question, and avoid the fix?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
