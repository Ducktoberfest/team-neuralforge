# Validation record — 0.2.3

11 October 2026. Executed checks are distinguished from observations supplied by the user.

## Executed for this update

- Python 3.12.14 on Linux, Streamlit 1.65.0.
- Version 0.2.3 full suite: `python -m unittest discover -s tests -v` — **35 tests passed**.
- Real child-process execution of all five starter prediction examples and all 25 reviewed checks against their reference solutions.
- Learning transitions, revision invalidation, session hydration, notebook updates and transfer questions. The partial basket correction fails the supplied-empty-list check; the reference solution passes its five checks. Editing afterward invalidates verification.
- Evidence, learner reasoning, confidence, recent replies and current code reach model context. Reference solutions are excluded.
- Response parsing, bounded repair, allowed actions/cases/evidence, some explicit spoilers, and a maximum of two model calls per learner action.
- Timeout, syntax-error and output-limit handling; child environments omit a sentinel API key.
- Mocked transport verifies default timeouts (31B: 60 seconds, 26B: 20 seconds), explicit overrides and returned-model metadata. Credentials do not enter notebook events.
- Streamlit AppTest covers prediction, corrections, revision invalidation, notebook creation, resumption, transfer checks and chat recovery.
- New UI regression: a failed sidebar connection test remains visible through a rerun; switching to 26B makes an actual second request and displays its result. Ordinary reruns make no extra request; changing model settings hides stale success.
- New UI regression: restoring an already-rendered editor replaces stale text with saved code while preserving the saved revision's verification.
- New context regression: correct, incorrect and uncertain runtime predictions remain separate from a failed exercise requirement. Model evidence labels specification values as `required_result`; after code changes, the original prediction retains its recorded revision and stale runs are excluded from current evidence.

Mocked model tests verify application behavior, not live tutoring quality or availability. AppTest verifies interactions and state, not rendered visual appearance. The user’s Mac screenshot confirms that the 0.2.1 banner overlaps the toolbar; 0.2.2 removes the top-padding override and restores Streamlit’s own header clearance. The revised browser layout still needs a Mac check.

## Live observations supplied by the user on the Mac

- The 26B tutor preflight completed in **8.12 seconds**, returned `ask_question`, used the actual apple/banana evidence, and did not state the correction.
- A staged 31B diagnostic accepted the full current app payload, including system instructions and JSON mode, in **29.2 seconds**. Other configured stages succeeded in roughly 37–50 seconds.
- Other requests returned HTTP 500 and 503. These observations show that 31B can work with the app payload, but do not establish sustained reliability or a controlled model benchmark.

The user also supplied a model question that conflated a correct runtime prediction with a failed requirement. Version 0.2.3 clarifies model context and policy in response. This prompt change cannot guarantee every generated question is sensible. No live API request was made in this workspace: no API key was provided here.

## Still to verify on the demonstration machine

1. Restart the updated app and visually inspect dark-theme widgets, menus, alerts, editor and narrow-window layout. A browser connected to this workspace's local Streamlit server was unavailable; no screenshot-based layout claim is made.
2. Complete a live multi-turn session with 26B. Review useful questions, anti-spoiler behavior, latency and account quota.
3. Repeat 31B preflight if demonstrating it; a longer timeout cannot remedy provider 500/503 responses.
4. Exercise Docker startup, isolation and cleanup if using Docker. Docker is unavailable in this workspace.
5. Verify local Ollama only if using local inference.

## Prototype limits

Five prepared exercises and finite checks do not prove general correctness or mastery. Regex validation cannot guarantee semantic spoiler prevention. Prepared offline hints remain labeled.

Trusted-local execution runs with host-user permissions; process limits are not a security sandbox. Keep it on localhost with trusted code. The Docker runner is a prototype, not a hardened adversarial judge, and submitted code shares a process with its test harness.

Notebook records persist and can be resumed. All records in one notebook directory are visible to the app; per-user authentication and notebook authorization are absent. Public hosting is not implemented. See DEPLOYMENT.md for the next deployment work.
