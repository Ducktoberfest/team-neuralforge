"""Child process harness. A process boundary alone is NOT a security sandbox."""
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
    payload = json.load(sys.stdin)
    output = BoundedOutput()
    result = {}
    try:
        # Best-effort resource bounds, not a defense against hostile Python.
        if sys.platform != "win32":
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
            if sys.platform == "linux":
                resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            namespace = {"__name__": "__submission__"}
            exec(compile(payload["code"], "submission.py", "exec"), namespace)
            scope = {"fn": namespace[payload["entrypoint"]]}
            exec(compile(payload["script"], "checked_case.py", "exec"), scope)
            value = scope["actual"]
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            if len(encoded) > 16384:
                raise ValueError("Result exceeds 16 KiB")
            result = {"status": "completed", "actual": value}
    except BaseException as exc:
        result = {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                  "traceback": traceback.format_exc(limit=3)[-2000:]}
    result.update(stdout=output.text, output_truncated=output.truncated)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
