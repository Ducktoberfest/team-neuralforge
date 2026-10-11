# DuckTutor — Project Status & Roadmap

> **Team NeuralForge** · *Ducktoberfest 2026*  
> **Repository:** `https://github.com/Ducktoberfest/team-neuralforge`  
> **Status Date:** October 2026  
> **Version:** 0.3.0  

---

## 0. Current update — 0.3.0, 11 October 2026

Both tracks are unified and passing on branch `add_own_code`.

1. **Own-Code Tutoring Workspace (`workspace_ui.py`):** The primary mode allows learners to paste code in 8 languages, set a goal, report runtime output/errors with revision attribution, and engage in Socratic dialogues with concept explanations, progressive hints, and continuity notes.
2. **7 Curated Practice Exercises (`exercises.py`):** Expanded from 5 to 7 exercises (`basket`, `largest`, `total`, `closures`, `countdown`, `shallow_copy`, `scope_leak`) with 35 curated test cases, 3 tiered hints each, anti-spoiler regexes, and interactive Stage 4 mental model transfer checks.
3. **Pure-Python Offline Audio Engine (`sound_effects.py`):** Zero-dependency WAV audio synthesizer generating authentic rubber duck quacks, squeaks, and celebratory fanfares for prediction submits, hints, verification passes/retries, transfer reflections, and an interactive "🦆 Squeeze the Duck!" sidebar button.
4. **Evaluation & Verification Suite:** Includes `evaluate_tutor.py` with 6 conversation scenarios and unscored rubrics (`conversation_evals.json`), alongside a unified test suite with **56 passing automated tests** across 7 test files on Python 3.14 with Streamlit.

Hosted Gemma 26B (`gemma-4-26b-a4b-it`) remains the recommended default model with a 20-second timeout; 31B is supported with automatic 500 error detection and a one-click 26B recovery button. Own-code mode performs code analysis without unconstrained server execution; practice mode uses isolated local child processes or Docker.

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
6. **Automatic Private Notebook & Hydration:** Every session is saved locally as an atomic JSON record (`data/<session_id>.json`). The notebook preserves predictions, confidence ratings, attempts, requested hints, execution runs, and reflection responses without logging credentials, and supports full state hydration back into active memory.

---

## 2. Current Architecture & Codebase Map

| File | Purpose | Key Responsibilities |
| :--- | :--- | :--- |
| [`app.py`](app.py) | **Streamlit UI** | Main user interface: sidebar configuration (workspace mode, Gemma provider, API key, execution mode, session resumption expander, audio effects), own-code discussion tab, 4-stage practice learning tab, and the persistent "My Notebook" tab. |
| [`workspace_ui.py`](workspace_ui.py) | **Own-Code Workspace** | Main workspace for discussing learner-provided code, defining goals, reporting runtime outputs, and engaging in Socratic tutoring without mandatory test cases. |
| [`sound_effects.py`](sound_effects.py) | **Audio Engine & Quacks** | Pure-Python offline WAV audio synthesizer (0 dependencies); authentic rubber duck quacks, squeaks, and celebratory fanfare on predictions, hints, and verified solutions. |
| [`core.py`](core.py) | **Session & State Machine** | Orchestrates session states (`predict` → `guide` → `reflect`), own-code tracking, code synchronization, revision hash invalidation, request budget management (max 2 per action), fallback guidance when Gemma is unavailable, atomic notebook persistence, and **full session hydration/resumption (`list_saved_sessions()`, `load_session()`)**. |
| [`tutor.py`](tutor.py) | **Model Interface & Guardrails** | Transports requests to Hosted Gemma (`gemma-4-26b-a4b-it`, `gemma-4-31b-it`) via Google AI Studio API or local Ollama; enforces strict JSON protocol and `"responseMimeType": "application/json"`; performs **context window pruning**; validates allowed actions, test IDs, and evidence IDs; filters spoilers and protects identifier rewriting. |
| [`runner.py`](runner.py) | **Execution Runner** | Manages code execution under two modes: `trusted-local` (child process with clean environment, resource bounds, process-group termination, 64 KiB stdout cap) and `docker` (container with `--network=none`, `--read-only`, dropped capabilities, memory/CPU caps). |
| [`worker.py`](worker.py) | **Child Process Harness** | Safe execution script executed inside the runner. Captures `stdout`/`stderr` up to 4 KiB, applies CPU and file size `rlimit`s, compiles and executes user code against the specified case script. |
| [`exercises.py`](exercises.py) | **Exercise & Case Catalog** | Defines 7 curated exercises (`basket`, `largest`, `total`, `closures`, `countdown`, `shallow_copy`, `scope_leak`) with specifications, starter code containing pedagogical traps, prediction choices, curated test cases (5 checks each, 35 total), reference solutions, forbidden patterns, explanations, tiered hint templates, and `TransferReflection`. |
| [`evaluate_tutor.py`](evaluate_tutor.py) | **Conversation Evaluator** | Runs controlled, reproducible multi-turn conversations against human rubrics (`conversation_evals.json`) to inspect model pedagogy. |
| [`preflight.py`](preflight.py) | **CLI Preflight Diagnostic** | Terminal script to test execution and live Gemma round-trip (`gemma-4-26b-a4b-it` default) before starting the Streamlit application. |
| [`tests/`](tests/) | **Automated Test Suite** | 56 test cases across `test_learning.py` (learning lifecycle, session hydration & invalidation, 7-exercise runner, transfer checks, anti-spoilers), `test_responses.py` (JSON parsing, BOM, fences, context pruning, HTTP 500 / timeout fallback), `test_ui.py` (Streamlit AppTest practice UI automation), `test_own_ui.py` (Own-code workspace AppTest automation), `test_tutoring.py` (pedagogical heuristics and guardrails), `test_evaluation.py` (evaluation scenario schemas), and `test_audio.py` (WAV audio synthesis, RIFF parsing, data URI formatting, audio UI controls). |

---

## 3. What Is Already Done

### 3.0 Engineering Milestones Summary
- [x] **Phase 1: Environment Setup & Verification** — Python 3.14 `.venv` created, `streamlit==1.65.0` installed, baseline tests passing (21/21 tests).
- [x] **Phase 2: AI Robustness, Context Pruning & Model Fallback** (commit `2461878`) — Context window pruning (capped at 3–4 dialogue turns / 8 messages & 6 evidence items), `"responseMimeType": "application/json"`, default model `gemma-4-26b-a4b-it`, and HTTP 500 / timeout resilient fallback (24/24 tests).
- [x] **Phase 3: Session Hydration & Persistence** (commit `94bfb35`) — `list_saved_sessions()` and `load_session()` in `core.py`, sidebar & notebook resume UI, strict revision hash invalidation (`verified_hash = None` upon edit) (26/26 tests).
- [x] **Phase 4: Exercise Catalog Expansion** (commit `2ba5abe`) — Added `closures` (late binding) and `countdown` (recursion base case), exercise-specific anti-spoiler forbidden patterns, 25 test cases total across 5 exercises (27/27 tests).
- [x] **Phase 5: Documentation Synchronization & Demo Readiness** (commit `2277041`) — Synchronized `README.md`, `PROJECT_STATUS.md`, and `DEMO.md` with complete v0.2.0 capabilities (27/27 tests).
- [x] **Phase 6: Interactive Transfer Reflection** (commit `a929656`) — Elevated Stage 4 (`reflect`) with interactive diagnostic transfer checks (`transfer_snippet`, `transfer_prompt`, choices, immediate evaluation, conceptual explanation) across all exercises and notebook persistence (29/29 tests).
- [x] **Phase 7: Own-Code Workspace & Multi-Language Socratic Dialogue** (commit `47cd7e7`) — Implemented `workspace_ui.py`, multi-language selection (Python, JS, TS, C, C++, Java, SQL), revision-attributed output reporting, `evaluate_tutor.py` conversation evaluation suite with 6 rubrics (50/50 tests).
- [x] **Phase 8: Offline Duck Audio Synthesizer, 7 Exercises & Track Unification** (commit `c4a7e29`) — Pure-Python WAV synthesizer (`sound_effects.py`), 6 contextual sound effects with sidebar controls and squeeze button, exercises 6 & 7 (`shallow_copy`, `scope_leak`) with 35 test cases total, safe choice parsing (56/56 tests passing).

### 3.1 Learning Workflow & State Management
- [x] **4-Stage Learning Lifecycle:** `predict` ➔ `guide` ➔ `check` ➔ `reflect`.
- [x] **Revision Tracking:** SHA-256 code hashing invalidates pass status immediately upon code edit.
- [x] **Confidence Assessment:** 1–5 confidence slider + textual rationale captured before execution.
- [x] **Selective Challenge Execution:** Gemma selects a targeted test case from the reviewed catalog to challenge incomplete student patches.
- [x] **Full Suite Verification:** Once the initial check and challenge pass, all 5 cases are run to verify the revision.
- [x] **Progressive Hinting:** Hint levels 0 (observation probe), 1 (conceptual hint), and 2 (location hint).
- [x] **Solution Reveal Drawer:** Explicit button to view the reference solution; records that the solution was viewed in the notebook.
- [x] **Interactive Transfer Checks:** Complete Stage 4 diagnostic transfer check across all 5 exercises with immediate evaluation, feedback linking back to root misconception, and atomic notebook persistence.

### 3.2 Gemma AI Model Integration & Robustness
- [x] **Multi-Provider Support:**
  - Google AI Studio (Hosted Gemma: `gemma-4-26b-a4b-it` [default] and `gemma-4-31b-it`).
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
  - Exercise-specific forbidden regex patterns enforce zero solution leaks across all 5 exercises.
- [x] **Quota & Outage Graceful Degradation:**
  - Clear identification of HTTP 429 (quota), 401/403 (auth), 500/502/503/504, and network timeouts.
  - Explicit UI badge: **"Exercise hint · live Gemma unavailable"** (suggesting `gemma-4-26b-a4b-it` without breaking Streamlit state).
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
- [x] **Exercise 4: `closures` ("The functions that forgot their numbers")**
  - *Bug:* Late-binding loop closures `[lambda x: x * i for i in range(n)]`.
  - *Trap:* All closures evaluate `i` at call time (retaining final loop value `n - 1`), returning identical multipliers.
  - *Suite:* 5 test cases covering multiple functions, single function, zero/negative inputs, and repeated calls with varied arguments.
- [x] **Exercise 5: `countdown` ("The countdown that stops too soon")**
  - *Bug:* Base case boundary omission `if n <= 1: return [1]`.
  - *Trap:* Omits 0 from countdown descent and returns `[1]` for zero and negative inputs.
  - *Suite:* 5 test cases covering normal countdown, zero boundary, single element (1), negative inputs, and large recursion chain.
- [x] **Exercise 6: `shallow_copy` ("The copy that wasn't independent")**
  - *Bug:* 2D grid mutation with `grid.copy()` / `list(grid)` sharing nested list references.
  - *Trap:* Outer list is duplicated, but modifying cells in copy mutates original inner row.
  - *Suite:* 5 test cases covering separate cells, row append, empty grid, single row, and distinct memory instances.
- [x] **Exercise 7: `scope_leak` ("The variable found too late")**
  - *Bug:* Closure `UnboundLocalError` when re-binding enclosing variables (`count += step`) without `nonlocal`.
  - *Trap:* Variable is read before local assignment inside tick function.
  - *Suite:* 5 test cases covering consecutive calls, custom step, negative steps, independent instances, and default start.

### 3.5 Persistence, Hydration & Privacy
- [x] **Atomic JSON Notebooks:** Writes to a tempfile in `data/`, flushes, fsyncs, and replaces atomically.
- [x] **Session Hydration & Resumption:** Full state hydration from disk (`list_saved_sessions()` and `load_session()`) in `core.py`, with UI selectors in the sidebar and notebook tab.
- [x] **Strict Hash Invariant on Resumption:** Hydrating a saved session retains verified status only if code matches; editing even a single character immediately invalidates `verified_hash`.
- [x] **Zero Secret Leakage:** Child execution environment and saved notebook files never receive the API key.
- [x] **Session Export:** Downloadable JSON report button in the UI.

### 3.6 Automated Testing
- [x] **Unit & Integration Suite:** 56 tests covering execution runner, timeout handling, syntax errors, output limits, model response parsing, JSON fences, single repair loop, context window pruning, HTTP 500 and timeout graceful fallbacks, session hydration & invalidation, 7-exercise anti-spoiler verification, own-code workspace UI, tutoring guardrails, evaluation schemas, and pure-Python audio synthesis.

---

## 4. Current Situation & Known Gaps

1. **Unified Version 0.3.0 on `add_own_code`:**
   - Both development tracks are merged: Own-code workspace (`workspace_ui.py`), 7 curated practice exercises (`exercises.py`), offline duck audio engine (`sound_effects.py`), and evaluation suite (`evaluate_tutor.py`).
   - All **56 automated tests** pass cleanly in ~4.6s.
2. **Live Gemma API Stability:**
   - `gemma-4-26b-a4b-it` is configured as the default recommended model across `app.py`, `preflight.py`, and `evaluate_tutor.py`.
   - Intermittent 500/503 errors on `gemma-4-31b-it` are automatically caught with an actionable warning and a direct "Switch to Gemma 26B & Retry" button.
3. **Execution Separation:**
   - Own-code mode performs client-side analysis and Socratic guidance without unconstrained server execution.
   - Practice exercise mode uses isolated local child processes (with POSIX process groups, resource limits, and stripped environments) or Docker containers.
4. **Code Editor:**
   - Uses Streamlit's native `st.text_area` for universal cross-platform compatibility and headless test automation without extra frontend dependencies.

---

## 5. Completed Roadmap & Next Action Items

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Environment & Baseline Verification [COMPLETE]                │
│ • Activate .venv & install streamlit 1.65.0                            │
│ • Baseline test suite passing (21/21 tests)                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 2: AI Robustness & Model Fallback [COMPLETE - commit 2461878]    │
│ • Context window pruning (last 3-4 dialogue turns + active evidence)   │
│ • Default model gemma-4-26b-a4b-it & responseMimeType JSON mode       │
│ • HTTP 500 / timeout graceful fallback state (24/24 tests)             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 3: Session Hydration & Persistence [COMPLETE - commit 94bfb35]   │
│ • list_saved_sessions() and load_session() in core.py                  │
│ • Sidebar & Notebook UI session selector with pending exercise sync    │
│ • Strict revision hash invalidation upon edit (26/26 tests)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 4: Exercise Catalog Expansion [COMPLETE - commit 2ba5abe]        │
│ • Added closures (late binding) & countdown (recursion) exercises      │
│ • 5 test cases per exercise (25 cases total) + forbidden anti-spoilers │
│ • Validated runner & solution execution (27/27 tests)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 5: Documentation & Demo Readiness [COMPLETE - v0.2.0]            │
│ • Synchronize README.md, PROJECT_STATUS.md, and DEMO.md                │
│ • Full test suite passing (27/27 tests)                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 6: Interactive Transfer Reflection [COMPLETE - commit a929656]   │
│ • Stage 4 diagnostic transfer check across all exercises               │
│ • Immediate evaluation, feedback linking back to root misconception    │
│ • Full test suite passing (29/29 tests)                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 7: Own-Code Workspace & Evaluation [COMPLETE - commit 47cd7e7]   │
│ • workspace_ui.py with multi-language selection & revision output      │
│ • evaluate_tutor.py conversation evaluation suite (6 rubrics)          │
│ • Full test suite passing (50/50 tests)                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 8: Duck Audio, 7 Exercises & Unification [COMPLETE - commit c4a7e29]
│ • sound_effects.py pure-Python offline WAV audio synthesizer           │
│ • Catalog expansion to 7 exercises (shallow_copy, scope_leak)          │
│ • Both tracks unified on add_own_code branch                           │
│ • Full test suite passing (56/56 tests)                                │
└────────────────────────────────────────────────────────────────────────┘
```

### Future Enhancements (Post-v0.3.0)
1. **Interactive Memory Diagram Visualizer:** Generate inline Mermaid diagrams visualizing stack vs. heap and reference aliasing for nested structures and closures.
2. **Notebook Export Format Options:** Export completed debugging journeys not only as JSON, but as formatted Jupyter Notebooks (`.ipynb`) or Markdown study guides.
3. **Client-side Pyodide Sandbox:** In-browser WebAssembly Python execution for zero-server untrusted code execution.

