"""
Validates that generated SQL is a single, read-only SELECT statement.

This is DEFENSE IN DEPTH, not the primary safeguard. The primary safeguard
is that the database user/connection string you provide must itself be
read-only (a GRANT SELECT-only user). This validator exists to catch
LLM mistakes before they ever reach the database, not to replace proper
DB-level permissions -- if your connection string has write access, this
code is not what's protecting your data.
"""

import re
import sqlparse

DISALLOWED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "EXEC", "EXECUTE",
    "MERGE", "REPLACE", "CALL", "COPY", "VACUUM", "REINDEX",
]

_KEYWORD_PATTERNS = [re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in DISALLOWED_KEYWORDS]


class SQLValidationError(Exception):
    pass


def validate_read_only_sql(sql: str) -> None:
    if not sql or not sql.strip():
        raise SQLValidationError("No SQL statement provided")

    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]

    if len(statements) == 0:
        raise SQLValidationError("No SQL statement found")
    if len(statements) > 1:
        raise SQLValidationError(
            "Only a single SQL statement is allowed (no stacked/multiple statements)"
        )

    stmt = statements[0]
    stmt_type = stmt.get_type()  # 'SELECT', 'INSERT', 'UNKNOWN', etc.
    stripped_upper = sql.strip().upper()

    # sqlparse reports CTEs ("WITH ... SELECT") as UNKNOWN, so allow that
    # case explicitly as long as it actually starts with SELECT or WITH.
    is_select = stmt_type == "SELECT"
    is_cte = stmt_type == "UNKNOWN" and (
        stripped_upper.startswith("SELECT") or stripped_upper.startswith("WITH")
    )

    if not (is_select or is_cte):
        raise SQLValidationError(
            f"Only SELECT queries are allowed (or WITH...SELECT CTEs), got: {stmt_type}"
        )

    for pattern, keyword in zip(_KEYWORD_PATTERNS, DISALLOWED_KEYWORDS):
        if pattern.search(sql):
            raise SQLValidationError(f"Disallowed keyword detected: {keyword}")