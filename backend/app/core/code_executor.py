"""
Executes LLM-generated pandas code, in one of two modes controlled by
app.config.SANDBOX_MODE:

  "docker"     -- runs inside a locked-down, ephemeral container (see
                  docker_sandbox.py): no network, read-only fs, memory/cpu
                  limits, non-root user. This is the default and the mode
                  you want for anything beyond solo local testing.

  "subprocess" -- the Phase 1-4 behavior: a plain subprocess with only a
                  timeout. Zero setup (no Docker needed), but NOT safe for
                  untrusted/public use -- no network restriction, no
                  filesystem jail, no memory limit. Use only if Docker
                  isn't available to you yet.

Both modes expose the identical run_python_code(code, csv_path) -> dict
interface and raise the same CodeExecutionError, so nothing calling this
module needs to know or care which mode is active.
"""

import json
import os
import subprocess
import sys
import tempfile
from app.config import MAX_CODE_EXEC_SECONDS, SANDBOX_MODE

_ERROR_MARKER = "__EXEC_ERROR_JSON__"


class CodeExecutionError(Exception):
    def __init__(self, error_type: str, error_message: str):
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(f"{error_type}: {error_message}")


def run_python_code(code: str, csv_path: str) -> dict:
    """
    Returns: {"stdout": str} on success.
    Raises: CodeExecutionError on any failure (bad code, timeout, crash,
    or -- in docker mode -- Docker itself being unavailable).
    """
    if SANDBOX_MODE == "docker":
        return _run_docker(code, csv_path)
    return _run_subprocess(code, csv_path)


# ---------------------------------------------------------------------------
# Docker mode
# ---------------------------------------------------------------------------

def _run_docker(code: str, csv_path: str) -> dict:
    from app.core.docker_sandbox import run_in_sandbox, SandboxExecutionError

    wrapper = f"""
import pandas as pd
import json
import sys

df = pd.read_csv("/sandbox/data.csv")

try:
{_indent(code)}
except Exception as e:
    print("{_ERROR_MARKER}" + json.dumps({{
        "error_type": type(e).__name__,
        "error_message": str(e)
    }}))
    sys.exit(1)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper)
        script_path = f.name

    try:
        volumes = {
            os.path.abspath(script_path): {"bind": "/sandbox/script.py", "mode": "ro"},
            os.path.abspath(csv_path): {"bind": "/sandbox/data.csv", "mode": "ro"},
        }
        try:
            stdout = run_in_sandbox(volumes)
        except SandboxExecutionError as e:
            if e.error_type == "ExecutionError":
                raise _extract_structured_error(e.error_message)
            raise CodeExecutionError(e.error_type, e.error_message)

        return {"stdout": stdout}
    finally:
        os.remove(script_path)


# ---------------------------------------------------------------------------
# Subprocess mode (fallback -- see module docstring)
# ---------------------------------------------------------------------------

def _run_subprocess(code: str, csv_path: str) -> dict:
    wrapper = f"""
import pandas as pd
import json
import sys

df = pd.read_csv(r"{csv_path}")

try:
{_indent(code)}
except Exception as e:
    print("{_ERROR_MARKER}" + json.dumps({{
        "error_type": type(e).__name__,
        "error_message": str(e)
    }}))
    sys.exit(1)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=MAX_CODE_EXEC_SECONDS,
        )
        if result.returncode != 0:
            combined = (result.stdout or "") + (result.stderr or "")
            raise _extract_structured_error(combined, stderr_fallback=result.stderr)
        return {"stdout": result.stdout}
    except subprocess.TimeoutExpired:
        raise CodeExecutionError("TimeoutError", f"Execution exceeded {MAX_CODE_EXEC_SECONDS}s")
    finally:
        os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Shared error-marker parsing (used by both modes)
# ---------------------------------------------------------------------------

def _extract_structured_error(output: str, stderr_fallback: str = "") -> CodeExecutionError:
    """
    Tries to extract the structured error the wrapper script printed via
    _ERROR_MARKER. Falls back to the last line of stderr/output if the
    script crashed before its own try/except could run (e.g. a SyntaxError
    at parse time, before any Python inside the try block ever executes).
    """
    if _ERROR_MARKER in output:
        payload = output.split(_ERROR_MARKER, 1)[1].strip()
        try:
            data = json.loads(payload)
            return CodeExecutionError(
                error_type=data.get("error_type", "UnknownError"),
                error_message=data.get("error_message", "Unknown error"),
            )
        except json.JSONDecodeError:
            pass

    tail_source = stderr_fallback or output
    lines = tail_source.strip().splitlines()
    last_line = lines[-1] if lines else "Unknown execution failure"
    return CodeExecutionError(error_type="SyntaxError", error_message=last_line)


def _indent(code: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in code.splitlines())