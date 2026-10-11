# DuckTutor 🦆 — VS Code Extension

**DuckTutor** is a Socratic, evidence-based debugging assistant for VS Code inspired by the rubber-duck debugging methodology and CS50's Duck.

Rather than immediately generating patches or spoiling solutions like traditional code-generation bots, DuckTutor guides learners through active problem discovery:

```
Predict with Confidence ➔ Execute ➔ Investigate Evidence ➔ Edit in Editor ➔ Challenge ➔ Verify ➔ Remember
```

---

## Features

### 1. 4-Stage Socratic Learning Loop
- **Stage 1: Predict with Confidence** — Examine the code and predict what will happen before running it. Rate your confidence (1–5) and provide your rationale.
- **Stage 2: Investigate (Evidence & Observation)** — Python executes the code and records real runtime evidence. Gemma / DuckTutor probes your faulty assumptions with focused Socratic questions (without spoiling the answer).
- **Stage 3: Guide & Check (Verification & Challenge)** — Edit directly in VS Code or the webview. Every edit generates a new SHA-256 revision hash and immediately invalidates previous pass verdicts. Run targeted challenge tests and verify the complete test suite.
- **Stage 4: Reflect & Remember (Transfer Diagnostic)** — Complete a conceptual transfer check that tests your deep understanding of the root concept (e.g. mutable default arguments, loop boundaries, closure late binding).

### 2. Dual Mode: Curated Exercises + Active Workspace Code
- **5 Curated Exercises:**
  - 🛒 **The basket that remembers:** Shared mutable state (`items=[]`)
  - 🔢 **The largest number that isn't there:** Initialization & input coverage (`best = 0`)
  - ➕ **The disappearing last number:** Exclusive loop boundaries (`range(len(numbers) - 1)`)
  - 🔄 **The functions that forgot their numbers:** Late binding in closures (`lambda x: x * i`)
  - ⏳ **The countdown that stops too soon:** Recursion base cases (`countdown(n - 1)`)
- **Active Workspace Debugging:** Right-click any Python code or click the Status Bar icon to start a Socratic Duck Debugging session on your own functions and scripts.

### 3. Native VS Code UI & Private Notebook
- **Activity Bar Panel:** Dedicated DuckTutor view container in the side bar with dark/light theme integration.
- **Status Bar Item:** One-click quick toggle `$(beaker) DuckTutor 🦆`.
- **Debugging Notebook:** Automatically saves your predictions, confidence levels, attempts, and verification status to your local storage.

---

## Configuration Settings

DuckTutor can be configured under VS Code **Settings (`Ctrl+,`) ➔ Extensions ➔ DuckTutor**:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `ducktutor.apiKey` | `""` | Google AI Studio / Gemini API Key (or set `GEMINI_API_KEY` / `GOOGLE_API_KEY` env var). |
| `ducktutor.model` | `gemma-4-26b-a4b-it` | Socratic model (`gemma-4-26b-a4b-it`, `gemma-4-31b-it`, `gemini-1.5-flash`, `gemini-2.5-flash`). |
| `ducktutor.provider` | `google` | AI Provider (`google` for Google AI Studio or `ollama` for local inference). |
| `ducktutor.ollamaUrl` | `http://127.0.0.1:11434` | Ollama local endpoint if provider is `ollama`. |
| `ducktutor.pythonPath` | `python` | Path to the Python interpreter used to run test cases. |

> **Note on Linters:** DuckTutor runs self-contained Python execution harnesses directly against your configured Python interpreter. No `pycodestyle` or external style linters are required.

---

## Commands

- `DuckTutor: Focus DuckTutor Panel` — Opens the sidebar webview.
- `DuckTutor: Socratic Debug on Active File / Selection` — Begins duck debugging your current editor file.
- `DuckTutor: Start Exercise` — Quick pick to launch any of the 5 curated exercises.
- `DuckTutor: Configure Gemini / Gemma API Key` — Easily enter your Google AI Studio API key.
- `DuckTutor: Reset Current Debugging Session` — Resets session state.

---

## Development & Testing

```bash
cd ducktutor-extension
npm.cmd install
npm.cmd run bundle
node tests/test_extension_core.js
```
