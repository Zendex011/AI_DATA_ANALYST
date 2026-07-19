"""
Builds a compact schema description to give the LLM enough to reference
real column names correctly, without ever including row-level sample data.

Deliberately excludes:
  - actual data values / sample rows (the expensive part on wide files)
  - anything that scales with row count (28,000 vs 28 rows costs the same)

Deliberately includes:
  - row count, column count (cheap, useful context)
  - every column name + dtype (needed for correctness — truncating this list
    on a 301-column file just means the LLM can't answer questions about the
    columns you cut, which causes more retries, not fewer tokens overall)
"""


def build_schema_summary(row_count: int, columns_with_dtypes: dict) -> str:
    column_lines = "\n".join(
        f"- {name}: {dtype}" for name, dtype in columns_with_dtypes.items()
    )
    return f"""Dataset shape: {row_count} rows, {len(columns_with_dtypes)} columns.
Columns (name: dtype):
{column_lines}"""