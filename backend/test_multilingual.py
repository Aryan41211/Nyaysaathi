"""Multilingual pipeline smoke/regression tests for NyaySaathi.

Run:
    python test_multilingual.py

Optional:
    python test_multilingual.py --json
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()

from ai_engine.response_generator import generate_legal_guidance  # noqa: E402


TEST_INPUTS: list[dict[str, str]] = [
    {"name": "english_salary", "query": "My salary has not been paid for two months."},
    {"name": "roman_hindi_salary", "query": "mera paisa 2 mahine se nahi mila"},
    {"name": "roman_marathi_theft", "query": "gharath zali chori"},
    {"name": "hindi_script_police", "query": "पुलिस FIR दर्ज नहीं कर रही है"},
    {"name": "marathi_script_fraud", "query": "माझे पैसे ऑनलाइन फसवणुकीत गेले"},
]


def _compact(result: dict[str, Any]) -> dict[str, Any]:
    workflow = result.get("workflow", []) or []
    return {
        "detected_language": result.get("detected_language"),
        "normalized_query": result.get("normalized_query"),
        "category": result.get("category"),
        "subcategory": result.get("subcategory"),
        "translation_triggered": result.get("translation_triggered"),
        "workflow_count": len(workflow),
        "workflow_preview": workflow[:2],
        "message": result.get("message"),
    }


def run_suite(json_mode: bool = False) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    for row in TEST_INPUTS:
        output = generate_legal_guidance(row["query"])
        record = {
            "name": row["name"],
            "query": row["query"],
            "result": _compact(output),
        }
        records.append(record)
        if not json_mode:
            print(json.dumps(record, ensure_ascii=True, indent=2))

    # Cache behavior check (second call should ideally avoid translation call when enabled).
    cache_probe_query = "mera paisa 2 mahine se nahi mila"
    first = generate_legal_guidance(cache_probe_query)
    second = generate_legal_guidance(cache_probe_query)

    summary = {
        "total_cases": len(TEST_INPUTS),
        "detected_languages": [r["result"]["detected_language"] for r in records],
        "cache_probe": {
            "query": cache_probe_query,
            "first_translation_triggered": first.get("translation_triggered", False),
            "second_translation_triggered": second.get("translation_triggered", False),
        },
    }

    payload = {"summary": summary, "records": records}
    print("\n=== MULTILINGUAL SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multilingual NyaySaathi tests")
    parser.add_argument("--json", action="store_true", help="Print only summary JSON")
    parser.add_argument("--output", default="", help="Optional output file for full report JSON")
    args = parser.parse_args()

    report = run_suite(json_mode=args.json)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=True, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
