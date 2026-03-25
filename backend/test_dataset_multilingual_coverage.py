"""Dataset-wide multilingual retrieval coverage test.

Validates whether Hindi/Marathi workflow titles retrieve the corresponding
English workflow within top-k semantic results.

Run from backend/:
  venv/Scripts/python.exe test_dataset_multilingual_coverage.py --top-k 5
  venv/Scripts/python.exe test_dataset_multilingual_coverage.py --top-k 5 --limit 60
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from search.semantic_engine import SemanticSearchEngine


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise ValueError(f"Dataset is not a JSON array: {path}")
    return [row for row in raw if isinstance(row, dict)]


def _pick_existing(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _normalized_text(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _evaluate_language(
    engine: SemanticSearchEngine,
    base_cases: list[dict[str, Any]],
    localized_rows: list[dict[str, Any]],
    top_k: int,
    language_name: str,
) -> tuple[int, int, list[dict[str, Any]]]:
    hits = 0
    total = 0
    misses: list[dict[str, Any]] = []

    for i, (base, local) in enumerate(zip(base_cases, localized_rows)):
        query = str(local.get("subcategory") or "").strip()
        expected = _normalized_text(str(base.get("subcategory") or ""))
        if not query or not expected:
            continue

        total += 1
        results, _ = engine.semantic_search(query, top_k=top_k)
        predicted = [_normalized_text(str(r.get("subcategory") or "")) for r in results]

        matched = expected in predicted
        if matched:
            hits += 1
        else:
            misses.append(
                {
                    "index": i,
                    "language": language_name,
                    "query": query,
                    "expected_subcategory": base.get("subcategory", ""),
                    "predicted_top": [r.get("subcategory", "") for r in results[:3]],
                }
            )

    return hits, total, misses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multilingual retrieval coverage across full dataset")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k semantic candidates considered a hit")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick runs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    backend_dir = Path(__file__).resolve().parent
    repo_dir = backend_dir.parent

    en_path = _pick_existing([
        backend_dir / "data" / "nyaysaathi_en.json",
        repo_dir / "dataset" / "legal_cases.json",
    ])
    hi_path = _pick_existing([
        backend_dir / "data" / "nyaysaathi_hi.json",
        repo_dir / "nyaysaathi_hindi.json",
    ])
    mr_path = _pick_existing([
        backend_dir / "data" / "nyaysaathi_mr.json",
        repo_dir / "nyaysaathi_marathi.json",
    ])

    en_rows = _load_rows(en_path)
    hi_rows = _load_rows(hi_path)
    mr_rows = _load_rows(mr_path)

    size = min(len(en_rows), len(hi_rows), len(mr_rows))
    if args.limit and args.limit > 0:
        size = min(size, args.limit)

    if size == 0:
        print("No records available for coverage test.")
        return 1

    en_rows = en_rows[:size]
    hi_rows = hi_rows[:size]
    mr_rows = mr_rows[:size]

    engine = SemanticSearchEngine(cache_dir=backend_dir / "search_cache")
    engine.ensure_index(en_rows)

    hi_hits, hi_total, hi_misses = _evaluate_language(engine, en_rows, hi_rows, args.top_k, "Hindi")
    mr_hits, mr_total, mr_misses = _evaluate_language(engine, en_rows, mr_rows, args.top_k, "Marathi")

    hi_rate = (hi_hits / hi_total) if hi_total else 0.0
    mr_rate = (mr_hits / mr_total) if mr_total else 0.0
    overall_hits = hi_hits + mr_hits
    overall_total = hi_total + mr_total
    overall_rate = (overall_hits / overall_total) if overall_total else 0.0

    print("=== DATASET MULTILINGUAL COVERAGE ===")
    print(f"Records tested: {size}")
    print(f"Top-k threshold: {args.top_k}")
    print(f"Hindi hit rate:   {hi_hits}/{hi_total} ({hi_rate:.2%})")
    print(f"Marathi hit rate: {mr_hits}/{mr_total} ({mr_rate:.2%})")
    print(f"Overall hit rate: {overall_hits}/{overall_total} ({overall_rate:.2%})")

    if hi_misses or mr_misses:
        print("\nSample misses (first 10):")
        for miss in (hi_misses + mr_misses)[:10]:
            print(
                f"- [{miss['language']}] idx={miss['index']} query={miss['query']}\n"
                f"  expected={miss['expected_subcategory']}\n"
                f"  predicted_top={miss['predicted_top']}"
            )

    # Soft quality gate for launch readiness checks.
    # Adjust threshold based on product expectations.
    quality_gate = 0.80
    if overall_rate < quality_gate:
        print(f"\nCoverage below gate ({quality_gate:.0%}). Improve aliases/query normalization before launch.")
        return 2

    print("\nCoverage meets quality gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
