import os
import tempfile
import pandas as pd
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.core.llm import get_llm
from app.core.sql_executor import run_sql_query, SQLExecutionError
from app.core.chart_generator import run_chart_code, ChartExecutionError
from app.config import GEMINI_MAX_OUTPUT_TOKENS_CODE, GEMINI_MAX_OUTPUT_TOKENS_TEXT

MAX_RETRIES = 1

SQL_RULES = """
Rules for the SQL you write:
- Only write a single SELECT statement (or a WITH ... SELECT CTE). Never
  write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or anything
  that modifies data or schema -- these are rejected before they ever reach
  the database, and the connection is expected to be read-only regardless.
- Use the EXACT table and column names given in the schema below. Do not
  guess or invent a name -- if it isn't listed, it doesn't exist.
- Only compute things derivable from the data with SQL. Do not add
  commentary or guesses about what a table represents -- that belongs in a
  separate step, not in the query itself.
- Include a LIMIT unless the question clearly needs every row (e.g. an
  aggregate like COUNT or AVG). Results are capped server-side regardless,
  but write the query as if that cap didn't exist.
- Return ONLY the SQL. No explanation, no markdown fences, no comments.
"""


class SQLAgentState(TypedDict):
    question: str
    connection_string: str
    schema_summary: str
    generated_sql: str
    columns: list
    rows: list
    row_count: int
    truncated: bool
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    retry_count: int
    final_answer: str
    include_chart: bool
    chart_generated: bool
    chart_base64: Optional[str]
    chart_error: Optional[str]
    wants_chart: bool
    gemini_api_key: Optional[str]


def plan_sql_node(state: SQLAgentState) -> SQLAgentState:
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))
    prompt = f"""You are a data analyst. A user connected a database and asked:
"{state['question']}"

Database schema:
{state['schema_summary']}

Write a SQL query that answers this question.
{SQL_RULES}
"""
    response = llm.invoke(prompt)
    state["generated_sql"] = _strip_code_fences(response.content)
    state["retry_count"] = 0
    return state


def execute_sql_node(state: SQLAgentState) -> SQLAgentState:
    try:
        result = run_sql_query(state["connection_string"], state["generated_sql"])
        state["success"] = True
        state["columns"] = result["columns"]
        state["rows"] = result["rows"]
        state["row_count"] = result["row_count"]
        state["truncated"] = result["truncated"]
        state["error_type"] = None
        state["error_message"] = None
    except SQLExecutionError as e:
        state["success"] = False
        state["columns"] = []
        state["rows"] = []
        state["row_count"] = 0
        state["truncated"] = False
        state["error_type"] = e.error_type
        state["error_message"] = e.error_message
    return state


def fix_sql_node(state: SQLAgentState) -> SQLAgentState:
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))
    prompt = f"""The following SQL query failed.

Original question: "{state['question']}"

Database schema:
{state['schema_summary']}

Query that failed:
{state['generated_sql']}

Error type: {state['error_type']}
Error message: {state['error_message']}

Fix the query so it runs correctly and answers the original question.
{SQL_RULES}
"""
    response = llm.invoke(prompt)
    state["generated_sql"] = _strip_code_fences(response.content)
    state["retry_count"] += 1
    return state


def interpret_sql_node(state: SQLAgentState) -> SQLAgentState:
    if not state["success"]:
        state["final_answer"] = (
            "The query failed and could not be completed automatically. "
            f"Error type: {state['error_type']}. "
            f"Details: {state['error_message']}"
        )
        return state

    llm = get_llm(temperature=0.3, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_TEXT, api_key=state.get("gemini_api_key"))
    preview = _rows_preview(state["columns"], state["rows"])
    truncated_note = " (truncated -- more rows exist)" if state["truncated"] else ""
    prompt = f"""Question asked: {state['question']}
SQL that was run: {state['generated_sql']}
Result columns: {state['columns']}
Result preview (up to 20 rows):
{preview}
Total rows returned: {state['row_count']}{truncated_note}

Explain the result in plain, direct English. If the question also asked
something the query couldn't answer (e.g. what a table represents), use
the schema and your own general knowledge for that part, and say clearly
that it's an inference, not something read from the data.
"""
    response = llm.invoke(prompt)
    state["final_answer"] = _finalize_answer(response)
    return state


def decide_chart_node(state: SQLAgentState) -> SQLAgentState:
    llm = get_llm(temperature=0, max_output_tokens=10, api_key=state.get("gemini_api_key"))
    prompt = f"""Question: {state['question']}
Answer given: {state['final_answer']}

Would a chart meaningfully help visualize this result? A single number
generally does NOT need one. A comparison across categories, a trend, or
a distribution generally DOES.

Reply with exactly one word: YES or NO.
"""
    response = llm.invoke(prompt)
    state["wants_chart"] = response.content.strip().upper().startswith("Y")
    return state


def generate_chart_node(state: SQLAgentState) -> SQLAgentState:
    """
    There's no CSV file to point the chart executor at here -- the data is
    the (already row-capped) query result. So it's written to a temp CSV
    and the same chart_generator.run_chart_code() used by the CSV path is
    reused as-is, rather than duplicating chart-execution logic.
    """
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))
    prompt = f"""Question: {state['question']}
Result columns: {state['columns']}

Write matplotlib code that creates ONE chart to help visualize this result.
Rules:
- `df` is already loaded as a pandas DataFrame (from the query result), and
  `output_path` is already defined. End with plt.savefig(output_path). Do
  NOT call plt.show().
- Use the EXACT column names listed above.
- Keep it to one chart, directly relevant to the question.
- Return ONLY the code. No explanation, no markdown fences.
"""
    response = llm.invoke(prompt)
    chart_code = _strip_code_fences(response.content)

    tmp_df = pd.DataFrame(state["rows"], columns=state["columns"])
    fd, tmp_csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    tmp_df.to_csv(tmp_csv_path, index=False)

    try:
        state["chart_base64"] = run_chart_code(chart_code, tmp_csv_path)
        state["chart_generated"] = True
        state["chart_error"] = None
    except ChartExecutionError as e:
        state["chart_generated"] = False
        state["chart_base64"] = None
        state["chart_error"] = f"{e.error_type}: {e.error_message}"
    finally:
        os.remove(tmp_csv_path)

    return state


def _route_after_interpret(state: SQLAgentState) -> str:
    if not state["success"]:
        return "skip"
    return "decide_chart" if state.get("include_chart") else "skip"


def _route_after_decide(state: SQLAgentState) -> str:
    return "generate_chart" if state.get("wants_chart") else "skip"


def _rows_preview(columns: list, rows: list, limit: int = 20) -> str:
    lines = [", ".join(columns)]
    for r in rows[:limit]:
        lines.append(", ".join(str(v) for v in r))
    return "\n".join(lines)


def _route_after_execute(state: SQLAgentState) -> str:
    if state["success"]:
        return "interpret"
    if state["retry_count"] < MAX_RETRIES:
        return "fix"
    return "interpret"


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines)
    return text


def _finalize_answer(response) -> str:
    """
    Detects when Gemini's response was cut off by max_output_tokens instead
    of finishing naturally, and says so explicitly rather than silently
    returning a sentence that stops mid-word. Same logic as orchestrator.py's
    version -- kept duplicated rather than shared to avoid a cross-import
    between the two orchestrators for one small helper.
    """
    text = response.content
    finish_reason = None
    try:
        finish_reason = response.response_metadata.get("finish_reason")
    except AttributeError:
        pass

    truncated = finish_reason is not None and str(finish_reason).upper() in (
        "MAX_TOKENS",
        "LENGTH",
    )

    if truncated:
        text = text.rstrip() + (
            "\n\n[This answer was cut off because it hit the response length "
            "limit. Try a more specific or narrower question for a complete answer.]"
        )
    return text


def build_sql_graph():
    graph = StateGraph(SQLAgentState)
    graph.add_node("plan", plan_sql_node)
    graph.add_node("execute", execute_sql_node)
    graph.add_node("fix", fix_sql_node)
    graph.add_node("interpret", interpret_sql_node)
    graph.add_node("decide_chart", decide_chart_node)
    graph.add_node("generate_chart", generate_chart_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges(
        "execute",
        _route_after_execute,
        {"fix": "fix", "interpret": "interpret"},
    )
    graph.add_edge("fix", "execute")
    graph.add_conditional_edges(
        "interpret",
        _route_after_interpret,
        {"decide_chart": "decide_chart", "skip": END},
    )
    graph.add_conditional_edges(
        "decide_chart",
        _route_after_decide,
        {"generate_chart": "generate_chart", "skip": END},
    )
    graph.add_edge("generate_chart", END)

    return graph.compile()
