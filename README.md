# DuckTutor — 0.3.0

A Gemma-powered programming tutor for Ducktoberfest. Bring your own code, goal and questions; the duck helps you understand the mechanism and find the next step, while leaving the final correction to you.

The main workspace is now **Your code**. Five reviewed Python exercises remain available under **Practice exercises**. This is an independent project inspired by rubber-duck debugging and CS50's teaching-first approach; it is not Harvard's software or a claim of equivalent tutoring quality.

## Start on your Mac

Use Python 3.11 or newer. Open Terminal in the extracted project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Stop the old Streamlit process with Ctrl+C before starting this update. Open `http://127.0.0.1:8501`. In **Connection settings**, enter your Google AI Studio key and use the default **Gemma 26B**. An existing `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable also works. Connection credentials are not written to notebooks.

Replace all files from this package, including the new `workspace_ui.py` and evaluation files. Keep your existing `data/`, working `.venv/` and local secret files. The archive excludes them. Old exercise sessions still resume.

## Your code

1. Choose a language and paste the relevant code, or ask a programming concept question without code.
2. Describe what should happen. Add an error or output you observed if useful.
3. Ask the duck a question or explain what you tried. The duck can ask a specific question, explain a concept, give a stronger hint or recap an insight.
4. Edit the code as you learn. Every next request uses the current revision. Old pasted output stays attached to its previous revision until you update it or explicitly confirm that you reproduced it.
5. Add your own learning notes or correct the duck's tentative working notes. Save, export and resume the conversation from the notebook.

The language selector supports Python, JavaScript, TypeScript, C, C++, Java, SQL and Other for discussion. This is **code analysis**: the app does not execute submissions in this workspace. Pasted output is learner-reported evidence, not a verified runtime result. It supplies no automated correctness verdict.

Model calls happen only on explicit actions. Editing code, switching workspaces and ordinary reruns do not call the model. Drafts survive switching between Your code and individual practice exercises. Empty starter workspaces do not clutter the notebook.

## How tutoring changed

- The duck can explain directly instead of ending every reply with another question. Short unrelated examples and readable paragraphs are allowed.
- Confusion should lead to a concept explanation or a more concrete clue. Correct reasoning should be acknowledged before moving forward.
- Exact or very similar repeated questions are rejected and get one bounded repair attempt; the prompt also discourages rephrasing the same question. Semantic repetition still needs live review.
- Learner-written notes and up to six tentative model interpretations provide continuity beyond the recent eight-message context window. They are not mastery assessments.
- Runtime predictions stay separate from specification requirements. A correct prediction of buggy behavior remains correct.
- Response checks allow ordinary terms such as “return value” while rejecting some complete submission rewrites, new inline replacement statements and fabricated execution claims. These are heuristics, not a guarantee against every spoiler or hallucination.

## Optional Python practice

Choose **Practice exercises**, then select basket, largest, total, closures, countdown, shallow_copy or scope_leak. Each exercise has five reviewed cases and a prepared transfer question:

**Predict → investigate → edit → check → reflect.**

Gemma receives the learner's current code, reasoning, confidence and real run evidence. It can select a reviewed test; Python executes it and determines the verdict. Passing all supplied checks verifies those cases for that code revision, not general correctness or mastery. Editing invalidates the previous pass status.

- **Offline synthesized sound effects:** Pure-Python WAV audio synthesizer (`sound_effects.py`, 0 external dependencies) with authentic rubber duck quacks, squeaks, and celebratory fanfare on predictions, hints, and verified solutions, with a sidebar toggle and interactive "Squeeze the Duck" button.

### Trusted local demo

In **Exercise execution**, choose Trusted local demo and check **I am running only code I trust**. This executes exercise code and your edits in local child processes with time/output limits and a minimal environment that excludes API keys. It is **not a security sandbox**: submitted Python still has host-user permissions. Keep the default localhost binding and run only trusted code.

### Docker

With Docker installed and running:

```bash
docker pull python:3.12-slim
python preflight.py
```

Select Docker container in Exercise execution. Each case runs with networking disabled, a non-root user, read-only filesystem, dropped capabilities and resource limits. The notebook directory and API key are not mounted into the runner. This prototype is not a hardened adversarial judge. Docker execution has not been exercised in this workspace.

## Gemma connection

Default: `gemma-4-26b-a4b-it`, with a 20-second timeout. Optional: `gemma-4-31b-it`, with a 60-second timeout. Connection tests show the last validated reply, latency and returned model when reported. A successful test does not guarantee the next request or teaching quality.

HTTP failures and invalid responses are displayed honestly. Rejected answers are not shown; a labeled local hint is used if recovery fails. Each learner action has at most two model requests, including repair and optional exercise-test feedback. A failed 31B connection test offers explicit retry with 26B.

Hosted inference sends the supplied code, goals, notes and conversation context to Google. The notebook stays in the local `data/` directory. Do not paste secrets into source or chat. A local Ollama adapter remains available for an already installed model; no local GPU is required for hosted inference.

Exercise preflight:

```bash
python preflight.py --trusted-local --model gemma-4-26b-a4b-it
```

For request diagnostics, see `diagnose_gemma_request.py`. For actual conversation review, use the evaluation runner below.

## Validate behavior and evaluate teaching

```bash
python -m unittest discover -s tests -v
python evaluate_tutor.py --list
python evaluate_tutor.py --case aliases --model gemma-4-26b-a4b-it
```

**56 automated tests passed** across exercise execution, own-code and practice UI flows, saved sessions, audio effects, current-code context, reported-output attribution, explanatory replies, bounded repetition repair and selected anti-spoiler/error checks. Mocked responses do not establish model teaching quality.

The live evaluation runner includes six conversations about aliasing, print/return, loop boundaries, JavaScript filtering, solution requests and correct predictions of buggy behavior. It prompts privately for the key, prints validated replies and saves a transcript with an **unscored human-review rubric**. `--all` explicitly runs the full set. Reports go to ignored `eval_results/` by default.

See [EVALUATION.md](EVALUATION.md), [VALIDATION.md](VALIDATION.md) and [DEMO.md](DEMO.md). No live call to the redesigned tutor was made in this workspace; it has no API key. The new layout still needs visual review on the Mac.

## Notebook and deployment

Notebooks persist code, conversation, goals, reported output, learning notes and exercise outcomes as atomic JSON records. They can be resumed and exported. `DATA_DIR` chooses another location. The notebook UI lists every record in that directory; there is no per-user authentication or authorization.

Run the immediate demonstration locally using hosted 26B. Public deployment still needs notebook ownership/access controls; public exercise execution also needs separate isolation. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Source layout

- `app.py`: application shell, connection settings, workspace switcher, practice flow and notebook.
- `workspace_ui.py`: own-code workspace, draft restoration and chat rendering.
- `sound_effects.py`: pure-Python offline WAV audio synthesizer and pedagogical audio triggers.
- `core.py`: sessions, revisions, model-action budgets, learning notes and persistence.
- `tutor.py`: Gemma transport, context construction and response validation.
- `runner.py`, `worker.py`: reviewed Python exercise execution.
- `exercises.py`: 7-exercise catalog (35 test cases) and prepared transfer questions.
- `evaluate_tutor.py`, `conversation_evals.json`: live conversation review.
- `tests/`: 56 automated behavior and interface checks.

Python's standard library implements the core; Streamlit is the only direct package dependency. Application code is MIT-licensed; Gemma and dependencies retain their own licenses.

Repository: https://github.com/Ducktoberfest/team-neuralforge

References: [Gemma API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api), [CS50 Duck](https://cs50.readthedocs.io/cs50.ai/), [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
