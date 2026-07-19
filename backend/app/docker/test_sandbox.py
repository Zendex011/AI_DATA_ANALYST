"""
Run this against a REAL Docker daemon before relying on SANDBOX_MODE=docker.

This was written and logic-tested with a MOCKED Docker client (there was
no Docker available in the environment it was built in) -- this script is
how you confirm it actually works for real, on your machine.

Usage:
    1. Build the image once:
       docker build -t ai-data-analyst-sandbox -f docker/sandbox.Dockerfile docker/
    2. Make sure Docker Desktop / the Docker daemon is running.
    3. From the backend/ directory:
       python ../docker/test_sandbox.py
"""

import base64
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("GEMINI_API_KEY", "dummy")  # not used by this script, just avoids the startup warning

from app.core.code_executor import run_python_code, CodeExecutionError
from app.core.chart_generator import run_chart_code, ChartExecutionError


def make_test_csv() -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as f:
        f.write("name,department,salary\n")
        f.write("Alice,Engineering,95000\n")
        f.write("Bob,Sales,65000\n")
        f.write("Carol,Engineering,105000\n")
    return path


def test_basic_execution(csv_path: str):
    print("[1/5] Basic code execution...")
    result = run_python_code("print(df['salary'].mean())", csv_path)
    assert "88333" in result["stdout"], f"Unexpected output: {result['stdout']}"
    print("      OK -- got:", result["stdout"].strip())


def test_structured_error(csv_path: str):
    print("[2/5] Structured error on bad code (Series/DataFrame mistake)...")
    try:
        run_python_code(
            "row = df.iloc[0]\nprint(row.select_dtypes(include='number'))", csv_path
        )
        raise AssertionError("Expected a CodeExecutionError, got none")
    except CodeExecutionError as e:
        assert e.error_type == "AttributeError", f"Expected AttributeError, got {e.error_type}"
        print("      OK -- correctly caught:", e.error_type, "|", e.error_message)


def test_network_is_blocked(csv_path: str):
    print("[3/5] Network access should be BLOCKED inside the sandbox...")
    code = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('http://example.com', timeout=3)\n"
        "    print('NETWORK_WAS_REACHABLE')\n"
        "except Exception as e:\n"
        "    print('NETWORK_BLOCKED:', type(e).__name__)\n"
    )
    result = run_python_code(code, csv_path)
    assert "NETWORK_WAS_REACHABLE" not in result["stdout"], (
        "SECURITY ISSUE: the sandbox has network access. Check network_disabled=True "
        "is actually being applied."
    )
    print("      OK -- network correctly blocked:", result["stdout"].strip())


def test_readonly_filesystem(csv_path: str):
    print("[4/5] Filesystem should be READ-ONLY outside mounted paths...")
    code = (
        "try:\n"
        "    with open('/sandbox/should_not_write.txt', 'w') as f:\n"
        "        f.write('test')\n"
        "    print('WRITE_SUCCEEDED')\n"
        "except Exception as e:\n"
        "    print('WRITE_BLOCKED:', type(e).__name__)\n"
    )
    result = run_python_code(code, csv_path)
    assert "WRITE_SUCCEEDED" not in result["stdout"], (
        "SECURITY ISSUE: the sandbox filesystem is writable outside mounted paths. "
        "Check read_only=True is actually being applied."
    )
    print("      OK -- filesystem correctly read-only:", result["stdout"].strip())


def test_chart_generation(csv_path: str):
    print("[5/5] Chart generation...")
    code = (
        "df.groupby('department')['salary'].mean().plot(kind='bar')\n"
        "plt.title('Average Salary by Department')\n"
        "plt.savefig(output_path)\n"
    )
    b64 = run_chart_code(code, csv_path)
    png_bytes = base64.b64decode(b64)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Output is not a valid PNG"
    print(f"      OK -- got a valid PNG ({len(png_bytes)} bytes)")


if __name__ == "__main__":
    csv_path = make_test_csv()
    try:
        test_basic_execution(csv_path)
        test_structured_error(csv_path)
        test_network_is_blocked(csv_path)
        test_readonly_filesystem(csv_path)
        test_chart_generation(csv_path)
        print()
        print("ALL SANDBOX CHECKS PASSED")
    except (CodeExecutionError, ChartExecutionError) as e:
        print()
        print(f"SANDBOX ERROR: {e.error_type}: {e.error_message}")
        if e.error_type in ("SandboxImageNotFound", "DockerUnavailable"):
            print()
            print("Fix: make sure Docker is running, then build the image:")
            print("  docker build -t ai-data-analyst-sandbox -f docker/sandbox.Dockerfile docker/")
        sys.exit(1)
    finally:
        os.remove(csv_path)