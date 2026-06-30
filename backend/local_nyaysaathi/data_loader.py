from __future__ import annotations

import json
from typing import Dict, List

from .config import DATA_FILES


def _safe_list(value):
    return value if isinstance(value, list) else []


def _normalize_case(record: Dict, language: str, source: str, idx: int) -> Dict:
    category = str(record.get("category", "Unknown"))
    subcategory = str(record.get("subcategory", "General Legal Issue"))
    description = str(record.get("problem_description", ""))

    descriptions = [str(x) for x in _safe_list(record.get("descriptions", []))]
    steps = [str(x) for x in _safe_list(record.get("workflow_steps", []))]
    documents = [str(x) for x in _safe_list(record.get("required_documents", []))]
    authorities = _safe_list(record.get("authorities", []))

    searchable_text = " ".join(
        [
            category,
            subcategory,
            description,
            " ".join(descriptions),
            " ".join(steps),
            " ".join(documents),
        ]
    ).strip()

    return {
        "id": f"{source}:{idx}",
        "language": language,
        "source": source,
        "category": category,
        "subcategory": subcategory,
        "problem_description": description,
        "descriptions": descriptions,
        "workflow_steps": steps,
        "required_documents": documents,
        "authorities": authorities,
        "online_portals": _safe_list(record.get("online_portals", [])),
        "helplines": _safe_list(record.get("helplines", [])),
        "searchable_text": searchable_text,
        "raw": record,
    }


def load_merged_cases() -> List[Dict]:
    merged: List[Dict] = []
    seen = set()

    for path, language in DATA_FILES:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            continue

        if not isinstance(records, list):
            continue

        for idx, record in enumerate(records):
            case = _normalize_case(record, language, path.name, idx)
            dedupe_key = (
                case["category"].strip().lower(),
                case["subcategory"].strip().lower(),
                case["problem_description"].strip().lower(),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            merged.append(case)

    return merged
