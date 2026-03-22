"""Local semantic AI smoke test for NyaySaathi understanding engine."""

from __future__ import annotations

import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()

from legal.ai_engine import understand_user_problem


TEST_INPUTS = [
    "My company has not paid salary",
    "UPI fraud happened",
    "Landlord keeping my deposit",
    "Employer delayed payment",
    "Bank account hacked",
]


def run() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for text in TEST_INPUTS:
        result = understand_user_problem(text)
        rows.append(
            {
                "input": text,
                "category": result.get("category", "Other"),
                "confidence": result.get("confidence", "Low"),
                "similarity": result.get("similarity_score", 0.0),
                "matched_sentence": result.get("matched_text", ""),
                "intent": result.get("intent", "guidance"),
                "workflow_steps": result.get("workflow_steps", []),
                "explanation": result.get("explanation", ""),
                "source": result.get("source", "fallback"),
            }
        )
    return rows


if __name__ == "__main__":
    output = run()
    print(json.dumps(output, ensure_ascii=False, indent=2))
