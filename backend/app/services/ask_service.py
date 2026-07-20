"""
The actual "ask a question" logic, extracted out of routes.py so it has
exactly one implementation shared by:
  - the synchronous /ask and /ask-db endpoints (routes.py)
  - the async Celery tasks (workers/tasks.py)

Without this, the async task would need its own copy of the cache-check /
graph-invoke / history-persist logic, and the two paths would silently
drift apart the next time one of them got a bugfix the other didn't.

Raises ValueError when the file/db_id isn't found -- callers translate
that into whatever's appropriate for their context (HTTPException in
routes.py, a failed Celery task result in tasks.py).
"""

import json
from sqlalchemy.orm import Session
from app.db.models import UploadedFile, DatabaseConnection, QueryHistory, User
from app.agents.orchestrator import build_graph
from app.agents.sql_orchestrator import build_sql_graph
from app.core import cache
from app.core.crypto import decrypt_secret

_graph = None
_sql_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _get_sql_graph():
    global _sql_graph
    if _sql_graph is None:
        _sql_graph = build_sql_graph()
    return _sql_graph


def get_user_gemini_key(user: User) -> str | None:
    """
    Returns the user's own decrypted Gemini key, or None if they haven't
    set one (get_llm() falls back to the app's shared GEMINI_API_KEY when
    given None). Also falls back to None if decryption fails -- e.g.
    ENCRYPTION_KEY changed since the key was saved -- rather than crashing
    the request; the user just silently uses the shared key that request.
    """
    if not user or not user.gemini_api_key:
        return None
    try:
        return decrypt_secret(user.gemini_api_key)
    except ValueError:
        return None


def run_csv_ask(
    db: Session, file_id: str, question: str, include_chart: bool, gemini_api_key: str | None = None
) -> dict:
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not db_file:
        raise ValueError("File not found. Upload it first via /upload")

    cached = cache.get_cached(file_id, question)
    if cached:
        return {**cached, "cached": True}

    state = {
        "question": question,
        "csv_path": db_file.path,
        "row_count": db_file.rows,
        "columns_with_dtypes": json.loads(db_file.dtypes),
        "generated_code": "",
        "stdout": "",
        "success": False,
        "error_type": None,
        "error_message": None,
        "retry_count": 0,
        "final_answer": "",
        "include_chart": include_chart,
        "chart_generated": False,
        "chart_base64": None,
        "chart_error": None,
        "wants_chart": False,
        "gemini_api_key": gemini_api_key,
    }
    final_state = _get_graph().invoke(state)

    history_entry = QueryHistory(
        source_type="csv",
        file_id=file_id,
        question=question,
        answer=final_state["final_answer"],
        generated_code=final_state["generated_code"],
        success=final_state["success"],
        error_type=final_state["error_type"],
        error_message=final_state["error_message"],
        retries_used=final_state["retry_count"],
    )
    db.add(history_entry)
    db.commit()

    response_data = {
        "answer": final_state["final_answer"],
        "success": final_state["success"],
        "generated_code": final_state["generated_code"],
        "stdout": final_state["stdout"],
        "error_type": final_state["error_type"],
        "error_message": final_state["error_message"],
        "retries_used": final_state["retry_count"],
        "chart_generated": final_state["chart_generated"],
        "chart_base64": final_state["chart_base64"],
        "chart_error": final_state["chart_error"],
    }

    if final_state["success"]:
        cache.set_cached(file_id, question, response_data)

    return {**response_data, "cached": False}


def run_db_ask(
    db: Session, db_id: str, question: str, include_chart: bool, gemini_api_key: str | None = None
) -> dict:
    db_conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == db_id).first()
    if not db_conn:
        raise ValueError("Database connection not found. Connect it first via /connect-db")

    cached = cache.get_cached(db_id, question)
    if cached:
        return {**cached, "cached": True}

    state = {
        "question": question,
        "connection_string": db_conn.connection_string,
        "schema_summary": db_conn.schema_summary,
        "generated_sql": "",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "truncated": False,
        "success": False,
        "error_type": None,
        "error_message": None,
        "retry_count": 0,
        "final_answer": "",
        "include_chart": include_chart,
        "chart_generated": False,
        "chart_base64": None,
        "chart_error": None,
        "wants_chart": False,
        "gemini_api_key": gemini_api_key,
    }
    final_state = _get_sql_graph().invoke(state)

    history_entry = QueryHistory(
        source_type="database",
        db_id=db_id,
        question=question,
        answer=final_state["final_answer"],
        generated_code=final_state["generated_sql"],
        success=final_state["success"],
        error_type=final_state["error_type"],
        error_message=final_state["error_message"],
        retries_used=final_state["retry_count"],
    )
    db.add(history_entry)
    db.commit()

    response_data = {
        "answer": final_state["final_answer"],
        "success": final_state["success"],
        "generated_sql": final_state["generated_sql"],
        "columns": final_state["columns"],
        "rows": final_state["rows"],
        "row_count": final_state["row_count"],
        "truncated": final_state["truncated"],
        "error_type": final_state["error_type"],
        "error_message": final_state["error_message"],
        "retries_used": final_state["retry_count"],
        "chart_generated": final_state["chart_generated"],
        "chart_base64": final_state["chart_base64"],
        "chart_error": final_state["chart_error"],
    }

    if final_state["success"]:
        cache.set_cached(db_id, question, response_data)

    return {**response_data, "cached": False}
