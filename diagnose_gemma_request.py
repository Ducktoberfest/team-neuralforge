#!/usr/bin/env python3
"""Compare progressively richer Gemma requests using DuckTutor's real context.

Place this file beside app.py, core.py, exercises.py, runner.py and tutor.py.
Run: python3 diagnose_gemma_request.py
The key is prompted privately, held in memory, and never saved.
"""

import argparse
import copy
import getpass
import http.client
import json
import os
import re
import time
from urllib import error, request


def payloads(policy, context):
    bare = {"contents": [{"parts": [{"text": "Reply with exactly READY."}]}]}
    settings = {"maxOutputTokens": 1200,
                "thinkingConfig": {"thinkingLevel": "minimal"}}
    configured = {**copy.deepcopy(bare), "generationConfig": copy.deepcopy(settings)}
    evidence = {"contents": [{"role": "user", "parts": [
        {"text": json.dumps(context, ensure_ascii=False)}]}],
        "generationConfig": copy.deepcopy(settings)}
    system = {**copy.deepcopy(evidence),
              "systemInstruction": {"parts": [{"text": policy}]}}
    full = copy.deepcopy(system)
    full["generationConfig"]["responseMimeType"] = "application/json"
    # Compare system-instruction transport with instructions in the user prompt.
    inline = copy.deepcopy(full)
    inline.pop("systemInstruction")
    inline["contents"][0]["parts"][0]["text"] = (
        policy + "\n\nTask data (JSON):\n" + json.dumps(context, ensure_ascii=False))
    return [
        ("A: minimal READY prompt", bare, False),
        ("B: READY + output limit + thinking disabled", configured, False),
        ("C: actual tutor context + those settings", evidence, False),
        ("D: C + systemInstruction (no JSON mode)", system, True),
        ("E: D + JSON mode (exact current app payload)", full, True),
        ("F: E with policy in user text instead of systemInstruction", inline, True),
    ]


def scrub(value, key):
    text = str(value).replace(key, "[REDACTED]")
    return re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED]", text)[:600]


def probe(model, payload, timeout, key, context, validate, parse_decision):
    started = time.monotonic()
    req = request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            print("  HTTP 200; response exceeded 256 KiB", flush=True)
            return
        body = json.loads(raw)
        candidates = body.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        parts = candidate.get("content", {}).get("parts", [])
        visible = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        print("  HTTP 200", flush=True)
        print("  Returned model:", body.get("modelVersion", "not provided"), flush=True)
        print("  Finish reason:", candidate.get("finishReason", "not provided"), flush=True)
        print("  Visible characters:", len(visible), flush=True)
        if validate:
            try:
                if candidate.get("finishReason") in {"MAX_TOKENS", "length"}:
                    raise ValueError("Reply was cut off at the output limit")
                if not visible.strip():
                    raise ValueError("No visible answer returned")
                decision = parse_decision(visible, context)
                print("  Tutor validation: accepted; action =", decision["action"], flush=True)
            except Exception as exc:
                print("  Tutor validation: rejected;", scrub(exc, key), flush=True)
        # Do not print raw model answers: they might reveal an exercise solution.
    except error.HTTPError as exc:
        print("  HTTP", exc.code, flush=True)
        try:
            provider_error = json.loads(exc.read(8192)).get("error", {})
            print("  Provider status:", scrub(provider_error.get("status", "not provided"), key), flush=True)
            print("  Provider message:", scrub(provider_error.get("message", "not provided"), key), flush=True)
        except (ValueError, OSError, AttributeError):
            print("  No readable provider error details", flush=True)
    except (error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        print("  Connection failure:", type(exc).__name__, flush=True)
    except (ValueError, TypeError, AttributeError) as exc:
        print("  Unreadable response:", type(exc).__name__, flush=True)
    finally:
        print(f"  Elapsed: {time.monotonic() - started:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("gemma-4-31b-it", "gemma-4-26b-a4b-it"),
                        default="gemma-4-31b-it")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--stages", default="ABCDEF",
                        help="Run selected stages, e.g. --stages DE to repeat a comparison")
    args = parser.parse_args()
    stages = args.stages.upper()
    if not stages or any(s not in "ABCDEF" for s in stages):
        parser.error("--stages must contain letters from ABCDEF")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        from core import new_session
        from exercises import BASKET
        from runner import Runner
        from tutor import POLICY, context_for, parse_decision
    except ImportError:
        parser.error("Place this script inside the DuckTutor project folder beside tutor.py.")

    # Execute only the bundled, reviewed exercise. Do not read learner notebooks.
    observed = Runner("trusted-local", allow_trusted=True).run(BASKET, BASKET.starter, "prediction")
    if observed["status"] != "completed":
        print("Runner failed:", observed.get("error", observed["status"]))
        return 1
    session = new_session(BASKET)
    session.update(prediction='["banana"]', confidence=5,
                   explanation="I think each omitted basket is a new list.",
                   initial_observation=observed["actual"], prediction_matches_execution=False,
                   runs=[observed])
    context = context_for(session, BASKET, "prediction_observed", ["ask_question"], [])
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
           or getpass.getpass("Google AI Studio API key (hidden; not saved): "))
    if not key:
        parser.error("An API key is required")
    print("Runner: completed; observed:", json.dumps(observed["actual"]), flush=True)
    print("Model:", args.model, flush=True)
    print("No automatic retries; generated hints are not displayed.\n", flush=True)
    for label, payload, validate in payloads(POLICY, context):
        if label[0] in stages:
            print(label, flush=True)
            probe(args.model, payload, args.timeout, key, context, validate, parse_decision)
            print(flush=True)
    print("A failed stage suggests a configuration to investigate; one run alone cannot rule out intermittent failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
