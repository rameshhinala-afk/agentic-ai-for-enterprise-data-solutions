"""The agent: plan -> act (call tool) -> observe -> repeat -> final answer.

Two interchangeable "brains":
  * ClaudeBrain      - real LLM tool-use loop (needs ANTHROPIC_API_KEY + `pip install anthropic`)
  * RuleBasedBrain   - offline keyword planner so the project runs with zero setup
Every tool call is recorded in an audit log, which matters in enterprise settings.
"""
import json
import os

from tools import TOOLS, TOOL_SPECS

MAX_STEPS = 6


# ---------------------------------------------------------------- offline brain
class RuleBasedBrain:
    """Very simple planner: schema first, then a query chosen by keywords."""

    def plan(self, question: str) -> list[tuple[str, dict]]:
        q = question.lower()
        steps = [("describe_schema", {})]
        if "anomal" in q or "outlier" in q or "unusual" in q:
            steps.append(("detect_anomalies", {"table": "orders", "column": "quantity"}))
        elif "region" in q:
            steps.append(("run_sql", {"query":
                "SELECT c.region, ROUND(SUM(o.amount),2) AS revenue, COUNT(*) AS orders "
                "FROM orders o JOIN customers c USING(customer_id) "
                "GROUP BY c.region ORDER BY revenue DESC"}))
        elif "customer" in q or "top" in q:
            steps.append(("run_sql", {"query":
                "SELECT c.name, c.segment, ROUND(SUM(o.amount),2) AS revenue "
                "FROM orders o JOIN customers c USING(customer_id) "
                "GROUP BY c.customer_id ORDER BY revenue DESC LIMIT 5"}))
        elif "stock" in q or "inventory" in q:
            steps.append(("run_sql", {"query":
                "SELECT name, stock FROM products ORDER BY stock LIMIT 3"}))
        elif "month" in q or "trend" in q:
            steps.append(("run_sql", {"query":
                "SELECT substr(order_date,1,7) AS month, ROUND(SUM(amount),2) AS revenue "
                "FROM orders GROUP BY month ORDER BY month"}))
        else:
            steps.append(("run_sql", {"query":
                "SELECT COUNT(*) AS total_orders, ROUND(SUM(amount),2) AS total_revenue FROM orders"}))
        return steps

    def run(self, question, call_tool):
        observations = []
        for name, args in self.plan(question):
            observations.append((name, call_tool(name, args)))
        return self._summarise(observations)

    @staticmethod
    def _summarise(observations):
        name, result = observations[-1]
        if "error" in result:
            return f"The query failed: {result['error']}"
        if name == "detect_anomalies":
            a = result["anomalies"]
            lines = [f"Found {len(a)} anomalous order(s) (mean qty {result['mean']}, std {result['std']}):"]
            lines += [f"  - order rowid {x['rowid']}: quantity {x['value']} (z={x['z_score']})" for x in a]
            return "\n".join(lines)
        header = " | ".join(result["columns"])
        body = "\n".join("  " + " | ".join(str(v) for v in r) for r in result["rows"])
        return f"Result ({result['row_count']} rows):\n  {header}\n{body}"


# ------------------------------------------------------------------ Claude brain
class ClaudeBrain:
    SYSTEM = ("You are an enterprise data analyst agent. Use the tools to inspect the schema, "
              "query data, and detect anomalies. Never guess numbers; base answers on tool results. "
              "Finish with a concise business-oriented answer.")

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

    def run(self, question, call_tool):
        messages = [{"role": "user", "content": question}]
        for _ in range(MAX_STEPS):
            resp = self.client.messages.create(
                model=self.model, max_tokens=1500, system=self.SYSTEM,
                tools=TOOL_SPECS, messages=messages)
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    out = call_tool(b.name, b.input)
                    results.append({"type": "tool_result", "tool_use_id": b.id,
                                    "content": json.dumps(out, default=str)})
            messages.append({"role": "user", "content": results})
        return "Stopped: step limit reached."


# ------------------------------------------------------------------------ agent
class EnterpriseDataAgent:
    def __init__(self, use_llm: bool | None = None):
        if use_llm is None:
            use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
        self.brain = ClaudeBrain() if use_llm else RuleBasedBrain()
        self.audit_log: list[dict] = []

    def call_tool(self, name: str, args: dict) -> dict:
        if name not in TOOLS:
            result = {"error": f"Unknown tool {name}"}
        else:
            try:
                result = TOOLS[name](**args)
            except Exception as e:  # keep the agent loop alive on tool failure
                result = {"error": str(e)}
        self.audit_log.append({"tool": name, "args": args, "ok": "error" not in result})
        return result

    def ask(self, question: str) -> str:
        return self.brain.run(question, self.call_tool)
