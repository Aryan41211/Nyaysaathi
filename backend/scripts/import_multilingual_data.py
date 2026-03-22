"""Import multilingual legal workflows into MongoDB.

Usage (from backend/):
  python scripts/import_multilingual_data.py
  python scripts/import_multilingual_data.py --wipe
  python scripts/import_multilingual_data.py --en ../data/nyaysaathi_en.json --hi ../data/nyaysaathi_hi.json --mr ../data/nyaysaathi_mr.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")

import django

django.setup()

from legal_cases.db_connection import get_collection
from legal_cases.services import invalidate_cache
from services.workflow_service import invalidate_workflow_cache

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_BACKEND_DIR = Path(__file__).resolve().parents[1]
BASE_REPO_DIR = BASE_BACKEND_DIR.parents[1]

DEFAULT_EN_CANDIDATES = [
    BASE_BACKEND_DIR / "data" / "nyaysaathi_en.json",
    BASE_BACKEND_DIR.parent / "dataset" / "legal_cases.json",
]
DEFAULT_HI_CANDIDATES = [
    BASE_BACKEND_DIR / "data" / "nyaysaathi_hi.json",
    BASE_REPO_DIR / "nyaysaathi_hindi.json",
]
DEFAULT_MR_CANDIDATES = [
    BASE_BACKEND_DIR / "data" / "nyaysaathi_mr.json",
    BASE_REPO_DIR / "nyaysaathi_marathi.json",
]

COLLECTION = "legal_workflows_multilingual"
_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9_\-]+")


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError(f"Dataset must be a JSON array: {path}")
    return [record for record in raw if isinstance(record, dict) and record.get("subcategory") and record.get("category")]


def _pick_first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _slugify(text: str) -> str:
    value = (text or "").strip().lower()
    value = _SPACE_RE.sub("_", value)
    value = _NON_WORD_RE.sub("", value)
    return value.strip("_")


def _normalized_documents(record: dict[str, Any]) -> list[str]:
    docs = record.get("documents_required")
    if isinstance(docs, list):
        return docs
    docs = record.get("required_documents")
    if isinstance(docs, list):
        return docs
    return []


def _normalize_translation(record: dict[str, Any]) -> dict[str, Any]:
    descriptions = list(record.get("descriptions") or [])
    return {
        "category": str(record.get("category") or "").strip(),
        "subcategory": str(record.get("subcategory") or "").strip(),
        "problem_description": str(record.get("problem_description") or "").strip(),
        "descriptions": descriptions,
        "workflow_steps": list(record.get("workflow_steps") or []),
        "documents_required": _normalized_documents(record),
        "required_documents": _normalized_documents(record),
        "authorities": list(record.get("authorities") or []),
        "escalation_path": list(record.get("escalation_path") or []),
        "complaint_template": str(record.get("complaint_template") or "").strip(),
        "online_portals": list(record.get("online_portals") or []),
        "helplines": list(record.get("helplines") or []),
    }


def _validate_lengths(en_rows: list[dict[str, Any]], hi_rows: list[dict[str, Any]], mr_rows: list[dict[str, Any]]) -> None:
    sizes = {"en": len(en_rows), "hi": len(hi_rows), "mr": len(mr_rows)}
    if len(set(sizes.values())) != 1:
        raise ValueError(f"Record count mismatch across languages: {sizes}")


def _build_document(index: int, en_row: dict[str, Any], hi_row: dict[str, Any], mr_row: dict[str, Any]) -> dict[str, Any]:
    en_category = str(en_row.get("category") or "")
    en_subcategory = str(en_row.get("subcategory") or "")
    category_id = _slugify(f"{en_category}_{en_subcategory}") or f"workflow_{index + 1:03d}"

    en_t = _normalize_translation(en_row)
    hi_t = _normalize_translation(hi_row)
    mr_t = _normalize_translation(mr_row)

    search_aliases = {
        "en": [en_t["category"], en_t["subcategory"], *en_t.get("descriptions", [])],
        "hi": [hi_t["category"], hi_t["subcategory"], *hi_t.get("descriptions", [])],
        "mr": [mr_t["category"], mr_t["subcategory"], *mr_t.get("descriptions", [])],
    }

    return {
        "category_id": category_id,
        "translations": {
            "en": en_t,
            "hi": hi_t,
            "mr": mr_t,
        },
        "search_aliases": search_aliases,
    }


def import_multilingual(en_path: Path, hi_path: Path, mr_path: Path, wipe: bool) -> None:
    en_rows = _load_json(en_path)
    hi_rows = _load_json(hi_path)
    mr_rows = _load_json(mr_path)

    _validate_lengths(en_rows, hi_rows, mr_rows)

    col = get_collection(COLLECTION)
    if wipe:
        col.drop()
        logger.warning("Dropped collection: %s", COLLECTION)

    col.create_index("category_id", unique=True)
    col.create_index("translations.en.category")
    col.create_index("translations.en.subcategory")
    col.create_index("translations.hi.category")
    col.create_index("translations.hi.subcategory")
    col.create_index("translations.mr.category")
    col.create_index("translations.mr.subcategory")

    inserted = 0
    updated = 0

    for idx, (en_row, hi_row, mr_row) in enumerate(zip(en_rows, hi_rows, mr_rows)):
        doc = _build_document(idx, en_row, hi_row, mr_row)
        result = col.update_one(
            {"category_id": doc["category_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1

    invalidate_workflow_cache()
    invalidate_cache()

    total = col.count_documents({})
    logger.info("Multilingual import complete: inserted=%d updated=%d total=%d", inserted, updated, total)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import multilingual NyaySaathi datasets into MongoDB")
    parser.add_argument("--en", type=Path, default=_pick_first_existing(DEFAULT_EN_CANDIDATES), help="English dataset path")
    parser.add_argument("--hi", type=Path, default=_pick_first_existing(DEFAULT_HI_CANDIDATES), help="Hindi dataset path")
    parser.add_argument("--mr", type=Path, default=_pick_first_existing(DEFAULT_MR_CANDIDATES), help="Marathi dataset path")
    parser.add_argument("--wipe", action="store_true", help="Drop multilingual collection before import")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        logger.info("Using datasets: en=%s hi=%s mr=%s", args.en, args.hi, args.mr)
        import_multilingual(args.en, args.hi, args.mr, args.wipe)
        return 0
    except Exception as exc:
        logger.error("Import failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
