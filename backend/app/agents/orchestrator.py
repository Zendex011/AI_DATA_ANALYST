from typing import TypedDict, Optional
from urllib import response
from langgraph.graph import StateGraph, END
from app.core.llm import get_llm
from app.core.schema_utils import build_schema_summary
from app.core.chart_generator import run_chart_code, ChartExecutionError
from app.agents.tools import execute_pandas_code
from app.config import GEMINI_MAX_OUTPUT_TOKENS_CODE, GEMINI_MAX_OUTPUT_TOKENS_TEXT

MAX_RETRIES = 1  # exactly one automatic retry, as specified

# Shared rules injected into both the initial code-gen prompt and the
# retry/fix prompt, so both paths follow the same pandas discipline.
PANDAS_RULES = """
Rules for the code you write:
- `df` is already loaded as a pandas DataFrame. Do not redefine it or re-read the CSV.
- Use the EXACT column names given in the schema above. Do not guess or
  assume a column name — if it's not in the schema, it doesn't exist.
- Know the difference between a DataFrame and a Series:
  - df.iloc[0], df.loc[x], a single column df['col'], or a groupby().sum() on
    one column all return a Series, NOT a DataFrame.
  - DataFrame-only methods (select_dtypes, merge, pivot_table, etc.) will
    raise AttributeError if called on a Series. Only call them on something
    you are sure is still a DataFrame.
- Prefer explicit column selection, e.g. df[['col_a', 'col_b']], over
  positional indexing when you can.
- Avoid chained indexing (e.g. df[df['x'] > 0]['y'][0]) since it can silently
  change types or trigger pandas warnings. Break it into steps instead.
- Use print() for every value the user needs to see. If nothing is printed,
  the user sees no answer.
- Only print VALUES COMPUTED FROM THE DATA (numbers, rows, aggregates,
  filtered tables). Never print explanations, guesses, or commentary about
  what a column "probably" means or what the dataset is "likely" about —
  that is not something you can verify by running code, and it belongs in
  a separate interpretation step, not here.
- If part of the user's question can't be answered by computing something
  from the data (e.g. "what is this dataset about", "what do these columns
  represent"), simply don't write code for that part. Only compute what is
  actually derivable from `df`. Do not fill the gap with a guess.
- Return ONLY the code. No explanation, no markdown code fences, no comments
  about what you're about to do.
"""


class AgentState(TypedDict):
    question: str
    csv_path: str
    row_count: int
    columns_with_dtypes: dict
    generated_code: str
    stdout: str
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


def plan_node(state: AgentState) -> AgentState:
    """LLM writes pandas code to answer the question."""
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))

    schema = build_schema_summary(state["row_count"], state["columns_with_dtypes"])
    prompt = f"""You are a data analyst. A user uploaded a CSV and asked:
"{state['question']}"

{schema}

Write pandas code that answers this question.
{PANDAS_RULES}
"""
    response = llm.invoke(prompt)

    content = response.content

# Newer LangChain/Gemini versions return a list of content blocks
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict)
            else getattr(part, "text", str(part))
            for part in content
        )

    state["generated_code"] = _strip_code_fences(content)
    state["retry_count"] = 0
    return state


def execute_node(state: AgentState) -> AgentState:
    """Runs the generated code in the sandbox and records structured result."""
    result = execute_pandas_code(state["generated_code"], state["csv_path"])

    state["success"] = result["success"]
    if result["success"]:
        state["stdout"] = result["stdout"]
        state["error_type"] = None
        state["error_message"] = None
    else:
        state["stdout"] = ""
        state["error_type"] = result["error_type"]
        state["error_message"] = result["error_message"]

    return state


def fix_node(state: AgentState) -> AgentState:
    """
    Sends the failed code + error back to the LLM for exactly one correction
    attempt. Only reached when execute_node fails and a retry is still available.
    """
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))

    schema = build_schema_summary(state["row_count"], state["columns_with_dtypes"])
    prompt = f"""The following pandas code failed when run against `df`.

Original question: "{state['question']}"

{schema}

Code that failed:
{state['generated_code']}

Error type: {state['error_type']}
Error message: {state['error_message']}

Fix the code so it runs correctly and answers the original question.
{PANDAS_RULES}
"""
    response = llm.invoke(prompt)
    print(type(response.content))
    print(repr(response.content))
    state["generated_code"] = _strip_code_fences(response.content)
    state["retry_count"] += 1
    return state


def interpret_node(state: AgentState) -> AgentState:
    """LLM turns raw output into a plain-English answer, or reports failure clearly."""
    if not state["success"]:
        state["final_answer"] = (
            "The analysis failed and could not be completed automatically. "
            f"Error type: {state['error_type']}. "
            f"Details: {state['error_message']}"
        )
        return state

    llm = get_llm(temperature=0.3, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_TEXT, api_key=state.get("gemini_api_key"))
    # Cap how much raw stdout gets embedded in the prompt. A question like
    # "tell me about this dataset" can produce a df.info()+describe()+
    # value_counts() dump running to thousands of characters -- feeding all
    # of it in invites the model to try to narrate every line, which is what
    # was actually causing the answer to hit the token ceiling and cut off
    # mid-sentence. Truncating here keeps the model focused on a summary.
    stdout_for_prompt = _truncate_for_prompt(state["stdout"])
    prompt = f"""Question asked: {state['question']}
Code that was run: {state['generated_code']}
Output produced: {stdout_for_prompt}

Explain the computed result in plain, direct English first. Keep it to a
few sentences -- summarize, don't narrate every line of the output.

If the question also asked something the code couldn't compute — like what
the dataset is about, or what the columns likely represent — answer that
part too, using the column names and your own general knowledge. Be clear
that this part is a reasonable inference, not something read from the data
itself.
"""
    response = llm.invoke(prompt)
    state["final_answer"] = _finalize_answer(response)
    return state


def decide_chart_node(state: AgentState) -> AgentState:
    """
    Only reached when the user requested include_chart=True. Still asks the
    LLM whether a chart actually helps THIS question -- "what's the average
    salary" doesn't need a bar chart of one number. Avoids spending the
    extra generate_chart LLM call + subprocess run when it wouldn't help.
    """
    llm = get_llm(temperature=0, max_output_tokens=10, api_key=state.get("gemini_api_key"))
    prompt = f"""Question: {state['question']}
Answer given: {state['final_answer']}

Would a chart (bar chart, line chart, histogram, scatter plot, etc.)
meaningfully help visualize the answer to this question? A single number
or short list generally does NOT need a chart. A comparison across
categories, a trend over time, or a distribution generally DOES.

Reply with exactly one word: YES or NO.
"""
    response = llm.invoke(prompt)
    state["wants_chart"] = response.content.strip().upper().startswith("Y")
    return state


def generate_chart_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CODE, api_key=state.get("gemini_api_key"))
    schema = build_schema_summary(state["row_count"], state["columns_with_dtypes"])
    prompt = f"""Question: {state['question']}

{schema}

Write matplotlib code that creates ONE chart to help visualize the answer.
Rules:
- `df` is already loaded as a pandas DataFrame, and `output_path` is already
  defined. End with plt.savefig(output_path). Do NOT call plt.show().
- Use the EXACT column names from the schema above.
- Keep it to one chart, directly relevant to the question -- not a grid of
  subplots unless the question clearly needs a multi-part comparison.
- Return ONLY the code. No explanation, no markdown fences.
"""
    response = llm.invoke(prompt)
    chart_code = _strip_code_fences(response.content)

    try:
        state["chart_base64"] = run_chart_code(chart_code, state["csv_path"])
        state["chart_generated"] = True
        state["chart_error"] = None
    except ChartExecutionError as e:
        state["chart_generated"] = False
        state["chart_base64"] = None
        state["chart_error"] = f"{e.error_type}: {e.error_message}"

    return state


def _route_after_interpret(state: AgentState) -> str:
    if not state["success"]:
        return "skip"  # nothing valid to chart if the analysis itself failed
    return "decide_chart" if state.get("include_chart") else "skip"


def _route_after_decide(state: AgentState) -> str:
    return "generate_chart" if state.get("wants_chart") else "skip"


def _route_after_execute(state: AgentState) -> str:
    """Conditional edge: retry once on failure, otherwise move on."""
    if state["success"]:
        return "interpret"
    if state["retry_count"] < MAX_RETRIES:
        return "fix"
    return "interpret"


def _strip_code_fences(text) -> str:
    if isinstance(text, list):
        parts = []
        for item in text:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                # Handles LangChain content block objects
                parts.append(getattr(item, "text", str(item)))
        text = "".join(parts)

    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return text.strip()


def _truncate_for_prompt(text: str, max_chars: int = 3000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated, {len(text) - max_chars} more characters not shown]"


def _finalize_answer(response) -> str:
    """
    Detects when Gemini's response was cut off by max_output_tokens instead
    of finishing naturally, and says so explicitly. Without this check, a
    response cut off mid-sentence looks identical to a complete one in the
    API response -- the user has no way to tell "The average is 50" from
    a genuinely truncated "The average is 5" (missing a digit) unless we
    flag it.
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


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("fix", fix_node)
    graph.add_node("interpret", interpret_node)
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
