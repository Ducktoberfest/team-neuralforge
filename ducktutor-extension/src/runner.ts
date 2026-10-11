import * as cp from 'child_process';
import * as crypto from 'crypto';
import { Case, Exercise, RunResult } from './types';

export function revision(code: string): string {
  return crypto.createHash('sha256').update(code).digest('hex').substring(0, 12);
}

function deepEqual(a: any, b: any): boolean {
  if (a === b) {
    return true;
  }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') {
    return false;
  }
  if (Array.isArray(a) !== Array.isArray(b)) {
    return false;
  }
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) {
    return false;
  }
  for (const key of keysA) {
    if (!keysB.includes(key) || !deepEqual(a[key], b[key])) {
      return false;
    }
  }
  return true;
}

const WORKER_PYTHON_SCRIPT = `
import contextlib
import io
import json
import sys
import traceback

class BoundedOutput(io.TextIOBase):
    def __init__(self):
        self.text = ""
        self.truncated = False

    def write(self, value):
        remaining = 4096 - len(self.text)
        self.text += value[:max(0, remaining)]
        self.truncated |= len(value) > remaining
        return len(value)

    def flush(self):
        pass

def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stdout.write(json.dumps({"status": "runner_error", "error": f"Invalid payload: {exc}", "actual": None}))
        return

    output = BoundedOutput()
    result = {}
    try:
        if sys.platform != "win32":
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
                resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
            except Exception:
                pass
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            namespace = {"__name__": "__submission__"}
            exec(compile(payload["code"], "submission.py", "exec"), namespace)
            if payload.get("custom_run"):
                result = {"status": "completed", "actual": output.text.strip()}
            else:
                entry = payload.get("entrypoint")
                if entry not in namespace:
                    raise NameError(f"Entrypoint '{entry}' was not defined in code.")
                scope = {"fn": namespace[entry]}
                exec(compile(payload["script"], "checked_case.py", "exec"), scope)
                value = scope.get("actual")
                encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
                if len(encoded) > 16384:
                    raise ValueError("Result exceeds 16 KiB")
                result = {"status": "completed", "actual": value}
    except BaseException as exc:
        result = {
            "status": "runtime_error",
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "traceback": traceback.format_exc(limit=3)[-2000:],
            "actual": None
        }
    result.update(stdout=output.text, output_truncated=output.truncated)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, allow_nan=False))

if __name__ == "__main__":
    main()
`;

export class PythonRunner {
  private pythonPath: string;
  private timeoutSeconds: number;

  constructor(pythonPath = 'python', timeoutSeconds = 5) {
    this.pythonPath = pythonPath;
    this.timeoutSeconds = timeoutSeconds;
  }

  public setPythonPath(path: string) {
    this.pythonPath = path;
  }

  public async runCase(exercise: Exercise, code: string, caseItem: Case): Promise<RunResult> {
    const runId = crypto.randomBytes(6).toString('hex');
    const codeHash = revision(code);
    const startTime = Date.now();

    if (code.length > 20000) {
      return {
        id: runId,
        caseId: caseItem.id,
        title: caseItem.title,
        codeHash,
        expected: caseItem.expected,
        actual: null,
        passed: false,
        status: 'syntax_error',
        error: 'Code length exceeds 20 KiB limit.',
        durationMs: 0,
      };
    }

    const payload = JSON.stringify({
      code,
      entrypoint: exercise.entrypoint,
      script: caseItem.script,
      custom_run: false,
    });

    return this.executeHarness(payload, caseItem, codeHash, runId, startTime);
  }

  public async runCustomCode(code: string, scriptTitle = 'Active Python Execution'): Promise<RunResult> {
    const runId = crypto.randomBytes(6).toString('hex');
    const codeHash = revision(code);
    const startTime = Date.now();

    const payload = JSON.stringify({
      code,
      custom_run: true,
    });

    const dummyCase: Case = {
      id: 'custom_run',
      title: scriptTitle,
      purpose: 'Execute active user code',
      script: '',
      expected: null,
    };

    return this.executeHarness(payload, dummyCase, codeHash, runId, startTime);
  }

  private executeHarness(
    payload: string,
    caseItem: Case,
    codeHash: string,
    runId: string,
    startTime: number
  ): Promise<RunResult> {
    return new Promise<RunResult>((resolve) => {
      const child = cp.spawn(this.pythonPath, ['-I', '-B', '-c', WORKER_PYTHON_SCRIPT], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      });

      let stdout = '';
      let stderr = '';
      let isTimedOut = false;

      const timer = setTimeout(() => {
        isTimedOut = true;
        child.kill();
        resolve({
          id: runId,
          caseId: caseItem.id,
          title: caseItem.title,
          codeHash,
          expected: caseItem.expected,
          actual: null,
          passed: false,
          status: 'timeout',
          error: `Execution timed out after ${this.timeoutSeconds}s. Check for infinite loops or recursion.`,
          durationMs: Date.now() - startTime,
        });
      }, this.timeoutSeconds * 1000);

      child.stdout.on('data', (data) => {
        stdout += data.toString('utf-8');
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString('utf-8');
      });

      child.on('error', (err: any) => {
        clearTimeout(timer);
        if (err && err.code === 'ENOENT' && this.pythonPath === 'python') {
          // Automatic macOS / Linux fallback: if 'python' does not exist, try 'python3'
          this.pythonPath = 'python3';
          this.executeHarness(payload, caseItem, codeHash, runId, startTime).then(resolve);
          return;
        }
        resolve({
          id: runId,
          caseId: caseItem.id,
          title: caseItem.title,
          codeHash,
          expected: caseItem.expected,
          actual: null,
          passed: false,
          status: 'runner_error',
          error: `Could not launch Python (${this.pythonPath}): ${err.message}. Please configure pythonPath in settings.`,
          durationMs: Date.now() - startTime,
        });
      });

      child.on('close', () => {
        clearTimeout(timer);
        if (isTimedOut) {
          return;
        }

        const durationMs = Date.now() - startTime;
        try {
          const parsed = JSON.parse(stdout);
          const actual = parsed.actual;
          let passed = false;

          if (parsed.status === 'completed') {
            if (caseItem.id === 'custom_run') {
              passed = true;
            } else {
              passed = deepEqual(actual, caseItem.expected);
            }
          }

          resolve({
            id: runId,
            caseId: caseItem.id,
            title: caseItem.title,
            codeHash,
            expected: caseItem.expected,
            actual,
            passed,
            status: parsed.status === 'completed' ? 'completed' : 'runtime_error',
            error: parsed.error,
            stdout: parsed.stdout || stderr,
            durationMs,
          });
        } catch {
          resolve({
            id: runId,
            caseId: caseItem.id,
            title: caseItem.title,
            codeHash,
            expected: caseItem.expected,
            actual: null,
            passed: false,
            status: 'runner_error',
            error: stdout.slice(0, 500) || stderr.slice(0, 500) || 'Unknown process error',
            stdout,
            durationMs,
          });
        }
      });

      child.stdin.write(payload);
      child.stdin.end();
    });
  }
}
