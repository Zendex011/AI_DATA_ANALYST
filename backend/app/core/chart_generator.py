"""
Generates a chart from LLM-generated matplotlib code, in one of two modes
controlled by app.config.SANDBOX_MODE ("docker" or "subprocess") -- same
split and same reasoning as code_executor.py; see that file's docstring.

Both modes expose the identical run_chart_code(code, csv_path) -> str
(base64 PNG) interface and raise the same ChartExecutionError.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from app.config import MAX_CODE_EXEC_SECONDS, SANDBOX_MODE

_ERROR_MARKER = "__CHART_ERROR_JSON__"


class ChartExecutionError(Exception):
    def __init__(self, error_type: str, error_message: str):
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(f"{error_type}: {error_message}")


def run_chart_code(code: str, csv_path: str) -> str:
    """
    Runs matplotlib code against `df` (loaded from csv_path). The code is
    expected to call plt.savefig(output_path) -- `output_path` is already
    defined for it -- and must NOT call plt.show(). Returns the resulting
    PNG as a base64 string. Raises ChartExecutionError on any failure.
    """
    img_fd, output_path = tempfile.mkstemp(suffix=".png")
    os.close(img_fd)
    try:
        return run_chart_code_to_file(code, csv_path, output_path)
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def run_chart_code_to_file(code: str, csv_path: str, output_path: str) -> str:
    """
    Runs matplotlib code and writes the result to the given output_path.
    Returns the resulting PNG as a base64 string and leaves the file in place.
    """
    if SANDBOX_MODE == "docker":
        return _run_docker(code, csv_path, output_path)
    return _run_subprocess(code, csv_path, output_path)


# ---------------------------------------------------------------------------
# Docker mode
# ---------------------------------------------------------------------------

def _run_docker(code: str, csv_path: str, output_path: str) -> str:
    from app.core.docker_sandbox import run_in_sandbox, SandboxExecutionError

    output_name = os.path.basename(output_path)
    host_output_dir = os.path.dirname(output_path)
    wrapper = f"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.show = lambda *args, **kwargs: None
import json
import os
import sys

df = pd.read_csv("/sandbox/data.csv")
output_path = "/sandbox/output/{output_name}"
chart_path = output_path

try:
{_indent(code)}
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        if plt.get_fignums():
            plt.gcf().savefig(output_path)
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
            os.path.abspath(host_output_dir): {"bind": "/sandbox/output", "mode": "rw"},
        }
        try:
            run_in_sandbox(volumes)
        except SandboxExecutionError as e:
            if e.error_type == "ExecutionError":
                raise _extract_structured_error(e.error_message)
            raise ChartExecutionError(e.error_type, e.error_message)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ChartExecutionError(
                "NoChartProduced",
                "Code ran without error but never called plt.savefig(output_path)",
            )
        with open(output_path, "rb") as img:
            return base64.b64encode(img.read()).decode("utf-8")
    finally:
        os.remove(script_path)


# ---------------------------------------------------------------------------
# Subprocess mode (fallback -- see code_executor.py's docstring)
# ---------------------------------------------------------------------------

def _run_subprocess(code: str, csv_path: str, output_path: str) -> str:
    wrapper = f"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.show = lambda *args, **kwargs: None
import json
import os
import sys

df = pd.read_csv(r"{csv_path}")
output_path = r"{output_path}"
chart_path = output_path

try:
{_indent(code)}
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        if plt.get_fignums():
            plt.gcf().savefig(output_path)
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
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=MAX_CODE_EXEC_SECONDS,
        )
        if result.returncode != 0:
            combined = (result.stdout or "") + (result.stderr or "")
            raise _extract_structured_error(combined, stderr_fallback=result.stderr)


        
        print("OUTPUT EXISTS:", os.path.exists(output_path))
        print("OUTPUT SIZE:",
            os.path.getsize(output_path)
            if os.path.exists(output_path) else 0)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ChartExecutionError(
                "NoChartProduced",
                "Code ran without error but never called plt.savefig(output_path)",
            )

        with open(output_path, "rb") as img:
            return base64.b64encode(img.read()).decode("utf-8")

    except subprocess.TimeoutExpired:
        raise ChartExecutionError("TimeoutError", f"Chart generation exceeded {MAX_CODE_EXEC_SECONDS}s")
    finally:
        os.remove(script_path)


# ---------------------------------------------------------------------------
# Shared error-marker parsing (used by both modes)
# ---------------------------------------------------------------------------

def _extract_structured_error(output: str, stderr_fallback: str = "") -> ChartExecutionError:
    if _ERROR_MARKER in output:
        payload = output.split(_ERROR_MARKER, 1)[1].strip()
        try:
            data = json.loads(payload)
            return ChartExecutionError(
                error_type=data.get("error_type", "UnknownError"),
                error_message=data.get("error_message", "Unknown error"),
            )
        except json.JSONDecodeError:
            pass

    tail_source = stderr_fallback or output
    lines = tail_source.strip().splitlines()
    last_line = lines[-1] if lines else "Unknown chart generation failure"
    return ChartExecutionError(error_type="SyntaxError", error_message=last_line)


def _indent(code: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in code.splitlines())