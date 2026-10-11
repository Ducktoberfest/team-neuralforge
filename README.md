# DuckTutor

A Gemma-powered debugging tutor for Ducktoberfest. One integrated Python application:

**Predict with confidence → execute → investigate → edit → challenge → check → remember.**

Gemma receives the learner's current code, answers, confidence and actual execution evidence.
It asks a focused question or selects a reviewed test case. Python executes the case;
the model never decides a pass verdict. Results refer to the checked cases and the exact
code revision. Changing the code invalidates the previous success.

This is an independent project inspired by the teaching-first rubber-duck concept and
CS50's Duck. It is not affiliated with Harvard or a release of Harvard's software.
DuckTutor is a working title.

## Start on your Mac

Use Python 3.11 or newer (your Python 3.12 installation is suitable).
Unzip the project, open Terminal in the `duck_tutor` directory, and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python preflight.py --trusted-local
```

The preflight asks for your Google AI Studio key without echoing or saving it. It runs the
bundled basket example, sends its **real observed output** plus a confidently wrong prediction
to Gemma, and checks the returned action. Read the question: a useful response should examine
the assumption without giving the correction. A valid JSON response alone does not prove
good teaching. The command exits with status 1 for execution failure and 2 for model failure.

Then launch the application:

```bash
python -m streamlit run app.py
```

Open **http://127.0.0.1:8501**. In Connection settings, enter your API key again (the preflight
did not save it). Alternatively, the app reads an existing `GEMINI_API_KEY` or `GOOGLE_API_KEY`
environment variable. Never commit keys or paste them into the notebook.

For a Docker-free personal demo, select **Trusted local demo** and check
**I am running only code I trust**. Submit a prediction to open the editor.

## Execution choices

### Trusted local demo

This option runs the bundled exercise and your own trusted edits in separate child processes.
It uses a temporary working directory, a minimal environment that excludes API keys, a wall
timeout, process-group cleanup on macOS/Linux, and output limits. Those are operational
controls, **not a security sandbox**. Submitted Python can still access host files, network,
and other resources under your user account. Do not run unfamiliar pasted code, invite
untrusted users, or expose this mode as an internet service. The Streamlit config binds the
app to `127.0.0.1`; leave that binding in place.

The trusted runner is tested on Linux here. The macOS resource-limit path uses the same
POSIX process APIs but still needs a run on the actual demonstration Mac. Windows is not
the validated target for this runner.

### Docker

With an installed and running Docker-compatible runtime, prepare the image once:

```bash
docker pull python:3.12-slim
python preflight.py
```

Select **Docker container** in the interface. Each case uses a separate container with
network disabled, a non-root user, a read-only filesystem, dropped capabilities, resource
limits, and only the temporary harness mounted read-only. The API key and notebook directory
are not mounted or forwarded. `--pull=never` prevents a surprise image download during a run.

Docker is optional and its runtime path has **not been exercised in this workspace**, where
Docker is unavailable. Run the preflight with Docker on the actual demo machine before
depending on it. This prototype is not a hardened adversarial online judge: malicious code
could interfere with an in-process test harness even inside a container.

## Gemma connection

Default: `gemma-4-26b-a4b-it`, through Google's Gemini API (configured as default in `app.py` and `preflight.py`). Alternate: `gemma-4-31b-it`.
Hosted access still uses Gemma; hosted inference sends the supplied code and conversation
context to Google. The notebook itself stays in the local `data` directory.

```bash
python preflight.py --trusted-local --model gemma-4-26b-a4b-it
```

### AI Robustness & Context Management
- **Structured JSON Mode:** Gemma requests specify `"responseMimeType": "application/json"` on Google AI Studio where supported, with robust markdown fence and BOM stripping as a reliable fallback.
- **Context Window Pruning:** `tutor.py` caps conversational history to the latest 3–4 dialogue turns (up to 8 messages) and active revision evidence to 6 items. Base exercise requirements, the learner's initial prediction, and current source code are always preserved.
- **Graceful Error Recovery:** HTTP 500, 502, 503, 504 and timeout conditions from hosted endpoints are caught cleanly and mapped to the badge **"Exercise hint · live Gemma unavailable"** (suggesting `gemma-4-26b-a4b-it`), preventing unhandled exceptions or state loss.
- **Self-Repair Loop:** Bounded single repair request if a response is malformed, with a hard ceiling of 2 model requests per learner action.

An Ollama adapter is included for an already running local installation:

```bash
python preflight.py --trusted-local --provider ollama --model YOUR_INSTALLED_GEMMA_TAG
```

Choose Local Ollama in the UI and enter the exact installed tag. A local deployment is not
necessary for the hosted demo.

If the model fails or is offline, real execution continues and guidance is visibly labeled
**Exercise hint · live Gemma unavailable**. No prerecorded answer is labeled as live AI.

## What's implemented

- **Five curated Python exercises** spanning foundational traps:
  1. `basket` — Mutable default arguments (`items=[]`).
  2. `largest` — Initial state assumptions & all-negative lists (`best = 0`).
  3. `total` — Off-by-one loop boundaries (`range(len(numbers) - 1)`).
  4. `closures` — Late-binding loop variables in lambdas / closures.
  5. `countdown` — Base case boundary omission in recursion.
- Exactly 5 reviewed test cases per exercise (25 execution cases total), distinguishing ordinary checks from trap probes.
- Confidence-sensitive model context and a bounded JSON action protocol.
- Model-selected challenges and real output fed back to Gemma; at most two calls per event.
- **Session hydration & resumption:** Saved sessions from `data/*.json` can be restored into active memory via the sidebar or "My Notebook" tab.
- **Strict revision tracking:** SHA-256 hash invalidates pass status immediately if learner code changes by even a single character (`verified_hash = None`).
- Anti-spoiler regex verification with exercise-specific forbidden patterns.
- Automatic local notebook upserts, historical evidence timeline, and JSON export.
- Optional conceptual transfer reflection questions.
- Execution event panel showing exact selected actions and child process outputs.

The exercise bank gives the agent safe, interpretable action choices. It does not script the
live conversation. Gemma's next question receives the learner's actual recent replies and
current source code. Generated text is still fallible; inspect the displayed execution
panel as the authority for outputs and pass results. Passing a finite suite does not prove
general correctness, full requirement coverage, or learner mastery.

## Notebook and privacy

`data/` contains one JSON record per session, atomically replaced after actions. Records
contain learner code, messages, confidence, observed runs, attempted corrections, whether
the solution was viewed, and any follow-up response. Credentials are never saved.

Notebook history survives app restarts. DuckTutor supports full interactive session hydration:
learners can select and resume any previously saved session from disk (`data/<session_id>.json`)
into an editable workspace directly from the sidebar or the **My Notebook** tab. Resuming
preserves full exercise context, evidence history, and dialogue turns while enforcing revision
hash verification.

Use `DATA_DIR` to choose another notebook directory. Keep notebook data out of the public
repository. `.gitignore` covers `data/`, virtual environments, secret files, and caches.

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The test suite checks real Python results for all 5 prepared solutions, starter traps,
state transitions, hash invalidation, notebook upserts, session hydration, timeout/output limits,
secret-free child environments, context window pruning, HTTP 500/timeout error recovery,
invalid model actions, and the interactive Streamlit UI flow.

Recorded validation: **27 automated tests passed on Python 3.14 (macOS) and Python 3.12 (Linux) with Streamlit 1.65.0**.
See `VALIDATION.md` for tested boundaries. See `DEMO.md` for a four-minute walkthrough.

## Source layout

This is one process and one launch command. Files are ordinary internal modules, not services
or independently developed components: `app.py` is the UI, `core.py` manages the session,
`tutor.py` handles model decisions, `runner.py` and `worker.py` execute code, and `exercises.py`
holds the reviewed material. No database, RAG, agent framework, fine-tuning or frontend build
is needed. Core logic and preflight use Python's standard library; Streamlit is the direct package dependency.

Application code is MIT-licensed; Gemma and third-party dependencies retain their respective
licenses. The project is maintained at `https://github.com/Ducktoberfest/team-neuralforge`.

## References

- [Hosted Gemma API documentation](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [CS50.ai documentation](https://cs50.readthedocs.io/cs50.ai/)
- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)

Documentation checked on 11 October 2026. Model availability in a particular account must
be established by a successful request.
