"""Continuous improvement loop for NyaySaathi intent and retrieval quality.

Reads production training events + user feedback and emits actionable updates:
- retraining triggers
- intent update candidates
- synonym dictionary update candidates
"""

from __future__ import annotations

import json
import os
import sys
import importlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _bootstrap_django() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
    django_mod = importlib.import_module("django")
    setup = getattr(django_mod, "setup")
    setup()


def _thresholds() -> dict[str, float]:
    return {
        "min_events_for_retrain": float(os.getenv("RETRAIN_MIN_EVENTS", "250")),
        "fallback_rate_trigger": float(os.getenv("RETRAIN_FALLBACK_RATE", "0.30")),
        "low_confidence_rate_trigger": float(os.getenv("RETRAIN_LOW_CONF_RATE", "0.35")),
        "intent_error_trigger": float(os.getenv("INTENT_UPDATE_ERROR_RATE", "0.25")),
        "synonym_min_occurrences": float(os.getenv("SYNONYM_MIN_OCCURRENCES", "3")),
    }


def _build_report(events: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    fallback_count = sum(1 for row in events if str(row.get("decision", "")).lower() == "fallback")
    low_conf_count = sum(1 for row in events if str(row.get("confidence", "")).lower() == "low")

    feedback_with_corrections = [row for row in feedback if str(row.get("correction_text", "")).strip()]

    corrected_intents = Counter(
        str(row.get("corrected_intent", "")).strip()
        for row in feedback_with_corrections
        if str(row.get("corrected_intent", "")).strip()
    )

    suggestion_terms = Counter()
    for row in feedback_with_corrections:
        correction = str(row.get("correction_text", "")).strip().lower()
        for token in correction.split():
            if len(token) >= 4:
                suggestion_terms[token] += 1

    thresholds = _thresholds()
    fallback_rate = fallback_count / max(1, total)
    low_conf_rate = low_conf_count / max(1, total)

    retrain_embeddings = (
        total >= thresholds["min_events_for_retrain"]
        and (fallback_rate >= thresholds["fallback_rate_trigger"] or low_conf_rate >= thresholds["low_confidence_rate_trigger"])
    )

    intent_update_needed = len(feedback_with_corrections) > 0 and (
        len(feedback_with_corrections) / max(1, total) >= thresholds["intent_error_trigger"]
    )

    synonym_candidates = [
        term
        for term, count in suggestion_terms.items()
        if count >= thresholds["synonym_min_occurrences"]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_training_events": total,
        "total_feedback_events": len(feedback),
        "corrected_feedback_events": len(feedback_with_corrections),
        "fallback_rate": round(fallback_rate, 4),
        "low_confidence_rate": round(low_conf_rate, 4),
        "intent_correction_distribution": dict(corrected_intents.most_common(20)),
        "retraining_plan": {
            "retrain_embeddings": retrain_embeddings,
            "update_intents": intent_update_needed,
            "update_synonyms": len(synonym_candidates) > 0,
        },
        "synonym_candidates": synonym_candidates[:100],
        "next_actions": [
            "Rebuild sentence embeddings + FAISS index when retrain_embeddings is true.",
            "Append corrected queries to supervised intent exemplars when update_intents is true.",
            "Review synonym_candidates and add approved tokens to query normalizer map.",
        ],
    }


def main() -> None:
    _bootstrap_django()

    from legal.query_logger import get_feedback_samples, get_training_events

    events = get_training_events(limit=5000, unresolved_only=False)
    feedback = get_feedback_samples(limit=5000, corrections_only=False)

    report = _build_report(events, feedback)

    backend_root = Path(__file__).resolve().parents[1]
    out_dir = backend_root / "data" / "improvement_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest_improvement_report.json"
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Saved improvement report at: {out_file}")


if __name__ == "__main__":
    main()
