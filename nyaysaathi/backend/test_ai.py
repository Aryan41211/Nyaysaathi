"""Production test harness for NyaySaathi AI legal understanding.

This script executes realistic legal problem statements against the AI engine,
evaluates intent/category/confidence quality, and emits a structured test report.

Usage:
    python test_ai.py
    python test_ai.py --output test_report.json --fail-on-fail

Prerequisites:
- OPENAI_API_KEY configured in environment or backend .env
- Django settings available via nyaysaathi_project.settings
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger("test_ai")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )


def _bootstrap_django() -> None:
    """Initialize Django app registry before importing project modules."""
    try:
        import django  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Django is not installed in the active Python environment. "
            "Activate the project virtual environment and retry."
        ) from error

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
    django.setup()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class TestCase:
    """Single AI understanding test case."""

    case_id: str
    user_input: str
    expected_category: str
    min_confidence: float
    intent_contains: tuple[str, ...]


@dataclass(frozen=True)
class CaseEvaluation:
    """Normalized result for one executed test case."""

    case_id: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    checks: dict[str, bool]
    passed: bool
    latency_ms: float
    error: str | None = None


TEST_CASES: list[TestCase] = [
    TestCase(
        case_id="T01_salary_unpaid",
        user_input="My employer has not paid my salary for the last 3 months and HR is ignoring my emails.",
        expected_category="Labour Issues",
        min_confidence=0.65,
        intent_contains=("salary", "wage", "payment"),
    ),
    TestCase(
        case_id="T02_cyber_fraud_upi",
        user_input="I clicked a fake UPI collect request and lost 48,000 rupees from my bank account.",
        expected_category="Cyber Crime",
        min_confidence=0.65,
        intent_contains=("fraud", "cyber", "upi"),
    ),
    TestCase(
        case_id="T03_tenant_deposit",
        user_input="Landlord is refusing to return my security deposit after I vacated the flat.",
        expected_category="Property",
        min_confidence=0.65,
        intent_contains=("tenant", "deposit", "landlord"),
    ),
    TestCase(
        case_id="T04_consumer_defective_product",
        user_input="I received a defective refrigerator and the seller denied replacement and refund.",
        expected_category="Consumer Issues",
        min_confidence=0.65,
        intent_contains=("consumer", "refund", "defective"),
    ),
    TestCase(
        case_id="T05_police_fir_refusal",
        user_input="Police station is refusing to register FIR for my chain snatching complaint.",
        expected_category="Police Issues",
        min_confidence=0.65,
        intent_contains=("fir", "police", "complaint"),
    ),
    TestCase(
        case_id="T06_identity_misuse_loan",
        user_input="Someone used my PAN details to take an instant loan and now recovery agents are calling me.",
        expected_category="Financial Fraud",
        min_confidence=0.60,
        intent_contains=("loan", "identity", "fraud"),
    ),
    TestCase(
        case_id="T07_domestic_violence",
        user_input="My husband is physically abusive and threatening to throw me out of the house.",
        expected_category="Family Issues",
        min_confidence=0.60,
        intent_contains=("violence", "abuse", "protection"),
    ),
    TestCase(
        case_id="T08_employment_wrongful_termination",
        user_input="I was terminated without notice after 6 years of service and salary dues are pending.",
        expected_category="Labour Issues",
        min_confidence=0.60,
        intent_contains=("termination", "salary", "employment"),
    ),
    TestCase(
        case_id="T09_property_partition_dispute",
        user_input="After my father's death, my brother forcefully occupied ancestral property and denies partition.",
        expected_category="Property",
        min_confidence=0.60,
        intent_contains=("property", "partition", "inheritance"),
    ),
    TestCase(
        case_id="T10_document_name_mismatch",
        user_input="My Aadhaar has a name mismatch and because of that my passport application got rejected.",
        expected_category="Documentation Issues",
        min_confidence=0.55,
        intent_contains=("document", "correction", "aadhaar"),
    ),
    TestCase(
        case_id="T11_consumer_hospital_overbilling",
        user_input="Private hospital charged hidden fees not mentioned in estimate and refused itemized bill.",
        expected_category="Consumer Issues",
        min_confidence=0.55,
        intent_contains=("overbilling", "consumer", "bill"),
    ),
    TestCase(
        case_id="T12_multi_issue_cyber_plus_police",
        user_input="My phone was hacked and money stolen, plus police are not filing FIR despite repeated visits.",
        expected_category="Cyber Crime",
        min_confidence=0.55,
        intent_contains=("cyber", "fir", "theft"),
    ),
    TestCase(
        case_id="T13_emotional_unclear",
        user_input="I am mentally exhausted and everyone is threatening me, I don't know what legal step to take.",
        expected_category="Other",
        min_confidence=0.30,
        intent_contains=("help", "clarify", "protection"),
    ),
    TestCase(
        case_id="T14_short_input",
        user_input="Need legal help urgently",
        expected_category="Other",
        min_confidence=0.20,
        intent_contains=("help", "unknown", "clarify"),
    ),
    TestCase(
        case_id="T15_non_legal_text",
        user_input="Can you suggest a healthy diet plan and workout schedule?",
        expected_category="Other",
        min_confidence=0.20,
        intent_contains=("unknown", "clarify", "general"),
    ),
]


def _contains_any(value: str, candidates: tuple[str, ...]) -> bool:
    lowered = (value or "").lower()
    return any(item.lower() in lowered for item in candidates)


def _evaluate_case(case: TestCase, output: dict[str, Any], latency_ms: float) -> CaseEvaluation:
    category = str(output.get("category", ""))
    intent = str(output.get("intent", ""))
    confidence = _safe_float(output.get("confidence"), default=0.0)

    checks = {
        "intent_check": _contains_any(intent, case.intent_contains),
        "category_check": category == case.expected_category,
        "confidence_check": confidence >= case.min_confidence,
    }

    return CaseEvaluation(
        case_id=case.case_id,
        expected={
            "category": case.expected_category,
            "min_confidence": case.min_confidence,
            "intent_contains": list(case.intent_contains),
        },
        actual={
            "intent": intent,
            "category": category,
            "subcategory": output.get("subcategory", ""),
            "summary": output.get("summary", ""),
            "next_action_type": output.get("next_action_type", ""),
            "confidence": confidence,
            "clarification_required": bool(output.get("clarification_required", False)),
            "clarification_questions": output.get("clarification_questions", []),
            "additional_issues": output.get("additional_issues", []),
        },
        checks=checks,
        passed=all(checks.values()),
        latency_ms=round(latency_ms, 2),
    )


def _evaluation_to_dict(evaluation: CaseEvaluation) -> dict[str, Any]:
    return {
        "case_id": evaluation.case_id,
        "expected": evaluation.expected,
        "actual": evaluation.actual,
        "checks": evaluation.checks,
        "pass": evaluation.passed,
        "latency_ms": evaluation.latency_ms,
        "error": evaluation.error,
    }


def run_test_suite(print_each_case: bool = True) -> dict[str, Any]:
    """Execute the AI test suite and return aggregate report."""
    from legal.ai_engine import understand_user_problem  # Imported post Django setup.

    results: list[CaseEvaluation] = []
    durations_ms: list[float] = []

    for case in TEST_CASES:
        start = time.perf_counter()
        try:
            output = understand_user_problem(case.user_input)
            duration_ms = (time.perf_counter() - start) * 1000
            durations_ms.append(duration_ms)
            evaluated = _evaluate_case(case, output, latency_ms=duration_ms)
        except Exception as error:  # noqa: BLE001 - per-case isolation is intentional.
            duration_ms = (time.perf_counter() - start) * 1000
            durations_ms.append(duration_ms)
            LOGGER.exception("Case %s failed with exception", case.case_id)
            evaluated = CaseEvaluation(
                case_id=case.case_id,
                expected={
                    "category": case.expected_category,
                    "min_confidence": case.min_confidence,
                    "intent_contains": list(case.intent_contains),
                },
                actual={
                    "intent": "",
                    "category": "",
                    "subcategory": "",
                    "summary": "",
                    "next_action_type": "",
                    "confidence": 0.0,
                    "clarification_required": True,
                    "clarification_questions": [],
                    "additional_issues": [],
                },
                checks={
                    "intent_check": False,
                    "category_check": False,
                    "confidence_check": False,
                },
                passed=False,
                latency_ms=round(duration_ms, 2),
                error=str(error),
            )

        results.append(evaluated)
        if print_each_case:
            print(json.dumps(_evaluation_to_dict(evaluated), ensure_ascii=True, indent=2))

    passed = sum(1 for item in results if item.passed)
    confidences = [float(item.actual.get("confidence", 0.0)) for item in results]

    p95_index = int(0.95 * (len(durations_ms) - 1)) if durations_ms else 0
    sorted_latencies = sorted(durations_ms)
    p95_value = sorted_latencies[p95_index] if sorted_latencies else 0.0

    summary = {
        "suite": "NyaySaathi AI Understanding",
        "total_cases": len(TEST_CASES),
        "passed_cases": passed,
        "failed_cases": len(TEST_CASES) - passed,
        "pass_rate": round((passed / len(TEST_CASES)) * 100, 2),
        "confidence_stats": {
            "avg": round(statistics.mean(confidences), 3),
            "min": round(min(confidences), 3),
            "max": round(max(confidences), 3),
        },
        "latency_ms": {
            "avg": round(statistics.mean(durations_ms), 2),
            "p95": round(p95_value, 2),
            "max": round(max(durations_ms), 2),
        },
    }

    print("\n=== TEST SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return {
        "summary": summary,
        "results": [_evaluation_to_dict(item) for item in results],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NyaySaathi AI understanding quality tests.")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional path to write full JSON report.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-case JSON output and print only summary.",
    )
    parser.add_argument(
        "--fail-on-fail",
        action="store_true",
        help="Exit with non-zero status if any case fails.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging failures.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _configure_logging(verbose=args.verbose)
    try:
        _bootstrap_django()
    except Exception as error:  # noqa: BLE001 - print user-friendly startup error.
        LOGGER.error("Bootstrap failed: %s", error)
        return 2

    # Real AI quality evaluation needs upstream model access.
    if not os.getenv("OPENAI_API_KEY"):
        LOGGER.error("OPENAI_API_KEY is missing. Set it before running the AI test suite.")
        return 2

    report = run_test_suite(print_each_case=not args.quiet)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=True, indent=2)
        LOGGER.info("Wrote report to %s", args.output)

    failed = int(report["summary"]["failed_cases"])
    if args.fail_on_fail and failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
