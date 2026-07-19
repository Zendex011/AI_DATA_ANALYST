"""
Executes validated SQL against an external database connection.

Row results are capped server-side (MAX_ROWS_RETURNED) regardless of what
the query asks for -- this protects against a query that returns millions
of rows blowing up memory or the LLM's context window in the interpret step.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.core.sql_validator import validate_read_only_sql, SQLValidationError

MAX_ROWS_RETURNED = 500


class SQLExecutionError(Exception):
    def __init__(self, error_type: str, error_message: str):
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(f"{error_type}: {error_message}")


def run_sql_query(connection_string: str, sql: str) -> dict:
    """
    Returns: {"columns": [...], "rows": [[...], ...], "row_count": int, "truncated": bool}
    Raises: SQLExecutionError on validation failure or DB error. Never raises
    a raw SQLAlchemy/DB exception -- callers get a structured type/message.
    """
    try:
        validate_read_only_sql(sql)
    except SQLValidationError as e:
        raise SQLExecutionError("SQLValidationError", str(e))

    engine = create_engine(connection_string, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_ROWS_RETURNED)
            truncated = len(rows) == MAX_ROWS_RETURNED and result.fetchone() is not None
    except SQLAlchemyError as e:
        original = getattr(e, "orig", None)
        raise SQLExecutionError(
            error_type=type(original).__name__ if original else type(e).__name__,
            error_message=str(original) if original else str(e),
        )
    finally:
        engine.dispose()

    return {
        "columns": columns,
        "rows": [list(r) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }