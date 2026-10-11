# Validation record — 0.3.0

11 October 2026. This update makes own-code tutoring the default and retains optional reviewed Python practice.

## Executed here

- Linux, Python 3.12.14, Streamlit 1.65.0.
- `python -m unittest discover -s tests -v`: **50 tests passed**.
- Real execution of five starter prediction examples and all 25 reviewed solution checks; partial correction failure, revision invalidation, output/timeout limits and secret-free runner environment.
- Existing exercise UI flow, notebook upserts, saved-session hydration, transfer checks, 31B recovery and persistent connection-test results.
- Own-code UI: default workspace, concept questions without a code submission or execution opt-in, explicit-action-only calls, draft preservation across workspace switches, notebook resumption and reported-output confirmation after edits.
- Own-code context: no fabricated execution evidence/verdict, current source and language, old reported output retained with its actual revision, learner-written notes and tentative model notes preserved across resume.
- Explanatory replies and short unrelated examples are accepted. Ordinary prose about a return value is no longer blocked. Selected full rewrites and new inline replacement statements are rejected while existing source can be discussed.
- Response heuristics cover Python, JavaScript, C++ and SQL problem names in examples, some fabricated execution claims, and exact/near-exact repeated questions with a bounded repair into a new explanation.
- The evaluation harness runs all six fixtures against a test model, preserves transcript/protocol status, executes no own-code submissions, and leaves human teaching scores unassigned.
- `python evaluate_tutor.py --list` lists all six conversations without model calls.

Tests with test models validate orchestration and response checks. They do not measure Gemma's teaching ability. No rejected raw model answers are retained, and model credentials are not recorded in events.

## Live observations from earlier versions, supplied by the user

The Mac 26B preflight returned a useful question in 8.12 seconds. Later session records contained four accepted replies around 2.6–2.9 seconds followed by two invalid decision shapes. A screenshot of 0.2.3 showed repetitive questions despite correct prediction handling. That motivated this redesign.

The full 31B payload succeeded during staged diagnostics in 29.2 seconds, with other successes around 37–50 seconds and separate HTTP 500/503 failures. These show compatibility in that run, not sustained reliability or comparative tutoring quality.

Those observations predate the redesigned policy. **No live API call for 0.3.0 was made here; no key was available.**

## Still to verify on the Mac

1. Restart with the full package and visually inspect Your code, chat, sidebar, notebook and narrow-window layout. AppTest verifies interaction/state, not screenshot appearance. Native top clearance is preserved after the earlier toolbar overlap.
2. Run the live conversation evaluation and score its rubric manually, then try unscripted multi-turn conversations. Check accurate explanations, progression, correct predictions and resistance to supplying complete solutions.
3. Verify optional Docker execution and cleanup on the actual runtime if demonstrating it. Docker is unavailable here.
4. Verify Ollama only if using local inference. Repeat 31B requests only if demonstrating the optional model.

## Boundaries

Own-code sessions discuss pasted code and learner-reported output; they do not execute code or verify correctness. Model interpretations of learning are tentative and can be corrected by the learner. Keyword/repetition/example guards cannot guarantee semantic safety or teaching quality.

Practice checks verify a finite reviewed suite for one revision. Trusted-local execution has host-user permissions and is not a security sandbox. Docker isolation remains a prototype, not a hardened adversarial judge.

Notebooks are stored locally and all records in one directory are visible to the app. Per-user authentication/authorization and public hosting are absent. See DEPLOYMENT.md before exposing the service.
