"""CLI entry point.

  python main.py --demo                 run sample questions
  python main.py "revenue by region"    ask one question
  python main.py                        interactive mode
"""
import os
import sys

from agent import EnterpriseDataAgent
from data_setup import DB_PATH, create_database

DEMO_QUESTIONS = [
    "What is the revenue by region?",
    "Who are our top customers?",
    "Which products have low stock?",
    "Are there any anomalies in orders?",
]


def main():
    if not os.path.exists(DB_PATH):
        create_database()
    agent = EnterpriseDataAgent()
    mode = type(agent.brain).__name__
    print(f"[Agent brain: {mode}]\n")

    args = sys.argv[1:]
    if args == ["--demo"]:
        questions = DEMO_QUESTIONS
    elif args:
        questions = [" ".join(args)]
    else:
        questions = None

    if questions:
        for q in questions:
            print(f"Q: {q}\n{agent.ask(q)}\n")
    else:
        while (q := input("Ask a data question (blank to quit): ").strip()):
            print(agent.ask(q), "\n")

    print("Audit log:")
    for entry in agent.audit_log:
        print(" ", entry)


if __name__ == "__main__":
    main()
