# Validation record

Built 11 October 2026 for the Ducktoberfest prototype. This record separates executed checks
from implementation that still needs a real environment trial.

## Executed here

- Python 3.12 on Linux, Streamlit 1.65.0.
- `python -m unittest discover -s tests -v`: **21 tests passed** after the response-handling update.
- Real child-process execution of all three original prediction examples and all fifteen
  checks against the reviewed reference solutions.
- The basket's `if not items` partial correction fails the supplied-empty-list check.
- The full correction passes the five basket checks; editing afterward removes the current
  pass verdict. Stale evidence is excluded from current-code model context.
- Confidence, learner explanation, recent replies and real output reach the model request.
- A test-only model selects the challenge and receives the observed result. This tests
  orchestration, not Gemma's intelligence or tutoring quality.
- Invalid model actions, unknown test IDs, invented evidence IDs and some explicit spoilers
  are rejected. Semantic spoiler prevention is not guaranteed.
- Timeouts, syntax errors, bounded print output, failed runner opt-in and model outages do
  not fabricate a successful run or live model response.
- The local child environment omits a sentinel API key.
- Notebook updates produce one record per session; solution viewing is recorded.
- Streamlit AppTest completes prediction, partial correction, complete correction, notebook
  creation and revision invalidation without exceptions. An ordinary rerun adds no runs.
- The Streamlit server started successfully on localhost.

## Still to verify on the demonstration machine

1. Live validation of the response-handling update. There is no API key in this workspace.
   The user has now shown one successful 26B preflight on the Mac (3.43 seconds, useful
   non-spoiling question), followed by an app response that did not parse as JSON.
2. Non-spoiling, useful multi-turn tutoring, confidence-sensitive responses, account quota,
   and latency. There are no invented performance measurements.
3. A complete session on the demonstration Mac. The user has now confirmed successful
   local execution of the basket preflight and the largest-number example on macOS.
4. Docker image/startup/cleanup on an installed Docker runtime, if you choose that route.
   Docker is unavailable in this workspace.
5. Ollama connectivity and local model performance, if you choose local inference.
6. Visual browser inspection. Playwright could not download a valid browser archive here;
   interaction-level Streamlit checks passed, but no screenshot-based layout claim is made.

## Deliberate prototype limits

Trusted-local execution is opt-in and is not a security sandbox. Keep it on localhost and
use only trusted code. Even the optional Docker runner is a prototype, not a hardened online
judge. Tests are finite and can be gamed by hostile submissions. The project makes claims
only about the listed checks for a source revision, never general correctness or mastery.

One local learner, three prepared exercises, no accounts, and no public hosting are included.
Notebook records persist; restoring a saved record into an active chat is not implemented.
The API is called only on explicit user actions. Static fallback hints are always labeled.

## Next concrete milestone

Apply the response-handling update, restart Streamlit, select 26B, and repeat the
largest-number prediction that previously produced invalid JSON. The raw failed response
was not retained, so its exact formatting defect is not known. If the updated response is
still rejected, inspect the safe event diagnostics: category, parser position, output size,
finish reason, and whether the single repair was attempted. No API keys or raw rejected
answers are recorded in those diagnostics.

Eight additional regression tests cover whole-response JSON fences/BOM, rejecting prose
and truncated objects, one bounded repair with preserved evidence, truthful error labels,
no format retry on connectivity errors, sharing the two-request budget across challenge
and feedback, unchanged action validation after repair, and output-limit detection.
