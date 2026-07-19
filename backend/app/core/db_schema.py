"""
Reflects table/column structure from an external database so the LLM has
something concrete to write SQL against, instead of guessing table names.
"""

from sqlalchemy import create_engine, inspect

MAX_TABLES_IN_SUMMARY = 30


def reflect_schema(connection_string: str) -> tuple[str, str]:
    """
    Connects to the given database just long enough to read its schema.
    Returns (schema_summary_text, dialect_name).
    Raises whatever SQLAlchemy raises on a bad connection string --
    callers should catch SQLAlchemyError and turn it into an HTTP 400.
    """
    engine = create_engine(connection_string, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        lines = []
        for table in table_names[:MAX_TABLES_IN_SUMMARY]:
            columns = inspector.get_columns(table)
            col_desc = ", ".join(f"{c['name']} ({c['type']})" for c in columns)
            lines.append(f"- {table}: {col_desc}")

        if len(table_names) > MAX_TABLES_IN_SUMMARY:
            lines.append(
                f"... and {len(table_names) - MAX_TABLES_IN_SUMMARY} more tables (not shown)"
            )

        return "\n".join(lines), engine.dialect.name
    finally:
        engine.dispose()