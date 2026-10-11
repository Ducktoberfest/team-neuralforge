import * as vscode from 'vscode';
import { PythonRunner } from './runner';
import { TutorService } from './tutor';
import { DuckTutorViewProvider } from './webview/DuckTutorViewProvider';
import { EXERCISES } from './exercises';

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration('ducktutor');

  const pythonPath = config.get<string>('pythonPath', 'python');
  const apiKey = config.get<string>('apiKey', '') || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '';
  const model = config.get<string>('model', 'gemma-4-26b-a4b-it');
  const provider = config.get<'google' | 'ollama'>('provider', 'google');
  const ollamaUrl = config.get<string>('ollamaUrl', 'http://127.0.0.1:11434');

  const runner = new PythonRunner(pythonPath);
  const tutor = new TutorService(apiKey, model, provider, ollamaUrl);

  const providerView = new DuckTutorViewProvider(context, runner, tutor);

  // Register Webview View
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(DuckTutorViewProvider.viewType, providerView, {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );

  // Listen for config changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('ducktutor')) {
        const updatedConfig = vscode.workspace.getConfiguration('ducktutor');
        runner.setPythonPath(updatedConfig.get<string>('pythonPath', 'python'));
        tutor.updateConfig(
          updatedConfig.get<string>('apiKey', ''),
          updatedConfig.get<string>('model', 'gemma-4-26b-a4b-it'),
          updatedConfig.get<'google' | 'ollama'>('provider', 'google'),
          updatedConfig.get<string>('ollamaUrl', 'http://127.0.0.1:11434')
        );
      }
    })
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand('ducktutor.openPanel', () => {
      vscode.commands.executeCommand('workbench.view.extension.ducktutor-container');
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('ducktutor.startExercise', async () => {
      const items = Object.values(EXERCISES).map((ex) => ({
        label: `🦆 ${ex.title}`,
        description: ex.concept,
        detail: ex.spec,
        exerciseId: ex.id,
      }));

      const selected = await vscode.window.showQuickPick(items, {
        placeHolder: 'Select a DuckTutor debugging exercise',
      });

      if (selected) {
        await providerView.startExercise(selected.exerciseId);
        vscode.commands.executeCommand('workbench.view.extension.ducktutor-container');
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('ducktutor.debugActiveFile', async () => {
      await providerView.debugActiveEditorCode();
      vscode.commands.executeCommand('workbench.view.extension.ducktutor-container');
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('ducktutor.setApiKey', async () => {
      const key = await vscode.window.showInputBox({
        title: 'DuckTutor: Gemini / Gemma API Key',
        prompt: 'Enter your Google AI Studio API key (starts with AIza...)',
        password: true,
        ignoreFocusOut: true,
      });

      if (key !== undefined) {
        await vscode.workspace.getConfiguration('ducktutor').update('apiKey', key, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage('DuckTutor: API key successfully updated!');
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('ducktutor.resetSession', () => {
      providerView.resetSession();
      vscode.window.showInformationMessage('DuckTutor: Session reset.');
    })
  );

  // Status Bar item
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'ducktutor.openPanel';
  statusBarItem.text = '$(beaker) DuckTutor 🦆';
  statusBarItem.tooltip = 'Click to open DuckTutor Socratic Debugging Assistant';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);
}

export function deactivate() {}
