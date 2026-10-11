# DuckTutor — Project Status & Roadmap

> **Team NeuralForge** · *Ducktoberfest 2026*  
> **Repository:** `https://github.com/Ducktoberfest/team-neuralforge`  
> **Status Date:** October 2026  
> **Version:** 0.1.0-prototype  

---

## 1. Overall Idea & Philosophy

### 1.1 The Core Problem
Modern AI coding assistants (GitHub Copilot, ChatGPT, Claude) optimize for *immediate code generation*. When a learner encounters a bug, traditional assistants provide the corrected patch instantly. While efficient for professional development, this **short-circuits learning**: the student never diagnoses the faulty assumption that caused the bug, leading to superficial comprehension and recurring errors.

### 1.2 The DuckTutor Solution
DuckTutor is an independent, Socratic, evidence-based debugging tutor inspired by the rubber-duck debugging methodology and Harvard CS50’s Duck tutor. Built specifically for **Ducktoberfest**, it guides learners through active problem discovery rather than handing them answers.

The core learning loop is:
```
Predict with Confidence ➔ Execute ➔ Investigate Evidence ➔ Edit Code ➔ Challenge ➔ Verify ➔ Remember
```

### 1.3 Key Architectural Principles
1. **Model Never Determines Verdicts:** Large Language Models hallucinate. In DuckTutor, Gemma **never** marks a test as passed or failed, and **never** invents test cases. All code execution and pass/fail evaluations are performed strictly by the Python runtime.
2. **Pedagogical Guidance vs. Execution Authority:**
   - **Gemma (The Duck):** Analyzes the learner’s code, current prediction, confidence level, and observed runtime evidence. It asks focused, Socratic questions (25–60 words) or selects an existing test case from a pre-reviewed catalog.
   - **Python Runtime (The Judge):** Executes the student code in an isolated child process or Docker container against rigorous test assertions. Real standard output and evaluation dictionaries are returned as concrete evidence.
3. **Confidence-Aware Tutoring:** Gemma's prompting adapts based on learner confidence:
   - *High confidence + wrong prediction:* Question the foundational assumption that caused the blind spot.
   - *Low confidence / unsure:* Guide attention toward small, concrete observations.
   - *Accurate prediction of buggy behavior:* Acknowledge correct observation without assuming false misconceptions.
4. **Strict Anti-Spoiler Policy:** Prompting and regex validation filter out direct code solutions, function definitions, replacement statements, or unjustified praise ("mastered", "proven correct"). Learners must use an explicit "Show explanation and solution" button if they cannot solve the problem.
5. **Revision-Specific Verification:** Every code change computes a new SHA-256 revision hash (`code_hash`). Changing even a single whitespace invalidates any previous pass verdict (`verified_hash = None`), preventing stale success claims.
6. **Automatic Private Notebook:** Every session is saved locally as an atomic JSON record (`data/<session_id>.json`). The notebook preserves predictions, confidence ratings, attempts, requested hints, execution runs, and reflection responses without logging credentials.

---

## 2. Current Architecture & Codebase Map

| File | Purpose | Key Responsibilities |
| :--- | :--- | :--- |
| [`app.py`](app.py) | **Streamlit UI** | Main user interface: sidebar configuration (Gemma provider, API key, execution mode), 4-stage learning tab (Predict, Investigate, Check, Reflect), and the persistent "My Notebook" tab. |
| [`core.py`](core.py) | **Session & State Machine** | Orchestrates session states (`predict` → `guide` → `reflect`), code synchronization, revision hash invalidation, request budget management (max 2 per action), fallback guidance when Gemma is unavailable, and atomic notebook persistence. |
| [`tutor.py`](tutor.py) | **Model Interface & Guardrails** | Transports requests to Hosted Gemma (`gemma-4-26b-a4b-it`, `gemma-4-31b-it`) via Google AI Studio API or local Ollama; enforces strict JSON protocol; validates allowed actions, test IDs, and evidence IDs; performs 1-step self-repair for malformed JSON; filters spoilers. |
| [`runner.py`](runner.py) | **Execution Runner** | Manages code execution under two modes: `trusted-local` (child process with clean environment, resource bounds, process-group termination, 64 KiB stdout cap) and `docker` (container with `--network=none`, `--read-only`, dropped capabilities, memory/CPU caps). |
| [`worker.py`](worker.py) | **Child Process Harness** | Safe execution script executed inside the runner. Captures `stdout`/`stderr` up to 4 KiB, applies CPU and file size `rlimit`s, compiles and executes user code against the specified case script. |
| [`exercises.py`](exercises.py) | **Exercise & Case Catalog** | Defines curated exercises with specification, starter code, prediction choices, curated test cases (5 checks each), reference solutions, explanations, and tiered hint templates. |
| [`preflight.py`](preflight.py) | **CLI Preflight Diagnostic** | Terminal script to test execution and live Gemma round-trip before starting the Streamlit application. |
| [`tests/`](tests/) | **Automated Test Suite** | 21 test cases across `test_learning.py` (learning lifecycle, invalidation, security), `test_responses.py` (JSON parsing, BOM, markdown fence, repair loops), and `test_ui.py` (Streamlit AppTest automation). |

---

## 3. What Is Already Done

### 3.1 Learning Workflow & State Management
- [x] **4-Stage Learning Lifecycle:** `predict` ➔ `guide` ➔ `check` ➔ `reflect`.
- [x] **Revision Tracking:** SHA-256 code hashing invalidates pass status immediately upon code edit.
- [x] **Confidence Assessment:** 1–5 confidence slider + textual rationale captured before execution.
- [x] **Selective Challenge Execution:** Gemma selects a targeted test case from the reviewed catalog to challenge incomplete student patches.
- [x] **Full Suite Verification:** Once the initial check and challenge pass, all 5 cases are run to verify the revision.
- [x] **Progressive Hinting:** Hint levels 0 (observation probe), 1 (conceptual hint), and 2 (location hint).
- [x] **Solution Reveal Drawer:** Explicit button to view the reference solution; records that the solution was viewed in the notebook.
- [x] **Transfer Reflection:** Follow-up conceptual question (e.g., shared reference mutation) after completing the basket exercise.

### 3.2 Gemma AI Model Integration & Robustness
- [x] **Multi-Provider Support:**
  - Google AI Studio (Hosted Gemma: `gemma-4-26b-a4b-it` and `gemma-4-31b-it`).
  - Local Ollama (`gemma4:12b-it-q4_K_M` or custom tag).
- [x] **Strict Action Protocol:** Gemma responds in bounded JSON with strict schema:
  `{"action": "ask_question"|"run_case"|"recap", "message": "...", "case_id": null|id, "evidence_ids": [...]}`.
- [x] **Self-Repair & JSON Fence Handling:**
  - Strips leading BOM and markdown fences (` ```json `).
  - Implements a bounded single repair request when JSON is malformed, reusing existing evidence without leaking prompt instructions.
- [x] **Anti-Hallucination & Anti-Spoiler Filters:**
  - Verifies that `case_id` is an allowed ID from the exercise.
  - Verifies that `evidence_ids` match real past execution runs.
  - Rejects responses containing code fences, function definitions, direct solution keywords (`items is None`), or exaggerated praise.
- [x] **Quota & Outage Graceful Degradation:**
  - Clear identification of HTTP 429 (quota), 401/403 (auth), 500 (service error).
  - Explicit UI badge: **"Exercise hint · live Gemma unavailable"** (no pre-recorded hint is ever misrepresented as live AI).
- [x] **Budget Throttling:** Strict ceiling of 2 model requests per user action (including repairs).
- [x] **Context Window Pruning:** Automatically bounds dialogue history to the last 3–4 turns (up to 8 messages) and active revision evidence to 6 runs, preventing context bloat in long sessions.
- [x] **Structured Response Enforcement:** Configures `"responseMimeType": "application/json"` on Google Gemini API calls while preserving BOM/fence stripping and 1-turn repair fallbacks.

### 3.3 Code Execution Engine
- [x] **Trusted Local Runner:**
  - Stripped environment (does not forward `GEMINI_API_KEY` or host secrets).
  - POSIX process group cleanup (`os.killpg(SIGKILL)`) to prevent runaway processes.
  - Resource limits: CPU time (2s), file size (1MB), memory (Linux AS limit 256MB).
  - Output truncation at 4 KiB total output and 64 KiB child total.
  - Explicit user opt-in required in UI ("I am running only code I trust").
- [x] **Docker Container Runner:**
  - Non-root user (`65534:65534`), dropped capabilities (`--cap-drop=ALL`).
  - Read-only root filesystem, network disabled (`--network=none`).
  - Resource limits: 256MB RAM, 1 CPU, 32 PIDs, temporary in-memory `/tmp`.
  - Temporary input harness mounted read-only; `--pull=never` flag to avoid surprise image downloads.

### 3.4 Curated Exercise Bank
- [x] **Exercise 1: `basket` ("The basket that remembers")**
  - *Bug:* Default mutable argument `items=[]`.
  - *Trap:* Naive fix `if not items: items = []` fails when caller provides an intentional empty list `[]`.
  - *Suite:* 5 test cases covering fresh repeat, provided empty, provided nonempty, explicit `None`, and mutation inheritance.
- [x] **Exercise 2: `largest` ("The largest number that isn't there")**
  - *Bug:* Initializing `best = 0` fails on all-negative inputs `[-8, -3, -11]`.
  - *Trap:* Empty list requirement requires explicit `ValueError`.
  - *Suite:* 5 test cases covering positive, all-negative, single negative, empty list, and mixed duplicate values.
- [x] **Exercise 3: `total` ("The disappearing last number")**
  - *Bug:* Off-by-one boundary error `for i in range(len(numbers) - 1)`.
  - *Trap:* Trailing zero can mask the omission `[2, 3, 0]`.
  - *Suite:* 5 test cases covering ordinary integers, single element, empty list, negative values, and ending zero.

### 3.5 Persistence, Hydration & Privacy
- [x] **Atomic JSON Notebooks:** Writes to a tempfile in `data/`, flushes, fsyncs, and replaces atomically.
- [x] **Session Hydration & Resumption:** Full state hydration from disk (`list_saved_sessions()` and `load_session()`) in `core.py`, with UI selectors in the sidebar and notebook tab.
- [x] **Strict Hash Invariant on Resumption:** Hydrating a saved session retains verified status only if code matches; editing even a single character immediately invalidates `verified_hash`.
- [x] **Zero Secret Leakage:** Child execution environment and saved notebook files never receive the API key.
- [x] **Session Export:** Downloadable JSON report button in the UI.

### 3.6 Automated Testing
- [x] **Unit & Integration Suite:** 26 tests covering execution runner, timeout handling, syntax errors, output limits, model response parsing, JSON fences, single repair loop, context window pruning, HTTP 500 and timeout graceful fallbacks, session hydration & invalidation, and Streamlit UI flow.

---

## 4. Current Situation & Known Gaps

1. **Live Gemma API Stability:**
   - Real-world preflight testing on Mac showed `gemma-4-26b-a4b-it` succeeded in 3.43 seconds, while `31b` returned an HTTP 500.
   - Live multi-turn sessions with Google AI Studio API must be verified for JSON stability and quota limits before presentations.
2. **Docker Execution Unexercised:**
   - The Docker runner code path is implemented and bounded, but has not been run in environments lacking a Docker daemon.
3. **Limited Exercise Library:**
   - Only 3 exercises currently exist (planned expansion for closures and recursion in Phase 4).
4. **Code Editor Capabilities:**
   - Currently uses Streamlit's native `st.text_area` without syntax highlighting, line numbers, or code autocompletion.

---

## 5. What Should Be Done (Roadmap)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Environment & Preflight (Immediate)                           │
│ • Activate .venv & install streamlit                                   │
│ • Validate all 21 unit tests on local machine                          │
│ • Execute live preflight.py with real Google AI Studio API key         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 2: Live Demo & Presentation Readiness                            │
│ • Rehearse 4-minute demo walkthrough (DEMO.md)                         │
│ • Verify degraded fallback mode behaves gracefully during outages      │
│ • Capture backup screen recording of successful session                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 3: AI Robustness & API Hardening                                 │
│ • Test native Gemini structured outputs (response_schema) if supported │
│ • Fine-tune Socratic prompt to minimize chat length and latency        │
│ • Add token count monitoring to prevent context window overflow        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 4: Feature Enhancements (Post-Demo)                              │
│ • Expand exercise bank (mutability, closures, recursion, floats)      │
│ • Replace st.text_area with Monaco / Ace editor component              │
│ • Implement session resume / reload from historical notebook JSON     │
│ • Step-by-step visual trace inspection (Python Tutor style)            │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed Next Action Items

#### Immediate (Pre-Demo)
1. **Set up local virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run full automated validation:**
   ```bash
   python -m unittest discover -s tests -v
   ```
3. **Execute preflight test with live Gemma model:**
   ```bash
   python preflight.py --trusted-local --model gemma-4-26b-a4b-it
   ```
4. **Dry run the 4-minute demo script** according to [`DEMO.md`](DEMO.md).

#### Short-Term Improvements
1. **Structured Outputs for Gemma:** Explore Google Gemini API's `response_mime_type: "application/json"` or schema constraints to guarantee JSON output without needing regex fence peeling or repair turns.
2. **Session Resume:** Add a "Load previous session" selector in the "My Notebook" tab to allow learners to pick up where they left off after closing the browser.
3. **Editor Upgrade:** Replace `st.text_area` with a dedicated code editor component (e.g., `streamlit-code-editor` or `streamlit-monaco`) for Python syntax highlighting and line numbers.

#### Long-Term Expansion
1. **New Concept Exercises:**
   - *Recursion:* Missing or incorrect base case in Fibonacci or tree traversal.
   - *Scoping & Closures:* Late binding in loop lambdas/closures (`[lambda: i for i in range(5)]`).
   - *Floating Point Equality:* Accumulation rounding errors (`0.1 + 0.2 != 0.3`).
   - *Shallow vs. Deep Copy:* Modifying nested lists within copied containers.
2. **Visual Memory / Object Graph Inspection:** Show a diagram of object references (e.g., default list pointer surviving across calls) directly in the execution panel.
3. **Adversarial Sandbox Hardening:** If hosted on a public server, replace `trusted-local` with WebAssembly (Pyodide) running in the client's browser, or a hardened microVM / gVisor backend.

