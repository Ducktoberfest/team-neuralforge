import * as vscode from 'vscode';
import { Exercise, Session } from '../types';
import { EXERCISES, getExercise } from '../exercises';
import { PythonRunner } from '../runner';
import { TutorService } from '../tutor';
import {
  addSessionMessage,
  createCustomCodeSession,
  createExerciseSession,
  recordRunResult,
  updateSessionCode,
} from '../session';
import { getWebviewHtml } from './getWebviewHtml';

export class DuckTutorViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'ducktutor.mainView';

  private view?: vscode.WebviewView;
  private currentSession: Session | null = null;
  private notebookHistory: Session[] = [];
  private runner: PythonRunner;
  private tutor: TutorService;
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext, runner: PythonRunner, tutor: TutorService) {
    this.context = context;
    this.runner = runner;
    this.tutor = tutor;
    this.loadNotebookFromStorage();

    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor) {
      const fileName = activeEditor.document.fileName.split(/[\\/]/).pop() || 'script.py';
      this.currentSession = createCustomCodeSession(activeEditor.document.getText(), fileName);
    } else {
      this.currentSession = createCustomCodeSession('', 'my_code.py');
    }

    // Auto-sync when active editor switches
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && this.currentSession && this.currentSession.isCustomCode) {
        const fileName = editor.document.fileName.split(/[\\/]/).pop() || 'script.py';
        const text = editor.document.getText();
        if (text && text !== this.currentSession.code) {
          updateSessionCode(this.currentSession, text);
          this.currentSession.title = `Duck Debug: ${fileName}`;
          this.updateWebview();
        }
      }
    });
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.context.extensionUri],
    };

    this.updateWebview();

    webviewView.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
  }

  public async startExercise(exerciseId: string, forceReset = false) {
    if (!forceReset && this.currentSession && !this.currentSession.isCustomCode && this.currentSession.exerciseId === exerciseId) {
      return;
    }
    const ex = getExercise(exerciseId);
    this.currentSession = createExerciseSession(ex);
    this.saveNotebook();
    this.updateWebview();
    if (this.view) {
      this.view.show(true);
    }
  }

  public async debugActiveEditorCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage('No active editor file found to debug with DuckTutor.');
      return;
    }

    const selection = editor.selection;
    let code = '';
    if (selection && !selection.isEmpty) {
      code = editor.document.getText(selection);
    } else {
      code = editor.document.getText();
    }

    const fileName = editor.document.fileName.split(/[\\/]/).pop() || 'script.py';
    this.currentSession = createCustomCodeSession(code, fileName);
    this.updateWebview();
    if (this.view) {
      this.view.show(true);
    }
  }

  public resetSession() {
    if (this.currentSession && !this.currentSession.isCustomCode) {
      const ex = getExercise(this.currentSession.exerciseId);
      this.currentSession = createExerciseSession(ex);
    } else {
      this.currentSession = createExerciseSession(EXERCISES['basket']);
    }
    this.updateWebview();
  }

  private updateWebview() {
    if (this.view) {
      this.view.webview.html = getWebviewHtml(this.view.webview, this.currentSession, this.notebookHistory);
    }
  }

  private async handleMessage(message: any) {
    if (!this.currentSession) {
      return;
    }

    switch (message.command) {
      case 'select_exercise': {
        await this.startExercise(message.exerciseId);
        break;
      }

      case 'debug_active_editor': {
        await this.debugActiveEditorCode();
        break;
      }

      case 'switch_stage': {
        this.currentSession.stage = message.stage;
        this.updateWebview();
        break;
      }

      case 'update_code': {
        updateSessionCode(this.currentSession, message.code);
        break;
      }

      case 'open_in_editor': {
        const doc = await vscode.workspace.openTextDocument({
          content: this.currentSession.code,
          language: 'python',
        });
        await vscode.window.showTextDocument(doc, { preview: true });
        break;
      }

      case 'sync_code_from_editor': {
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
          const editorText = activeEditor.document.getText();
          const changed = updateSessionCode(this.currentSession, editorText);
          if (changed) {
            vscode.window.showInformationMessage('DuckTutor: Code synced from active editor!');
          }
        }
        this.updateWebview();
        break;
      }

      case 'submit_prediction': {
        await this.handleSubmitPrediction(message.prediction, message.confidence, message.explanation);
        break;
      }

      case 'run_challenge': {
        await this.handleRunChallenge();
        break;
      }

      case 'run_all': {
        await this.handleRunAll();
        break;
      }

      case 'request_hint': {
        await this.handleRequestHint();
        break;
      }

      case 'reveal_solution': {
        this.handleRevealSolution();
        break;
      }

      case 'submit_transfer': {
        this.handleSubmitTransfer(message.choiceIndex);
        break;
      }

      case 'send_chat': {
        await this.handleUserChat(message.text);
        break;
      }

      case 'run_and_diagnose': {
        await this.handleRunAndDiagnose();
        break;
      }

      case 'sync_active_editor': {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
          const fileName = editor.document.fileName.split(/[\\/]/).pop() || 'script.py';
          const text = editor.document.getText();
          updateSessionCode(this.currentSession, text);
          this.currentSession.title = `Duck Debug: ${fileName}`;
          addSessionMessage(this.currentSession, 'system', `Synced code from "${fileName}" (${text.split('\n').length} lines).`, 'System');
          this.updateWebview();
        } else {
          vscode.window.showInformationMessage('No active editor tab found to sync from.');
        }
        break;
      }
    }
  }

  private async handleRunAndDiagnose() {
    if (!this.currentSession) {
      return;
    }

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'DuckTutor: Running Python code and consulting Gemma 4...',
        cancellable: false,
      },
      async () => {
        const result = await this.runner.runCustomCode(this.currentSession!.code);
        recordRunResult(this.currentSession!, result);

        let errorOrOutput = '';
        let promptQuestion = '';

        if (result.status === 'runtime_error' || result.status === 'syntax_error') {
          errorOrOutput = `Error: ${result.error}\n${result.stdout || ''}`;
          promptQuestion = `My Python code threw this error when running: ${result.error}. Ask me a focused Socratic question about the line and root assumption without giving the code solution.`;
        } else {
          errorOrOutput = `Output:\n${result.stdout || '(No output produced)'}`;
          promptQuestion = `I ran the Python code and it printed:\n${result.stdout || '(None)'}. Ask me if this matches what I intended and what variable or logic I should examine next.`;
        }

        const reply = await this.tutor.askSocraticDuck(
          this.currentSession!.code,
          errorOrOutput,
          this.currentSession!.messages,
          promptQuestion
        );

        addSessionMessage(this.currentSession!, 'assistant', reply, 'DuckTutor 🦆');
        this.saveNotebook();
        this.updateWebview();
      }
    );
  }

  private async handleUserChat(text: string) {
    if (!this.currentSession || !text || !text.trim()) {
      return;
    }
    const userText = text.trim();
    addSessionMessage(this.currentSession, 'user', userText, 'Learner');
    this.updateWebview();

    let reply = '';
    try {
      if (this.currentSession.isCustomCode) {
        const lastRun = this.currentSession.runs[this.currentSession.runs.length - 1];
        const errorOrOutput = lastRun
          ? lastRun.error
            ? `Exception: ${lastRun.error}\n${lastRun.stdout || ''}`
            : `Output: ${lastRun.stdout || ''}`
          : '';
        reply = await this.tutor.askSocraticDuck(
          this.currentSession.code,
          errorOrOutput,
          this.currentSession.messages,
          userText
        );
      } else {
        const ex = getExercise(this.currentSession.exerciseId);
        if (this.tutor.hasApiKey()) {
          const decision = await this.tutor.decide(
            this.currentSession,
            ex,
            'user_question',
            ['ask_question'],
            ex ? ex.cases : []
          );
          reply = decision.message;
        } else {
          reply = this.tutor.getFallbackQuestion(this.currentSession, ex, userText);
        }
      }
    } catch {
      reply = this.tutor.generateOfflineSocraticProbe(this.currentSession.code, '', userText);
    }

    addSessionMessage(this.currentSession, 'assistant', reply, 'DuckTutor 🦆');
    this.saveNotebook();
    this.updateWebview();
  }

  private async handleSubmitPrediction(prediction: string, confidence: number, explanation: string) {
    if (!this.currentSession) {
      return;
    }

    this.currentSession.prediction = prediction;
    this.currentSession.confidence = confidence;
    this.currentSession.explanation = explanation;

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'DuckTutor: Executing test case and consulting Gemma...',
        cancellable: false,
      },
      async () => {
        const ex = !this.currentSession!.isCustomCode ? getExercise(this.currentSession!.exerciseId) : null;

        let runResult;
        if (ex) {
          runResult = await this.runner.runCase(ex, this.currentSession!.code, ex.prediction);
        } else {
          runResult = await this.runner.runCustomCode(this.currentSession!.code);
        }

        recordRunResult(this.currentSession!, runResult);

        // Check whether prediction matched actual execution
        const actualStr = JSON.stringify(runResult.actual);
        const matches = prediction ? actualStr.includes(prediction) || prediction.includes(actualStr) : false;
        this.currentSession!.predictionMatchesExecution = matches;

        // Ask Gemma Socratic question
        const decision = await this.tutor.decide(
          this.currentSession!,
          ex,
          'prediction_completed',
          ['ask_question'],
          ex ? ex.cases : []
        );

        addSessionMessage(this.currentSession!, 'assistant', decision.message, 'DuckTutor 🦆');
        this.currentSession!.stage = 'investigate';
        this.saveNotebook();
        this.updateWebview();
      }
    );
  }

  private async handleRunChallenge() {
    if (!this.currentSession) {
      return;
    }
    const ex = !this.currentSession.isCustomCode ? getExercise(this.currentSession.exerciseId) : null;

    if (!ex) {
      // Custom code run
      const result = await this.runner.runCustomCode(this.currentSession.code);
      recordRunResult(this.currentSession, result);
      this.updateWebview();
      return;
    }

    // Gemma picks a target case or we select the first unverified case
    const pastRunCaseIds = this.currentSession.runs.filter((r) => r.codeHash === this.currentSession!.codeHash).map((r) => r.caseId);
    const candidateCases = ex.cases.filter((c) => !pastRunCaseIds.includes(c.id));
    const targetCase = candidateCases.length > 0 ? candidateCases[0] : ex.cases[0];

    const result = await this.runner.runCase(ex, this.currentSession.code, targetCase);
    recordRunResult(this.currentSession, result);

    const decision = await this.tutor.decide(
      this.currentSession,
      ex,
      'challenge_run',
      ['ask_question'],
      ex.cases
    );

    addSessionMessage(this.currentSession, 'assistant', decision.message, 'DuckTutor 🦆');
    this.updateWebview();
  }

  private async handleRunAll() {
    if (!this.currentSession) {
      return;
    }
    const ex = !this.currentSession.isCustomCode ? getExercise(this.currentSession.exerciseId) : null;
    if (!ex) {
      return;
    }

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'DuckTutor: Running full verification test suite...',
        cancellable: false,
      },
      async () => {
        let allPassed = true;
        for (const testCase of ex.cases) {
          const res = await this.runner.runCase(ex, this.currentSession!.code, testCase);
          recordRunResult(this.currentSession!, res);
          if (!res.passed) {
            allPassed = false;
          }
        }

        if (allPassed) {
          this.currentSession!.verifiedHash = this.currentSession!.codeHash;
          this.currentSession!.outcome = 'verified';
          addSessionMessage(
            this.currentSession!,
            'assistant',
            `Quack! All ${ex.cases.length} test cases passed for revision ${this.currentSession!.codeHash}! Proceed to the Transfer Reflection to complete this exercise.`,
            'DuckTutor 🦆'
          );
        } else {
          this.currentSession!.verifiedHash = null;
          addSessionMessage(
            this.currentSession!,
            'assistant',
            'Some test cases did not pass on this revision. Review the failing case and investigate your assumptions.',
            'DuckTutor 🦆'
          );
        }

        this.saveNotebook();
        this.updateWebview();
      }
    );
  }

  private async handleRequestHint() {
    if (!this.currentSession) {
      return;
    }
    const ex = !this.currentSession.isCustomCode ? getExercise(this.currentSession.exerciseId) : null;
    this.currentSession.hintLevel = Math.min((this.currentSession.hintLevel || 0) + 1, 3);

    const hintText = ex?.hints?.[this.currentSession.hintLevel - 1] ||
      this.tutor.getFallbackQuestion(this.currentSession, ex);

    addSessionMessage(
      this.currentSession,
      'assistant',
      `💡 Hint (Level ${this.currentSession.hintLevel}): ${hintText}`,
      'DuckTutor 🦆'
    );

    this.updateWebview();
  }

  private handleRevealSolution() {
    if (!this.currentSession) {
      return;
    }
    const ex = !this.currentSession.isCustomCode ? getExercise(this.currentSession.exerciseId) : null;
    if (!ex) {
      return;
    }

    this.currentSession.solutionViewed = true;
    this.currentSession.outcome = 'solution_revealed';

    addSessionMessage(
      this.currentSession,
      'assistant',
      `Reference Solution:\n\n${ex.solution}\n\nExplanation: ${ex.explanation}`,
      'DuckTutor (Solution Revealed)'
    );

    this.saveNotebook();
    this.updateWebview();
  }

  private handleSubmitTransfer(choiceIndex: number) {
    if (!this.currentSession) {
      return;
    }
    const ex = !this.currentSession.isCustomCode ? getExercise(this.currentSession.exerciseId) : null;
    if (!ex || !ex.reflection) {
      return;
    }

    this.currentSession.transferPrediction = choiceIndex;
    this.currentSession.transferCorrect = choiceIndex === ex.reflection.correctChoiceIndex;

    this.saveNotebook();
    this.updateWebview();
  }

  private saveNotebook() {
    if (!this.currentSession) {
      return;
    }
    const existingIdx = this.notebookHistory.findIndex((s) => s.id === this.currentSession!.id);
    if (existingIdx >= 0) {
      this.notebookHistory[existingIdx] = { ...this.currentSession };
    } else {
      this.notebookHistory.push({ ...this.currentSession });
    }
    this.context.globalState.update('ducktutor.notebook', this.notebookHistory);
  }

  private loadNotebookFromStorage() {
    const saved = this.context.globalState.get<Session[]>('ducktutor.notebook', []);
    this.notebookHistory = saved;
  }
}
