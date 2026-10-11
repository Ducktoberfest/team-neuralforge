"""Bounded execution with explicit trusted-local opt-in or Docker isolation."""
import ast
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid


def revision(code):
    return hashlib.sha256(code.encode()).hexdigest()[:12]


class Runner:
    def __init__(self, mode="docker", allow_trusted=False, timeout=4):
        self.mode = mode
        self.allow_trusted = allow_trusted
        self.timeout = timeout

    def run(self, exercise, code, case_id):
        case = exercise.case(case_id)
        start = time.monotonic()
        result = {"id": uuid.uuid4().hex[:12], "case_id": case_id,
                  "title": case.title, "code_hash": revision(code), "expected": case.expected,
                  "status": "runner_error", "passed": False, "actual": None,
                  "runner": self.mode}
        try:
            if len(code.encode()) > 20000:
                raise ValueError("Keep this exercise under 20 KiB of Python.")
            try:
                ast.parse(code)
            except SyntaxError as exc:
                result.update(status="syntax_error", error=f"Line {exc.lineno}: {exc.msg}")
                return result
            if self.mode == "trusted-local" and not self.allow_trusted:
                raise ValueError("Enable the trusted-code checkbox before using the local demo runner.")
            if self.mode not in {"trusted-local", "docker"}:
                raise ValueError("Unknown execution mode.")
            if self.mode == "docker" and not shutil.which("docker"):
                raise ValueError("Docker is not installed. Set up Docker or explicitly select trusted local demo mode.")
            with tempfile.TemporaryDirectory(prefix="ducktutor-") as folder:
                worker = Path(folder) / "worker.py"
                shutil.copyfile(Path(__file__).with_name("worker.py"), worker)
                payload = json.dumps({"code": code, "entrypoint": exercise.entrypoint,
                                      "script": case.script}).encode()
                container = "ducktutor-" + uuid.uuid4().hex
                if self.mode == "docker":
                    cmd = ["docker", "run", "--rm", "-i", "--pull=never", "--name", container,
                           "--network=none", "--read-only", "--cap-drop=ALL",
                           "--security-opt=no-new-privileges", "--user=65534:65534",
                           "--memory=256m", "--cpus=1", "--pids-limit=32",
                           "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--workdir=/tmp",
                           "--mount", f"type=bind,source={folder},target=/input,readonly",
                           os.environ.get("RUNNER_IMAGE", "python:3.12-slim"),
                           "python", "-I", "-B", "/input/worker.py"]
                    # Other users inside the container must be able to read the input.
                    os.chmod(folder, 0o755)
                    os.chmod(worker, 0o644)
                    env = os.environ.copy()  # docker CLI only; no -e flags forward it.
                else:
                    cmd = [sys.executable, "-I", "-B", str(worker)]
                    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": folder,
                           "TMPDIR": folder, "PYTHONIOENCODING": "utf-8"}
                    if "SYSTEMROOT" in os.environ:
                        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, cwd=folder, env=env,
                                        start_new_session=(os.name == "posix"))
                try:
                    try:
                        proc.stdin.write(payload)
                        proc.stdin.close()
                    except BrokenPipeError:
                        pass
                    raw = bytearray()
                    with selectors.DefaultSelector() as sel:
                        sel.register(proc.stdout, selectors.EVENT_READ)
                        deadline = time.monotonic() + (10 if self.mode == "docker" else self.timeout)
                        while sel.get_map():
                            if time.monotonic() > deadline:
                                result.update(status="timeout", error="Execution exceeded the time limit.")
                                return result
                            for key, _ in sel.select(0.05):
                                chunk = os.read(key.fd, 8192)
                                if not chunk:
                                    sel.unregister(key.fileobj)
                                    continue
                                raw.extend(chunk)
                                if len(raw) > 65536:
                                    result.update(status="output_limit", error="Output exceeded 64 KiB.")
                                    return result
                    proc.wait(timeout=1)
                    if proc.returncode:
                        if self.mode == "docker":
                            error = "Container failed to start or execute. Check Docker and the pre-pulled image."
                            status = "runner_error"
                        else:
                            error = "Execution stopped (process error or resource limit)."
                            status = "execution_error"
                        result.update(status=status, error=error)
                        return result
                    try:
                        child = json.loads(raw.decode())
                    except (ValueError, UnicodeError):
                        result.update(status="execution_error", error="Execution did not return a valid result.")
                        return result
                    result.update(child)
                    if child["status"] == "completed":
                        result["passed"] = child["actual"] == case.expected
                finally:
                    if os.name == "posix":
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    elif proc.poll() is None:
                        proc.kill()
                    proc.wait(timeout=2)
                    proc.stdout.close()
                    if self.mode == "docker":
                        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=4)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result.update(status="runner_error", error=str(exc)[:250])
        finally:
            result["duration_ms"] = round((time.monotonic() - start) * 1000)
        return result

    def run_custom(self, code, script="", entrypoint=None):
        start = time.monotonic()
        code_rev = revision(code)
        result = {"id": uuid.uuid4().hex[:12], "case_id": "custom_run",
                  "title": "Custom execution", "code_hash": code_rev, "expected": None,
                  "status": "runner_error", "passed": False, "actual": None,
                  "runner": self.mode}
        try:
            if len(code.encode()) > 20000:
                raise ValueError("Keep your code under 20 KiB of Python.")
            try:
                ast.parse(code)
            except SyntaxError as exc:
                result.update(status="syntax_error", error=f"Line {exc.lineno}: {exc.msg}")
                return result
            if self.mode == "trusted-local" and not self.allow_trusted:
                raise ValueError("Enable the trusted-code checkbox before using the local demo runner.")
            if self.mode not in {"trusted-local", "docker"}:
                raise ValueError("Unknown execution mode.")
            if self.mode == "docker" and not shutil.which("docker"):
                raise ValueError("Docker is not installed. Set up Docker or explicitly select trusted local demo mode.")
            with tempfile.TemporaryDirectory(prefix="ducktutor-") as folder:
                worker = Path(folder) / "worker.py"
                shutil.copyfile(Path(__file__).with_name("worker.py"), worker)
                payload = json.dumps({"code": code, "entrypoint": entrypoint,
                                      "script": script}).encode()
                container = "ducktutor-" + uuid.uuid4().hex
                if self.mode == "docker":
                    cmd = ["docker", "run", "--rm", "-i", "--pull=never", "--name", container,
                           "--network=none", "--read-only", "--cap-drop=ALL",
                           "--security-opt=no-new-privileges", "--user=65534:65534",
                           "--memory=256m", "--cpus=1", "--pids-limit=32",
                           "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--workdir=/tmp",
                           "--mount", f"type=bind,source={folder},target=/input,readonly",
                           os.environ.get("RUNNER_IMAGE", "python:3.12-slim"),
                           "python", "-I", "-B", "/input/worker.py"]
                    os.chmod(folder, 0o755)
                    os.chmod(worker, 0o644)
                    env = os.environ.copy()
                else:
                    cmd = [sys.executable, "-I", "-B", str(worker)]
                    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": folder,
                           "TMPDIR": folder, "PYTHONIOENCODING": "utf-8"}
                    if "SYSTEMROOT" in os.environ:
                        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, cwd=folder, env=env,
                                        start_new_session=(os.name == "posix"))
                try:
                    try:
                        proc.stdin.write(payload)
                        proc.stdin.close()
                    except BrokenPipeError:
                        pass
                    raw = bytearray()
                    with selectors.DefaultSelector() as sel:
                        sel.register(proc.stdout, selectors.EVENT_READ)
                        deadline = time.monotonic() + (10 if self.mode == "docker" else self.timeout)
                        while sel.get_map():
                            if time.monotonic() > deadline:
                                result.update(status="timeout", error="Execution exceeded the time limit.")
                                return result
                            for key, _ in sel.select(0.05):
                                chunk = os.read(key.fd, 8192)
                                if not chunk:
                                    sel.unregister(key.fileobj)
                                    continue
                                raw.extend(chunk)
                                if len(raw) > 65536:
                                    result.update(status="output_limit", error="Output exceeded 64 KiB.")
                                    return result
                    proc.wait(timeout=1)
                    if proc.returncode:
                        if self.mode == "docker":
                            error = "Container failed to start or execute. Check Docker and the pre-pulled image."
                            status = "runner_error"
                        else:
                            error = "Execution stopped (process error or resource limit)."
                            status = "execution_error"
                        result.update(status=status, error=error)
                        return result
                    try:
                        child = json.loads(raw.decode())
                    except (ValueError, UnicodeError):
                        result.update(status="execution_error", error="Execution did not return a valid result.")
                        return result
                    result.update(child)
                    if child.get("status") == "completed":
                        result["passed"] = True
                finally:
                    if os.name == "posix":
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    elif proc.poll() is None:
                        proc.kill()
                    proc.wait(timeout=2)
                    proc.stdout.close()
                    if self.mode == "docker":
                        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=4)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result.update(status="runner_error", error=str(exc)[:250])
        finally:
            result["duration_ms"] = round((time.monotonic() - start) * 1000)
        return result
