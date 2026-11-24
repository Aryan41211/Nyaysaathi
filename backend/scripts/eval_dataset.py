"""NyaySaathi human-validated evaluation dataset builder.

Creates a JSONL file of human-validated evaluation queries with relevance
judgments. Each query includes:
- query_id, query_text, relevant_case_ids (indices into expanded corpus)
- relevance_grades (0-3 per case), label_source="human-validated"
- annotator metadata

Usage:
    python scripts/create_eval_dataset.py --init  # create empty template
    python scripts/create_eval_dataset.py --add   # add a query interactively
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = REPO_ROOT / "backend"
DATA_FILE = BACKEND / "dataset" / "expanded_cases.json"
EVAL_FILE = BACKEND / "dataset" / "human_eval_queries.jsonl"


def _load_cases() -> List[Dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_index(cases: List[Dict]) -> Dict[str, int]:
    """Map case id -> index in corpus."""
    return {str(c.get("id", "")): i for i, c in enumerate(cases)}


def init_dataset() -> None:
    """Create an empty evaluation dataset file with a header comment."""
    if EVAL_FILE.exists():
        print(f"{EVAL_FILE} already exists; not overwriting.")
        return
    header = {
        "_meta": {
            "description": "Human-validated retrieval evaluation queries.",
            "format": "JSONL, one object per line.",
            "fields": [
                "query_id", "query_text", "relevant_case_ids",
                "relevance_grades", "label_source",
                "annotator", "category", "difficulty",
            ],
        },
    }
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
    print(f"Created {EVAL_FILE}")


def add_query(
    query_id: str,
    query_text: str,
    relevant_case_ids: List[str],
    relevance_grades: Dict[str, int],
    annotator: str,
    category: str,
    difficulty: str,
) -> None:
    """Append a single evaluated query to the JSONL file."""
    record = {
        "query_id": query_id,
        "query_text": query_text,
        "relevant_case_ids": relevant_case_ids,
        "relevance_grades": relevance_grades,
        "label_source": "human-validated",
        "annotator": annotator,
        "category": category,
        "difficulty": difficulty,
    }
    with open(EVAL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Added query {query_id}")


def validate() -> Dict[str, Any]:
    """Validate the evaluation dataset against the corpus."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)
    index = _build_index(cases)

    errors: List[str] = []
    n_queries = 0
    n_with_grades = 0
    categories: Dict[str, int] = {}

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"Line {line_no}: invalid JSON")
                    continue
                if "_meta" in obj:
                    continue
                n_queries += 1
            qid = obj.get("query_id", f"line_{line_no}")
            cat = obj.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            if obj.get("label_source") == "human-validated":
                n_with_grades += 1
            # Check case ids exist
            for cid in obj.get("relevant_case_ids", []):
                if cid not in index:
                    # Try as index position (cases don't have explicit IDs)
                    try:
                        idx = int(cid)
                        if idx < 0 or idx >= len(cases):
                            errors.append(f"Line {line_no}: case index {cid} out of range (0-{len(cases)-1})")
                    except ValueError:
                        errors.append(f"Line {line_no}: unknown case id '{cid}'")
                else:
                    errors.append(f"Line {line_no}: unknown case id '{cid}'")
            # Check grades match
            for cid, grade in obj.get("relevance_grades", {}).items():
                try:
                    idx = int(cid)
                    if idx < 0 or idx >= len(cases):
                        errors.append(f"Line {line_no}: grade for unknown case index '{cid}'")
                except ValueError:
                    errors.append(f"Line {line_no}: grade for unknown case '{cid}'")
                if not isinstance(grade, int) or grade < 0 or grade > 3:
                    errors.append(f"Line {line_no}: invalid grade {grade} for '{cid}'")

    return {
        "n_queries": n_queries,
        "human_validated": n_with_grades,
        "categories": categories,
        "errors": errors,
        "valid": len(errors) == 0,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NyaySaathi eval dataset tool")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Create empty evaluation dataset file")

    add_p = sub.add_parser("add", help="Add a single evaluation query")
    add_p.add_argument("--query-id", required=True)
    add_p.add_argument("--query-text", required=True)
    add_p.add_argument("--relevant-ids", required=True, help="Comma-separated case ids")
    add_p.add_argument("--grades", default="", help="Comma-separated grade:int pairs")
    add_p.add_argument("--annotator", required=True)
    add_p.add_argument("--category", required=True)
    add_p.add_argument("--difficulty", required=True)

    sub.add_parser("validate", help="Validate the evaluation dataset")

    args = parser.parse_args()

    if args.command == "init":
        init_dataset()
    elif args.command == "add":
        grades = {}
        if args.grades:
            for item in args.grades.split(","):
                k, v = item.split(":")
                grades[k.strip()] = int(v.strip())
        add_query(
            query_id=args.query_id,
            query_text=args.query_text,
            relevant_case_ids=[x.strip() for x in args.relevant_ids.split(",")],
            relevance_grades=grades,
            annotator=args.annotator,
            category=args.category,
            difficulty=args.difficulty,
        )
    elif args.command == "validate":
        result = validate()
        print(json.dumps(result, indent=2))
        if not result["valid"]:
            return 1
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
