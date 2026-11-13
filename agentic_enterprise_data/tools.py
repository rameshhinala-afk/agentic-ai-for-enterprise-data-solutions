"""Tools the agent can call. Each returns a JSON-serialisable dict."""
import re
import sqlite3
import statistics

DB_PATH = "enterprise.db"
MAX_ROWS = 50


def _conn():
    # Read-only connection: the agent can never modify enterprise data.
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def describe_schema() -> dict:
    with _conn() as c:
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t: [col[1] for col in c.execute(f"PRAGMA table_info({t})")] for t in tables}


def run_sql(query: str) -> dict:
    q = query.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", q, re.I) or re.search(
            r"\b(insert|update|delete|drop|alter|create|attach|pragma)\b", q, re.I):
        return {"error": "Only read-only SELECT queries are allowed."}
    try:
        with _conn() as c:
            cur = c.execute(q)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS)
        return {"columns": cols, "rows": rows, "row_count": len(rows)}
    except sqlite3.Error as e:
        return {"error": str(e)}


def detect_anomalies(table: str, column: str, z_threshold: float = 3.0) -> dict:
    schema = describe_schema()
    if table not in schema or column not in schema[table]:
        return {"error": f"Unknown table/column: {table}.{column}"}
    with _conn() as c:
        rows = c.execute(f"SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
    values = [float(v) for _, v in rows]
    if len(values) < 3:
        return {"anomalies": []}
    mean, std = statistics.mean(values), statistics.pstdev(values)
    if std == 0:
        return {"anomalies": []}
    out = [{"rowid": rid, "value": v, "z_score": round((v - mean) / std, 2)}
           for rid, v in rows if abs((v - mean) / std) >= z_threshold]
    return {"mean": round(mean, 2), "std": round(std, 2), "anomalies": out[:MAX_ROWS]}


TOOLS = {
    "describe_schema": describe_schema,
    "run_sql": run_sql,
    "detect_anomalies": detect_anomalies,
}

# Tool definitions for the Claude API (used when ANTHROPIC_API_KEY is set).
TOOL_SPECS = [
    {"name": "describe_schema",
     "description": "List all tables and their columns in the enterprise database.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_sql",
     "description": "Run a read-only SQLite SELECT query. Returns up to 50 rows.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "detect_anomalies",
     "description": "Find statistical outliers (z-score) in a numeric column of a table.",
     "input_schema": {"type": "object",
                      "properties": {"table": {"type": "string"}, "column": {"type": "string"},
                                     "z_threshold": {"type": "number"}},
                      "required": ["table", "column"]}},
]
