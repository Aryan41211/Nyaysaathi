from __future__ import annotations

import json

from .assistant import run_legal_assistant


def _print_result(result):
    print("\n=== NyayaSaathi Answer ===")
    print("Intent:", result.get("intent"))
    print("Category:", result.get("matched_category"))
    print("Subcategory:", result.get("matched_subcategory"))
    print("Confidence:", result.get("confidence_score"))
    print("\nReasoning:")
    print(result.get("explanation", ""))

    steps = result.get("steps", [])
    if steps:
        print("\nRecommended Steps:")
        for i, step in enumerate(steps[:6], start=1):
            print(f"{i}. {step}")

    docs = result.get("documents", [])
    if docs:
        print("\nDocuments:")
        for d in docs[:6]:
            print("-", d)

    auth = result.get("authorities", [])
    if auth:
        print("\nAuthorities:")
        for a in auth[:6]:
            print("-", a)

    sugg = result.get("suggestions", [])
    if sugg:
        print("\nSuggestions:")
        for s in sugg:
            print("-", s)

    print("\nRaw JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    print("NyayaSaathi Local Assistant (type 'exit' to quit)")

    while True:
        try:
            query = input("\nEnter your problem: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting NyayaSaathi.")
            break

        if query.lower() in {"exit", "quit", "q"}:
            print("Exiting NyayaSaathi.")
            break

        if not query:
            print("Please enter a non-empty query.")
            continue

        try:
            result = run_legal_assistant(query, top_k=5)
            _print_result(result)
        except Exception as exc:
            print("System error:", str(exc))


if __name__ == "__main__":
    main()
