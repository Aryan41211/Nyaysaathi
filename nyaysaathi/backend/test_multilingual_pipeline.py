"""Basic multilingual functional checks for NyaySaathi response pipeline.

Run from backend/:
  python test_multilingual_pipeline.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")

import django

django.setup()

from ai_engine.response_generator import generate_legal_guidance

TEST_CASES = [
    {
        "name": "English input -> English output",
        "query": "My employer did not pay salary for two months",
        "expected_language": "en",
    },
    {
        "name": "Hindi input -> Hindi output",
        "query": "मुझे वेतन नहीं मिला है, क्या करूं",
        "expected_language": "hi",
    },
    {
        "name": "Marathi input -> Marathi output",
        "query": "माझा पगार मिळाला नाही, तक्रार कशी करायची",
        "expected_language": "mr",
    },
    {
        "name": "Roman Hindi input -> Hindi output",
        "query": "mera paisa nahi mila, kya karu",
        "expected_language": "hi",
    },
    {
        "name": "Roman Marathi input -> Marathi output",
        "query": "gharath chori zali, takrar kuthe karaychi",
        "expected_language": "mr",
    },
]


def run() -> int:
    failures = 0

    for case in TEST_CASES:
        result = generate_legal_guidance(case["query"])
        actual_language = result.get("language") or result.get("detected_language")
        has_workflow = isinstance(result.get("workflow"), list)

        ok = actual_language == case["expected_language"] and has_workflow
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['name']}")
        print(
            f"  query={case['query']}\n"
            f"  expected_language={case['expected_language']} actual_language={actual_language}\n"
            f"  category_id={result.get('category_id', '')} total={result.get('total', 0)}"
        )

        if not ok:
            failures += 1

    print("\nSummary:", "PASS" if failures == 0 else f"{failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
