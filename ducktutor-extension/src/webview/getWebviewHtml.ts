import * as vscode from 'vscode';
import { Session, Exercise, RunResult } from '../types';
import { EXERCISES } from '../exercises';

export function getWebviewHtml(webview: vscode.Webview, session: Session | null, notebookHistory: Session[] = []): string {
  const nonce = getNonce();

  const currentExercise: Exercise | null = session && !session.isCustomCode ? EXERCISES[session.exerciseId] || null : null;
  const isCustom = !!session?.isCustomCode;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DuckTutor</title>
  <style>
    :root {
      --duck-amber: #f59e0b;
      --duck-amber-light: #fbbf24;
      --duck-amber-glow: rgba(245, 158, 11, 0.25);
      --duck-amber-subtle: rgba(245, 158, 11, 0.08);
      --duck-bg-card: var(--vscode-editorWidget-background, rgba(30, 30, 36, 0.95));
      --duck-border: var(--vscode-widget-border, rgba(255, 255, 255, 0.09));
      --duck-border-focus: var(--vscode-focusBorder, #007acc);
      --duck-pass: #22c55e;
      --duck-pass-bg: rgba(34, 197, 94, 0.12);
      --duck-fail: #ef4444;
      --duck-fail-bg: rgba(239, 68, 68, 0.12);
      --duck-user-bg: var(--vscode-button-secondaryBackground, #2d3748);
      --duck-font: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif);
      --duck-mono: var(--vscode-editor-font-family, 'Fira Code', 'Cascadia Code', Consolas, 'Courier New', monospace);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    /* Custom thin scrollbar */
    ::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.18);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--duck-amber);
    }

    body {
      font-family: var(--duck-font);
      font-size: var(--vscode-font-size, 13px);
      color: var(--vscode-editor-foreground, #e2e8f0);
      background-color: var(--vscode-editor-background, #121214);
      line-height: 1.5;
      padding: 12px;
      overflow-x: hidden;
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--duck-border);
      margin-bottom: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 9px;
      font-weight: 700;
      font-size: 1.15rem;
      color: var(--vscode-editor-foreground, #fff);
      letter-spacing: -0.01em;
    }
    .duck-mascot {
      font-size: 1.5rem;
      display: inline-block;
      filter: drop-shadow(0 2px 8px var(--duck-amber-glow));
      animation: duckBob 3s ease-in-out infinite;
      cursor: default;
    }
    @keyframes duckBob {
      0%, 100% { transform: translateY(0) rotate(0deg); }
      50% { transform: translateY(-3px) rotate(-3deg); }
    }
    .brand-meta {
      display: flex;
      flex-direction: column;
    }
    .brand-title-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .brand-badge {
      font-size: 0.65rem;
      background: linear-gradient(135deg, var(--duck-amber), #d97706);
      color: #000;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      box-shadow: 0 2px 6px var(--duck-amber-glow);
    }
    .brand-sub {
      font-size: 0.72rem;
      color: var(--vscode-descriptionForeground, #94a3b8);
      font-weight: 400;
    }

    /* Mode Segmented Switcher */
    .mode-switcher {
      display: flex;
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--duck-border);
      padding: 3px;
      border-radius: 8px;
      margin-bottom: 12px;
      gap: 3px;
    }
    .mode-tab {
      flex: 1;
      text-align: center;
      padding: 6px 8px;
      font-size: 0.78rem;
      font-weight: 600;
      border-radius: 6px;
      color: var(--vscode-descriptionForeground, #94a3b8);
      background: transparent;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
    }
    .mode-tab:hover {
      color: var(--vscode-editor-foreground, #fff);
      background: rgba(255, 255, 255, 0.05);
    }
    .mode-tab.active {
      background: var(--vscode-button-background, #0e639c);
      color: var(--vscode-button-foreground, #ffffff);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }

    /* Exercise Selector Container */
    .selector-container {
      margin-bottom: 12px;
      background: var(--duck-bg-card);
      border: 1px solid var(--duck-border);
      border-radius: 8px;
      padding: 10px;
    }
    .selector-container label {
      display: block;
      font-size: 0.73rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 5px;
      color: var(--vscode-descriptionForeground);
    }
    select, input[type="text"], textarea {
      width: 100%;
      background: var(--vscode-input-background, #1e1e24);
      color: var(--vscode-input-foreground, #fff);
      border: 1px solid var(--vscode-input-border, rgba(255, 255, 255, 0.12));
      border-radius: 6px;
      padding: 7px 10px;
      font-family: inherit;
      font-size: 0.84rem;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    select:focus, input[type="text"]:focus, textarea:focus {
      outline: none;
      border-color: var(--duck-amber);
      box-shadow: 0 0 0 2px var(--duck-amber-glow);
    }

    /* Stage Steps Bar */
    .stage-bar {
      display: flex;
      gap: 4px;
      margin-bottom: 14px;
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--duck-border);
      padding: 4px;
      border-radius: 8px;
    }
    .stage-pill {
      flex: 1;
      text-align: center;
      padding: 5px 3px;
      font-size: 0.72rem;
      font-weight: 600;
      border-radius: 5px;
      color: var(--vscode-descriptionForeground);
      background: transparent;
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .stage-pill:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--vscode-editor-foreground);
    }
    .stage-pill.active {
      background: linear-gradient(135deg, var(--duck-amber), #d97706);
      color: #000;
      font-weight: 700;
      box-shadow: 0 2px 8px var(--duck-amber-glow);
    }

    /* Cards */
    .card {
      background: var(--duck-bg-card);
      border: 1px solid var(--duck-border);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 12px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
      backdrop-filter: blur(10px);
    }
    .card-title {
      font-weight: 600;
      font-size: 0.88rem;
      margin-bottom: 9px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--vscode-editor-foreground);
    }

    /* Code Window Frame */
    .code-window {
      background: #0d1117;
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-radius: 7px;
      overflow: hidden;
      margin: 8px 0;
    }
    .code-window-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 10px;
      background: rgba(255, 255, 255, 0.04);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 0.72rem;
      color: var(--vscode-descriptionForeground);
    }
    .window-dots {
      display: flex;
      gap: 5px;
    }
    .window-dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      display: inline-block;
    }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #eab308; }
    .dot-green { background: #22c55e; }
    .code-window pre {
      margin: 0;
      padding: 10px;
      max-height: 170px;
      overflow-y: auto;
      font-family: var(--duck-mono);
      font-size: 0.82rem;
      line-height: 1.45;
      color: #e2e8f0;
      background: transparent;
      white-space: pre-wrap;
      word-break: break-all;
    }

    /* Buttons */
    button.btn-primary {
      width: 100%;
      background: linear-gradient(135deg, var(--duck-amber) 0%, #d97706 100%);
      color: #000;
      border: none;
      border-radius: 6px;
      padding: 9px 14px;
      font-weight: 700;
      font-size: 0.86rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 2px 10px var(--duck-amber-glow);
    }
    button.btn-primary:hover {
      filter: brightness(1.08);
      transform: translateY(-1px);
      box-shadow: 0 4px 14px var(--duck-amber-glow);
    }
    button.btn-primary:active {
      transform: translateY(0);
      filter: brightness(0.96);
    }
    button.btn-secondary {
      background: var(--vscode-button-secondaryBackground, rgba(255, 255, 255, 0.08));
      color: var(--vscode-button-secondaryForeground, #ffffff);
      border: 1px solid var(--duck-border);
      border-radius: 6px;
      padding: 7px 11px;
      font-weight: 600;
      font-size: 0.8rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: all 0.15s ease;
    }
    button.btn-secondary:hover {
      background: var(--vscode-button-secondaryHoverBackground, rgba(255, 255, 255, 0.14));
      border-color: rgba(255, 255, 255, 0.18);
    }

    /* Quick Chips */
    .chip-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--duck-border);
      color: var(--vscode-editor-foreground, #cbd5e1);
      border-radius: 14px;
      padding: 5px 11px;
      font-size: 0.74rem;
      font-weight: 500;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.18s ease;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .chip-btn:hover {
      background: var(--duck-amber-subtle);
      color: var(--duck-amber-light);
      border-color: var(--duck-amber);
      transform: translateY(-1px);
    }

    /* Choice Buttons */
    .choice-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin: 10px 0;
    }
    .choice-btn {
      background: var(--vscode-button-secondaryBackground, rgba(255, 255, 255, 0.06));
      color: var(--vscode-editor-foreground, #fff);
      border: 1px solid var(--duck-border);
      border-radius: 6px;
      padding: 8px 12px;
      text-align: left;
      font-family: var(--duck-mono);
      font-size: 0.83rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .choice-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .choice-btn.selected {
      border: 1.5px solid var(--duck-amber);
      background: var(--duck-amber-subtle);
      color: var(--duck-amber-light);
      font-weight: 600;
      box-shadow: 0 0 8px var(--duck-amber-glow);
    }

    /* Confidence Slider */
    .slider-container {
      margin: 12px 0;
    }
    .slider-labels {
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--vscode-descriptionForeground);
      margin-top: 4px;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--duck-amber);
      cursor: pointer;
    }

    /* Badges */
    .badge-hash {
      font-family: var(--duck-mono);
      font-size: 0.7rem;
      background: rgba(255, 255, 255, 0.08);
      color: var(--vscode-descriptionForeground);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid var(--duck-border);
    }
    .badge-pass {
      color: var(--duck-pass);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.8rem;
    }
    .badge-fail {
      color: var(--duck-fail);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.8rem;
    }

    /* Alerts */
    .alert {
      padding: 9px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      margin: 8px 0;
      line-height: 1.45;
    }
    .alert-success {
      background: var(--duck-pass-bg);
      border: 1px solid rgba(34, 197, 94, 0.35);
      color: var(--duck-pass);
    }
    .alert-error {
      background: var(--duck-fail-bg);
      border: 1px solid rgba(239, 68, 68, 0.35);
      color: #fca5a5;
    }
    .alert-info {
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.35);
      color: #93c5fd;
    }

    /* Chat Messages */
    .duck-chat-history {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 6px 2px;
      margin-bottom: 10px;
    }
    .chat-bubble-container {
      display: flex;
      flex-direction: column;
      width: 100%;
    }
    .chat-bubble-container.user {
      align-items: flex-end;
    }
    .chat-bubble-container.assistant {
      align-items: flex-start;
    }
    .chat-bubble-meta {
      font-size: 0.7rem;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 3px;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .chat-bubble {
      max-width: 92%;
      padding: 10px 13px;
      font-size: 0.85rem;
      line-height: 1.5;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    }
    .chat-bubble.user {
      background: var(--duck-user-bg);
      color: #fff;
      border-radius: 14px 14px 2px 14px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .chat-bubble.assistant {
      background: var(--duck-amber-subtle);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-left: 3px solid var(--duck-amber);
      border-radius: 4px 14px 14px 14px;
      color: var(--vscode-editor-foreground, #f1f5f9);
    }
    .chat-bubble.system {
      background: rgba(255, 255, 255, 0.04);
      border: 1px dashed var(--duck-border);
      border-radius: 8px;
      color: var(--vscode-descriptionForeground);
      font-size: 0.78rem;
      font-style: italic;
      align-self: center;
      max-width: 100%;
      text-align: center;
    }

    /* Inline markdown formatting */
    code.inline-code {
      background: rgba(0, 0, 0, 0.35);
      color: var(--duck-amber-light);
      padding: 1px 5px;
      border-radius: 4px;
      font-family: var(--duck-mono);
      font-size: 0.8em;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .chat-bubble pre {
      background: #0d1117;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      padding: 8px 10px;
      margin: 6px 0;
      overflow-x: auto;
      font-family: var(--duck-mono);
      font-size: 0.8rem;
    }

    /* Typing Indicator */
    .duck-typing-indicator {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 10px;
      background: var(--duck-amber-subtle);
      border: 1px solid rgba(245, 158, 11, 0.18);
      border-radius: 12px;
      align-self: flex-start;
      margin-top: 4px;
      animation: fadeIn 0.2s ease-in;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .typing-dots {
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }
    .typing-dots span {
      width: 5px;
      height: 5px;
      background: var(--duck-amber);
      border-radius: 50%;
      animation: typingBounce 1.2s infinite ease-in-out;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typingBounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1.1); opacity: 1; }
    }

    /* Chat Input Bar */
    .chat-input-capsule {
      display: flex;
      align-items: center;
      background: var(--vscode-input-background, #1a1a20);
      border: 1px solid var(--vscode-input-border, rgba(255, 255, 255, 0.14));
      border-radius: 24px;
      padding: 4px 6px 4px 14px;
      gap: 6px;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    }
    .chat-input-capsule:focus-within {
      border-color: var(--duck-amber);
      box-shadow: 0 0 0 2px var(--duck-amber-glow);
    }
    .chat-input-capsule input {
      flex: 1;
      border: none;
      background: transparent;
      padding: 6px 0;
      color: var(--vscode-input-foreground, #fff);
      font-size: 0.84rem;
      outline: none;
    }
    .btn-capsule-send {
      background: linear-gradient(135deg, var(--duck-amber), #d97706);
      color: #000;
      border: none;
      border-radius: 18px;
      padding: 6px 13px;
      font-weight: 700;
      font-size: 0.78rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }
    .btn-capsule-send:hover {
      filter: brightness(1.1);
      transform: scale(1.03);
    }

    /* Test Case Status Rows */
    .test-case-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 7px 10px;
      border-bottom: 1px solid var(--duck-border);
      font-size: 0.81rem;
    }
    .test-case-row:last-child {
      border-bottom: none;
    }

    .action-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin: 10px 0;
    }

    .history-item {
      padding: 8px 10px;
      border-bottom: 1px solid var(--duck-border);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.15s ease;
      border-radius: 4px;
    }
    .history-item:hover {
      background: var(--vscode-list-hoverBackground, rgba(255, 255, 255, 0.06));
    }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="brand">
      <span class="duck-mascot">🦆</span>
      <div class="brand-meta">
        <div class="brand-title-row">
          <span>DuckTutor</span>
          <span class="brand-badge">Socratic AI</span>
        </div>
        <span class="brand-sub">Powered by Gemma 4 · Pair Debugger</span>
      </div>
    </div>
    <button class="btn-secondary" id="btn-notebook-toggle" title="View Debugging Notebook">📓 Notes</button>
  </div>

  <!-- Segmented Mode Switcher -->
  <div class="mode-switcher">
    <button class="mode-tab ${isCustom ? 'active' : ''}" id="tab-mode-custom">
      <span>📄</span> My Code (Chat)
    </button>
    <button class="mode-tab ${!isCustom ? 'active' : ''}" id="tab-mode-exercises">
      <span>🎯</span> Practice Traps
    </button>
  </div>

  <!-- Exercise Selector (shown when in exercise mode) -->
  <div id="exercise-picker-card" class="selector-container" style="display: ${isCustom ? 'none' : 'block'};">
    <label for="exercise-select">Choose Practice Trap:</label>
    <select id="exercise-select">
      <option value="basket" ${session?.exerciseId === 'basket' ? 'selected' : ''}>🛒 The basket that remembers (Mutable Default)</option>
      <option value="largest" ${session?.exerciseId === 'largest' ? 'selected' : ''}>🔢 The largest number that isn't there (Initialization)</option>
      <option value="total" ${session?.exerciseId === 'total' ? 'selected' : ''}>➕ The disappearing last number (Loop Boundary)</option>
      <option value="closures" ${session?.exerciseId === 'closures' ? 'selected' : ''}>🔄 The functions that forgot their numbers (Closures)</option>
      <option value="countdown" ${session?.exerciseId === 'countdown' ? 'selected' : ''}>⏳ The countdown that stops too soon (Recursion)</option>
    </select>
  </div>

  <!-- Main Content View -->
  ${isCustom ? renderCustomCodeChatView(session) : renderExerciseStages(session, currentExercise)}

  <!-- Notebook Drawer -->
  <div id="notebook-drawer" class="card" style="display: none; margin-top: 14px;">
    <div class="card-title">
      <span>📓 Learning Notebook</span>
      <button class="btn-secondary" id="btn-close-notebook" style="padding: 2px 7px;">✕</button>
    </div>
    <div style="font-size: 0.76rem; color: var(--vscode-descriptionForeground); margin-bottom: 8px;">
      Saved debugging sessions and insights:
    </div>
    <div id="notebook-list">
      ${renderNotebookList(notebookHistory)}
    </div>
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();

    // Mode tabs
    const tabModeCustom = document.getElementById('tab-mode-custom');
    const tabModeExercises = document.getElementById('tab-mode-exercises');
    const exercisePickerCard = document.getElementById('exercise-picker-card');
    const exerciseSelect = document.getElementById('exercise-select');

    if (tabModeCustom) {
      tabModeCustom.addEventListener('click', () => {
        vscode.postMessage({ command: 'debug_active_editor' });
      });
    }

    if (tabModeExercises) {
      tabModeExercises.addEventListener('click', () => {
        const val = exerciseSelect ? exerciseSelect.value : 'basket';
        vscode.postMessage({ command: 'select_exercise', exerciseId: val });
      });
    }

    if (exerciseSelect) {
      exerciseSelect.addEventListener('change', (e) => {
        vscode.postMessage({ command: 'select_exercise', exerciseId: e.target.value });
      });
    }

    // Custom code actions
    const btnRunDiagnose = document.getElementById('btn-run-diagnose');
    const btnSyncEditor = document.getElementById('btn-sync-editor');
    const btnCopyCode = document.getElementById('btn-copy-code');

    function showDuckThinking() {
      const ind = document.getElementById('duck-typing-indicator');
      if (ind) {
        ind.style.display = 'flex';
        const box = ind.closest('.duck-chat-history');
        if (box) box.scrollTop = box.scrollHeight;
      }
    }

    if (btnRunDiagnose) {
      btnRunDiagnose.addEventListener('click', () => {
        showDuckThinking();
        vscode.postMessage({ command: 'run_and_diagnose' });
      });
    }

    const btnReviewCode = document.getElementById('btn-review-code');
    if (btnReviewCode) {
      btnReviewCode.addEventListener('click', () => {
        showDuckThinking();
        vscode.postMessage({ command: 'review_code' });
      });
    }

    if (btnSyncEditor) {
      btnSyncEditor.addEventListener('click', () => {
        vscode.postMessage({ command: 'sync_active_editor' });
      });
    }

    if (btnCopyCode) {
      btnCopyCode.addEventListener('click', () => {
        const codeElem = document.getElementById('active-code-display');
        if (codeElem) {
          navigator.clipboard.writeText(codeElem.textContent || '');
          btnCopyCode.textContent = '✓ Copied!';
          setTimeout(() => { btnCopyCode.textContent = '📋 Copy'; }, 2000);
        }
      });
    }

    // Quick-prompt chips
    document.querySelectorAll('.duck-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const text = chip.getAttribute('data-text');
        if (text) {
          showDuckThinking();
          vscode.postMessage({ command: 'send_chat', text });
        }
      });
    });

    // Chat send
    function sendChatFromInput() {
      const input = document.getElementById('duck-chat-input-field');
      if (input && input.value.trim()) {
        const text = input.value.trim();
        input.value = '';
        showDuckThinking();
        vscode.postMessage({ command: 'send_chat', text });
      }
    }

    const btnChatSend = document.getElementById('btn-chat-send');
    if (btnChatSend) {
      btnChatSend.addEventListener('click', sendChatFromInput);
    }

    const chatInputField = document.getElementById('duck-chat-input-field');
    if (chatInputField) {
      chatInputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendChatFromInput();
        }
      });
    }

    // Exercise stage controls
    const confidenceRange = document.getElementById('confidence-range');
    const confVal = document.getElementById('conf-val');
    if (confidenceRange && confVal) {
      confidenceRange.addEventListener('input', (e) => {
        confVal.textContent = e.target.value;
      });
    }

    let selectedChoice = null;
    document.querySelectorAll('.choice-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.choice-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedChoice = btn.getAttribute('data-choice');
      });
    });

    const btnSubmitPrediction = document.getElementById('btn-submit-prediction');
    if (btnSubmitPrediction) {
      btnSubmitPrediction.addEventListener('click', () => {
        const customPred = document.getElementById('custom-prediction-input');
        const prediction = customPred ? customPred.value : selectedChoice;
        const confidence = parseInt(confidenceRange ? confidenceRange.value : 3);
        const explanationText = document.getElementById('explanation-text');
        const explanation = explanationText ? explanationText.value : '';

        showDuckThinking();
        vscode.postMessage({
          command: 'submit_prediction',
          prediction,
          confidence,
          explanation
        });
      });
    }

    const btnOpenEditor = document.getElementById('btn-open-editor');
    if (btnOpenEditor) {
      btnOpenEditor.addEventListener('click', () => {
        vscode.postMessage({ command: 'open_in_editor' });
      });
    }

    const btnSyncCode = document.getElementById('btn-sync-code');
    if (btnSyncCode) {
      btnSyncCode.addEventListener('click', () => {
        vscode.postMessage({ command: 'sync_code_from_editor' });
      });
    }

    const editorCode = document.getElementById('editor-code');
    if (editorCode) {
      editorCode.addEventListener('input', (e) => {
        vscode.postMessage({ command: 'update_code', code: e.target.value });
      });
    }

    const btnRunChallenge = document.getElementById('btn-run-challenge');
    if (btnRunChallenge) {
      btnRunChallenge.addEventListener('click', () => {
        showDuckThinking();
        vscode.postMessage({ command: 'run_challenge' });
      });
    }

    const btnRunAll = document.getElementById('btn-run-all');
    if (btnRunAll) {
      btnRunAll.addEventListener('click', () => {
        showDuckThinking();
        vscode.postMessage({ command: 'run_all' });
      });
    }

    const btnRequestHint = document.getElementById('btn-request-hint');
    if (btnRequestHint) {
      btnRequestHint.addEventListener('click', () => {
        showDuckThinking();
        vscode.postMessage({ command: 'request_hint' });
      });
    }

    const btnRevealSolution = document.getElementById('btn-reveal-solution');
    if (btnRevealSolution) {
      btnRevealSolution.addEventListener('click', () => {
        vscode.postMessage({ command: 'reveal_solution' });
      });
    }

    const btnGoToReflect = document.getElementById('btn-go-to-reflect');
    if (btnGoToReflect) {
      btnGoToReflect.addEventListener('click', () => {
        vscode.postMessage({ command: 'switch_stage', stage: 'reflect' });
      });
    }

    document.querySelectorAll('.transfer-choice-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const index = parseInt(btn.getAttribute('data-index'));
        vscode.postMessage({ command: 'submit_transfer', choiceIndex: index });
      });
    });

    document.querySelectorAll('.stage-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const stage = pill.getAttribute('data-stage');
        vscode.postMessage({ command: 'switch_stage', stage });
      });
    });

    const btnNotebookToggle = document.getElementById('btn-notebook-toggle');
    const btnCloseNotebook = document.getElementById('btn-close-notebook');
    const notebookDrawer = document.getElementById('notebook-drawer');

    if (btnNotebookToggle && notebookDrawer) {
      btnNotebookToggle.addEventListener('click', () => {
        notebookDrawer.style.display = notebookDrawer.style.display === 'none' ? 'block' : 'none';
      });
    }

    if (btnCloseNotebook && notebookDrawer) {
      btnCloseNotebook.addEventListener('click', () => {
        notebookDrawer.style.display = 'none';
      });
    }

    // Auto-scroll chat histories
    document.querySelectorAll('.duck-chat-history').forEach((box) => {
      box.scrollTop = box.scrollHeight;
    });
  </script>
</body>
</html>`;
}

function getLanguageInfo(language?: string, fileName?: string): { icon: string; name: string; isRunnable: boolean } {
  const lang = (language || '').toLowerCase();
  const ext = (fileName || '').split('.').pop()?.toLowerCase() || '';

  if (lang === 'python' || ext === 'py') {
    return { icon: '🐍', name: 'Python', isRunnable: true };
  }
  if (lang === 'javascript' || lang === 'javascriptreact' || ext === 'js' || ext === 'mjs' || ext === 'jsx') {
    return { icon: '🟨', name: 'JavaScript', isRunnable: true };
  }
  if (lang === 'typescript' || lang === 'typescriptreact' || ext === 'ts' || ext === 'tsx') {
    return { icon: '🔷', name: 'TypeScript', isRunnable: false };
  }
  if (lang === 'cpp' || lang === 'c' || ext === 'cpp' || ext === 'c' || ext === 'h') {
    return { icon: '⚙️', name: 'C/C++', isRunnable: false };
  }
  if (lang === 'java' || ext === 'java') {
    return { icon: '☕', name: 'Java', isRunnable: false };
  }
  if (lang === 'rust' || ext === 'rs') {
    return { icon: '🦀', name: 'Rust', isRunnable: false };
  }
  if (lang === 'go' || ext === 'go') {
    return { icon: '🐹', name: 'Go', isRunnable: false };
  }
  if (lang === 'html' || ext === 'html') {
    return { icon: '🌐', name: 'HTML', isRunnable: false };
  }
  if (lang === 'css' || ext === 'css') {
    return { icon: '🎨', name: 'CSS', isRunnable: false };
  }
  return { icon: '📄', name: language ? language.toUpperCase() : 'Code', isRunnable: false };
}

function renderCustomCodeChatView(session: Session | null): string {
  const code = session?.code || '';
  const lines = code ? code.split('\n').length : 0;
  const fileName = session?.title?.replace('Duck Debug: ', '') || 'active_file';
  const langInfo = getLanguageInfo(session?.language, fileName);
  const lastRun = session?.runs?.[session.runs.length - 1];

  let runResultHtml = '';
  if (lastRun) {
    if (lastRun.error) {
      runResultHtml = `
      <div class="card" style="border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.05); margin-bottom: 10px;">
        <div class="card-title">
          <span style="color: #fca5a5; display:flex; align-items:center; gap:5px;">💥 Traceback &amp; Error</span>
          <span class="badge-hash">${escapeHtml(lastRun.codeHash)}</span>
        </div>
        <div class="alert alert-error" style="margin-bottom: 0;">
          <pre style="white-space: pre-wrap; font-size: 0.79rem; margin: 0; font-family: var(--duck-mono);">${escapeHtml(lastRun.error)}</pre>
        </div>
        ${lastRun.stdout ? `<div style="font-size:0.72rem;color:var(--vscode-descriptionForeground);margin-top:6px;">stdout:</div><div class="code-window"><pre>${escapeHtml(lastRun.stdout)}</pre></div>` : ''}
      </div>`;
    } else {
      runResultHtml = `
      <div class="card" style="border-color: rgba(34, 197, 94, 0.35); background: rgba(34, 197, 94, 0.05); margin-bottom: 10px;">
        <div class="card-title">
          <span style="color: var(--duck-pass); display:flex; align-items:center; gap:5px;">✓ Executed Cleanly</span>
          <span class="badge-hash">${escapeHtml(lastRun.codeHash)}</span>
        </div>
        ${lastRun.stdout
          ? `<div style="font-size:0.72rem;color:var(--vscode-descriptionForeground);margin-bottom:4px;">Output:</div><div class="code-window"><pre>${escapeHtml(lastRun.stdout)}</pre></div>`
          : `<div style="font-size:0.8rem;color:var(--duck-pass);">The script executed without crashing (no output generated).</div>`}
      </div>`;
    }
  }

  const chips = [
    { label: '💡 What could break here?', text: 'What potential edge cases or assumptions could break in this code?' },
    { label: '🔍 Walk me through this', text: 'Can you walk me through what this logic is doing step by step?' },
    { label: '❓ What should this return?', text: 'What should this code return and why?' },
    { label: '🪄 Give me a hint', text: 'Can you give me a subtle Socratic hint on what to look for?' },
  ];

  const chipsHtml = chips.map(c =>
    `<button class="chip-btn duck-chip" data-text="${escapeHtml(c.text)}">${escapeHtml(c.label)}</button>`
  ).join('');

  return `
    <!-- Active Editor Code Preview -->
    <div class="card" style="margin-bottom: 10px;">
      <div class="card-title">
        <span style="display:flex; align-items:center; gap:6px;">
          <span>${langInfo.icon}</span> ${escapeHtml(fileName)}
          <span style="font-size:0.72rem; font-weight:400; color:var(--vscode-descriptionForeground);">(${lines} lines · ${langInfo.name})</span>
        </span>
        <button class="btn-secondary" id="btn-copy-code" style="padding: 2px 7px; font-size: 0.72rem;">📋 Copy</button>
      </div>

      <div class="code-window">
        <div class="code-window-bar">
          <div class="window-dots">
            <span class="window-dot dot-red"></span>
            <span class="window-dot dot-yellow"></span>
            <span class="window-dot dot-green"></span>
          </div>
          <span>${langInfo.name}</span>
        </div>
        <pre><code id="active-code-display">${escapeHtml(code || '// Open any code file in VS Code editor to start')}</code></pre>
      </div>

      <div style="display: flex; gap: 8px; margin-top: 8px;">
        ${langInfo.isRunnable ? `
          <button class="btn-primary" id="btn-run-diagnose" style="flex: 2;">
            <span>▶️</span> Run &amp; Ask Duck
          </button>
        ` : ''}
        <button class="${langInfo.isRunnable ? 'btn-secondary' : 'btn-primary'}" id="btn-review-code" style="flex: ${langInfo.isRunnable ? '2' : '3'};" title="Ask Duck to inspect your code logic Socratically">
          <span>🔍</span> Socratic Review
        </button>
        <button class="btn-secondary" id="btn-sync-editor" style="flex: 1;" title="Sync active file from editor">
          <span>🔄</span> Sync
        </button>
      </div>
    </div>

    <!-- Execution Status / Diagnostics -->
    ${runResultHtml}

    <!-- Socratic Chat Stream -->
    <div class="card">
      <div class="card-title">
        <span style="display:flex; align-items:center; gap:6px;">
          <span>🦆</span> Socratic Tutor
        </span>
        <span style="font-size: 0.72rem; color: var(--vscode-descriptionForeground);">
          ${session?.messages?.length ?? 0} messages
        </span>
      </div>

      <div class="duck-chat-history" style="max-height: 280px; overflow-y: auto;">
        ${(session?.messages ?? []).map(msg => renderChatMessage(msg)).join('')}

        <!-- Dynamic Typing Indicator -->
        <div id="duck-typing-indicator" class="duck-typing-indicator" style="display: none;">
          <span style="font-size: 0.95rem;">🦆</span>
          <div class="typing-dots">
            <span></span><span></span><span></span>
          </div>
          <span style="font-size: 0.74rem; color: var(--vscode-descriptionForeground); margin-left: 4px;">Duck is pondering your code...</span>
        </div>
      </div>

      <!-- Quick Chips -->
      <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;">
        ${chipsHtml}
      </div>

      <!-- Chat Input Capsule -->
      <div class="chat-input-capsule">
        <input type="text" id="duck-chat-input-field" placeholder="Ask Duck about your code... (Press Enter)" autocomplete="off">
        <button class="btn-capsule-send" id="btn-chat-send">🦆 Ask</button>
      </div>
      <div style="text-align: right; margin-top: 4px; font-size: 0.68rem; color: var(--vscode-descriptionForeground);">
        Socratic method · Guides without spoiling
      </div>
    </div>
  `;
}

function renderChatMessage(msg: { role: string; text: string; source?: string }): string {
  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';

  if (isSystem) {
    return `
      <div class="chat-bubble-container">
        <div class="chat-bubble system">
          ℹ️ ${escapeHtml(msg.text)}
        </div>
      </div>
    `;
  }

  const roleLabel = isUser ? '🧑‍💻 You' : `🦆 ${escapeHtml(msg.source || 'DuckTutor')}`;
  const formattedText = formatMarkdown(msg.text);

  return `
    <div class="chat-bubble-container ${isUser ? 'user' : 'assistant'}">
      <div class="chat-bubble-meta">
        ${roleLabel}
      </div>
      <div class="chat-bubble ${isUser ? 'user' : 'assistant'}">
        ${formattedText}
      </div>
    </div>
  `;
}

function formatMarkdown(text: string): string {
  if (!text) return '';
  let safe = escapeHtml(text);
  // Code blocks: ```python ... ``` or ``` ... ```
  safe = safe.replace(/```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)```/g, (_match, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });
  // Inline code: `...`
  safe = safe.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
  // Bold: **...**
  safe = safe.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  // Italic: *...*
  safe = safe.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  // Newlines
  safe = safe.replace(/\n/g, '<br>');
  return safe;
}

function renderExerciseStages(session: Session | null, currentExercise: Exercise | null): string {
  const stage = session?.stage || 'predict';
  const stages: Array<{ id: string; label: string }> = [
    { id: 'predict',     label: '1 · Predict' },
    { id: 'investigate', label: '2 · Investigate' },
    { id: 'guide',       label: '3 · Check' },
    { id: 'reflect',     label: '4 · Reflect' },
  ];

  const stageBar = `
    <div class="stage-bar">
      ${stages.map(s => `
        <div class="stage-pill ${stage === s.id ? 'active' : ''}" data-stage="${s.id}">${s.label}</div>
      `).join('')}
    </div>`;

  // PREDICT
  const predictHtml = `
    <div id="stage-predict" style="display:${stage === 'predict' ? 'block' : 'none'};">
      <div class="card">
        <div class="card-title">🎯 Predict the Output</div>
        ${currentExercise ? `
          <p style="font-size:0.82rem;margin-bottom:8px;">${escapeHtml(currentExercise.spec)}</p>
          <div class="code-window">
            <div class="code-window-bar"><span>Starter Snippet</span></div>
            <pre><code>${escapeHtml(currentExercise.starter)}</code></pre>
          </div>
          <p style="font-size:0.78rem;color:var(--vscode-descriptionForeground);margin:8px 0;">What do you think this code will output?</p>
          ${renderPredictionInput(session, currentExercise)}
          <div class="slider-container">
            <label style="font-size:0.78rem;font-weight:600;">Confidence: <span id="conf-val">${session?.confidence ?? 3}</span>/5</label>
            <input type="range" id="confidence-range" min="1" max="5" value="${session?.confidence ?? 3}">
            <div class="slider-labels"><span>Not sure</span><span>Certain</span></div>
          </div>
          <div style="margin-top:6px;">
            <label style="font-size:0.78rem;font-weight:600;display:block;margin-bottom:4px;">Your reasoning (optional):</label>
            <textarea id="explanation-text" rows="2" placeholder="Why do you think this?">${escapeHtml(session?.explanation || '')}</textarea>
          </div>
          <button class="btn-primary" id="btn-submit-prediction" style="margin-top:10px;">🚀 Lock In &amp; Run</button>
        ` : '<div style="font-size:0.8rem;color:var(--vscode-descriptionForeground);">Select an exercise above.</div>'}
      </div>
      ${renderDuckDialogue(session)}
    </div>`;

  // INVESTIGATE
  const investigateHtml = `
    <div id="stage-investigate" style="display:${stage === 'investigate' ? 'block' : 'none'};">
      <div class="card">
        <div class="card-title">🔍 Investigate the Evidence</div>
        ${renderInvestigationEvidence(session)}
      </div>
      <div class="card">
        <div class="card-title">🛠 Try a Fix</div>
        <p style="font-size:0.78rem;color:var(--vscode-descriptionForeground);margin-bottom:6px;">Edit the code below, then run the prediction test again.</p>
        <textarea id="editor-code" rows="8" style="font-family:var(--duck-mono);font-size:0.82rem;">${escapeHtml(session?.code || '')}</textarea>
        <div class="action-grid" style="margin-top:8px;">
          <button class="btn-secondary" id="btn-sync-code">⬇ Sync from Editor</button>
          <button class="btn-secondary" id="btn-open-editor">↗ Open in Editor</button>
          <button class="btn-primary" id="btn-run-challenge" style="grid-column:span 2;">▶ Re-run Prediction Test</button>
        </div>
      </div>
      ${renderDuckDialogue(session)}
    </div>`;

  // CHECK / GUIDE
  const checkHtml = `
    <div id="stage-guide" style="display:${stage === 'guide' ? 'block' : 'none'};">
      <div class="card">
        <div class="card-title">
          <span>✅ Run All Test Cases</span>
          <button class="btn-primary" id="btn-run-all" style="width:auto;padding:5px 12px;font-size:0.8rem;">▶ Run All</button>
        </div>
        ${renderTestCasesList(session, currentExercise)}
      </div>
      <div class="card">
        <div class="card-title">💬 Duck Analysis</div>
        <div class="action-grid">
          <button class="btn-secondary" id="btn-request-hint">🪄 Get a Hint</button>
          <button class="btn-secondary" id="btn-reveal-solution">👁 Reveal Fix</button>
          <button class="btn-primary" id="btn-go-to-reflect" style="grid-column:span 2;">📝 Go to Reflection →</button>
        </div>
      </div>
      ${renderDuckDialogue(session)}
    </div>`;

  // REFLECT
  const reflectHtml = `
    <div id="stage-reflect" style="display:${stage === 'reflect' ? 'block' : 'none'};">
      <div class="card">
        <div class="card-title">📝 Reflect &amp; Transfer</div>
        ${renderReflectionCard(session, currentExercise)}
      </div>
      ${renderDuckDialogue(session)}
    </div>`;

  return stageBar + predictHtml + investigateHtml + checkHtml + reflectHtml;
}

function renderPredictionInput(session: Session | null, currentExercise: Exercise | null): string {
  if (session?.isCustomCode || !currentExercise) {
    return `
      <div style="margin: 8px 0;">
        <label style="font-size: 0.78rem; font-weight: 600; display: block; margin-bottom: 4px;">Expected Output / Behavior:</label>
        <input type="text" id="custom-prediction-input" placeholder="e.g. Return [1, 2] without errors" value="${escapeHtml(session?.prediction || '')}">
      </div>
    `;
  }

  const choicesHtml = currentExercise.choices
    .map(
      (c) => `
    <button class="choice-btn ${session?.prediction === c ? 'selected' : ''}" data-choice="${escapeHtml(c)}">
      ${escapeHtml(c)}
    </button>
  `
    )
    .join('');

  return `<div class="choice-group">${choicesHtml}</div>`;
}

function renderInvestigationEvidence(session: Session | null): string {
  if (!session) {
    return '';
  }
  const lastRun = session.runs[session.runs.length - 1];
  if (!lastRun) {
    return `<div style="font-size: 0.8rem; color: var(--vscode-descriptionForeground);">No execution run recorded yet.</div>`;
  }

  let statusBadge = '';
  if (lastRun.status === 'runtime_error' || lastRun.status === 'runner_error') {
    statusBadge = `<span class="badge-fail">💥 Execution Exception</span>`;
  } else if (lastRun.caseId === 'prediction') {
    if (session.predictionMatchesExecution) {
      statusBadge = `<span class="badge-pass">🎯 Prediction Matched Execution</span>`;
    } else {
      statusBadge = `<span style="color: var(--duck-amber); font-weight: 600;">⚡ Prediction Differed from Execution</span>`;
    }
  } else {
    statusBadge = lastRun.passed
      ? `<span class="badge-pass">✓ Passed</span>`
      : `<span class="badge-fail">✕ Test Failed</span>`;
  }

  const isPrediction = lastRun.caseId === 'prediction';

  return `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span style="font-weight: 600; font-size: 0.85rem;">${escapeHtml(lastRun.title)}</span>
      ${statusBadge}
    </div>
    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--duck-border); border-radius: 6px; padding: 8px 10px; margin-bottom: 8px;">
      <div style="font-size: 0.82rem; margin: 3px 0;">
        <strong>Your Prediction:</strong> <code class="inline-code">${escapeHtml(String(session.prediction || 'None'))}</code>
        <span style="color: var(--vscode-descriptionForeground); margin-left: 6px;">(Confidence: ${session.confidence || 3}/5)</span>
      </div>
      <div style="font-size: 0.82rem; margin: 3px 0;">
        <strong>Actual Observed Output:</strong> <code class="inline-code" style="color: var(--duck-amber);">${escapeHtml(JSON.stringify(lastRun.actual))}</code>
      </div>
      ${isPrediction && !lastRun.error ? `
        <div style="font-size: 0.78rem; color: var(--vscode-descriptionForeground); margin-top: 6px;">
          ℹ️ The code executed without crashing. Notice how the actual result differs from what you predicted! That is the bug to investigate.
        </div>
      ` : ''}
    </div>
    ${lastRun.error ? `<div class="alert alert-error" style="margin-top: 6px;"><strong>Traceback/Error:</strong><br>${escapeHtml(lastRun.error)}</div>` : ''}
    ${lastRun.stdout ? `<div style="font-size: 0.75rem; color: var(--vscode-descriptionForeground);">Standard Output:</div><div class="code-window"><pre>${escapeHtml(lastRun.stdout)}</pre></div>` : ''}
  `;
}

function renderDuckDialogue(session: Session | null): string {
  if (!session) {
    return '';
  }

  return `
    <div class="card" style="margin-top: 10px;">
      <div class="card-title">
        <span style="display:flex; align-items:center; gap:6px;">
          <span>🦆</span> Socratic Dialogue with Duck
        </span>
        <span style="font-size: 0.72rem; color: var(--vscode-descriptionForeground);">${session.messages.length} messages</span>
      </div>
      <div class="duck-chat-history" style="max-height: 220px; overflow-y: auto;">
        ${session.messages.map((msg) => renderChatMessage(msg)).join('')}
      </div>
    </div>
  `;
}

function renderTestCasesList(session: Session | null, currentExercise: Exercise | null): string {
  if (!session || !currentExercise) {
    return '<div style="font-size: 0.8rem;">No cases defined.</div>';
  }

  const currentRuns = session.runs.filter((r) => r.codeHash === session.codeHash);

  return currentExercise.cases
    .map((c) => {
      const run = currentRuns.find((r) => r.caseId === c.id);
      let statusHtml = '<span style="color: var(--vscode-descriptionForeground);">Untested</span>';
      if (run) {
        statusHtml = run.passed
          ? '<span class="badge-pass">✓ Pass</span>'
          : '<span class="badge-fail">✕ Fail</span>';
      }
      return `
      <div class="test-case-row">
        <div>
          <div style="font-weight: 500;">${escapeHtml(c.title)}</div>
          <div style="font-size: 0.72rem; color: var(--vscode-descriptionForeground);">${escapeHtml(c.purpose)}</div>
        </div>
        <div>${statusHtml}</div>
      </div>
    `;
    })
    .join('');
}

function renderReflectionCard(session: Session | null, currentExercise: Exercise | null): string {
  const ref = currentExercise?.reflection;
  if (!ref) {
    return `<div>Reflection completed for this session!</div>`;
  }

  const isAnswered = session?.transferPrediction !== null;
  const isCorrect = session?.transferCorrect === true;

  const choicesHtml = ref.transferChoices
    .map((choice, idx) => {
      let extraClass = '';
      if (isAnswered) {
        if (idx === ref.correctChoiceIndex) {
          extraClass = 'selected';
        }
      }
      return `
      <button class="choice-btn transfer-choice-btn ${extraClass}" data-index="${idx}" ${isAnswered ? 'disabled' : ''}>
        ${escapeHtml(choice)}
      </button>
    `;
    })
    .join('');

  return `
    <p style="font-size: 0.85rem; margin-bottom: 6px;"><strong>${escapeHtml(ref.transferPrompt)}</strong></p>
    <div class="code-window">
      <pre><code>${escapeHtml(ref.transferSnippet)}</code></pre>
    </div>
    <div class="choice-group">${choicesHtml}</div>
    ${
      isAnswered
        ? `
      <div class="alert ${isCorrect ? 'alert-success' : 'alert-info'}" style="margin-top: 10px;">
        <strong>${isCorrect ? '🎯 Spot on!' : '💡 Conceptual Insight:'}</strong><br>
        ${escapeHtml(ref.explanation)}
      </div>
    `
        : ''
    }
  `;
}

function renderNotebookList(history: Session[]): string {
  if (history.length === 0) {
    return `<div style="font-size: 0.78rem; color: var(--vscode-descriptionForeground);">No sessions saved yet.</div>`;
  }
  return history
    .slice(-10)
    .reverse()
    .map(
      (s) => `
    <div class="history-item">
      <div>
        <div style="font-weight: 600;">${escapeHtml(s.title)}</div>
        <div style="font-size: 0.72rem; color: var(--vscode-descriptionForeground);">
          ${s.outcome === 'verified' ? '✓ Verified' : 'In Progress'} · ${new Date(s.startedAt).toLocaleDateString()}
        </div>
      </div>
      <span class="badge-hash">${s.codeHash}</span>
    </div>
  `
    )
    .join('');
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getNonce(): string {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
