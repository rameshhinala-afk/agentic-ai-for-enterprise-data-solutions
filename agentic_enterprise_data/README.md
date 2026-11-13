# Agentic AI for Enterprise Data Solutions

A minimal agent that answers business questions over an enterprise database by
planning, calling tools, observing results, and returning an answer.

## Structure
| File | Purpose |
|---|---|
| `data_setup.py` | Builds a sample SQLite DB (customers, products, orders) |
| `tools.py` | Agent tools: `describe_schema`, `run_sql` (read-only), `detect_anomalies` |
| `agent.py` | Agent loop, offline rule-based brain, optional Claude brain, audit log |
| `main.py` | CLI |

## Run
```bash
python main.py --demo                  # no dependencies, works offline
python main.py "revenue by region"
```

## Use a real LLM (optional)
```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key
python main.py "Which customer segment drives the most revenue?"
```

## Enterprise-minded design
- Read-only DB connection + SELECT-only SQL guard
- Row limits on every query
- Audit log of every tool call
- Step limit to prevent runaway loops

## Ideas to extend
Swap SQLite for Postgres/Snowflake, add RAG over documents, add human approval
for sensitive tools, add role-based access per tool.
