from langchain.tools import tool
from app.core.code_executor import run_python_code, CodeExecutionError


def execute_pandas_code(code: str, csv_path: str) -> dict:
    """
    Plain function (not an LLM-facing tool) used directly by the LangGraph
    orchestrator, so it can see structured success/failure info and decide
    whether to retry. Returns a dict, never raises.

    {"success": True, "stdout": "..."}
    {"success": False, "error_type": "...", "error_message": "..."}
    """
    try:
        result = run_python_code(code, csv_path)
        return {"success": True, "stdout": result["stdout"] or "(no output printed)"}
    except CodeExecutionError as e:
        return {
            "success": False,
            "error_type": e.error_type,
            "error_message": e.error_message,
        }


@tool
def run_python_analysis(code: str, csv_path: str) -> str:
    """
    Runs pandas code against the uploaded CSV and returns stdout.
    The code must use the variable `df`, which is already loaded from the CSV.
    Code should use print() to output any result it wants returned.

    Kept as a LangChain @tool (string in/out) for cases where an LLM needs
    to call this directly as a tool-call. The orchestrator itself uses
    execute_pandas_code() above instead, because it needs structured
    success/failure data to drive the retry logic.
    """
    result = execute_pandas_code(code, csv_path)
    if result["success"]:
        return result["stdout"]
    return f"Execution failed: {result['error_type']}: {result['error_message']}"
