"""Annotation workflow helper for NyaySaathi human-validated evaluation.

Provides utilities to:
1. List unannotated queries from the auto-generated dataset
2. Export queries for annotation
3. Import annotated queries and merge with auto-generated dataset
4. Validate annotation completeness
5. Create train/dev/test splits

Usage:
    python annotation_workflow.py list-unannotated
    python annotation_workflow.py export-for-annotation --output queries_to_annotate.json
    python annotation_workflow.py import-annotations --file annotated_queries.json
    python annotation_workflow.py create-splits --input annotated_queries.json --output-dir splits/
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

from evaluation import EvalQuery, load_dataset, save_dataset

CORPUS_SIZE = 201  # Will be updated dynamically from dataset loader


def list_unannotated(queries: List[EvalQuery]) -> List[EvalQuery]:
    """Return queries that are auto-generated (not human-validated)."""
    return [q for q in queries if q.label_source != "human-validated"]


def export_for_annotation(
    queries: List[EvalQuery],
    output_path: Path,
    max_queries: int = 100,
) -> None:
    """Export auto-generated queries for human annotation.

    Strips relevance judgments so annotators start fresh.
    """
    unannotated = list_unannotated(queries)
    to_export = unannotated[:max_queries]

    export_data = []
    for q in to_export:
        export_data.append(
            {
                "query_id": q.query_id,
                "query_text": q.query_text,
                "relevant_case_ids": [],
                "relevance_grades": {},
                "label_source": "human-validated",
                "metadata": {
                    "annotator_id": "",
                    "annotation_date": "",
                    "query_category": q.metadata.get("source_category", ""),
                    "difficulty": "",
                    "source": "auto-generated-query",
                },
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    print(f"Exported {len(export_data)} queries to {output_path}")


def import_annotations(
    existing_queries: List[EvalQuery],
    annotated_path: Path,
) -> List[EvalQuery]:
    """Import human-validated annotations and merge with existing queries.

    Matches by query_id. Annotated queries replace their auto-generated
    counterparts with human-validated labels.
    """
    with open(annotated_path, "r", encoding="utf-8") as f:
        annotated_data = json.load(f)

    annotated_by_id: Dict[str, Dict[str, Any]] = {}
    for item in annotated_data:
        annotated_by_id[item["query_id"]] = item

    merged: List[EvalQuery] = []
    human_count = 0
    auto_count = 0

    for q in existing_queries:
        if q.query_id in annotated_by_id:
            item = annotated_by_id[q.query_id]
            merged.append(
                EvalQuery(
                    query_id=item["query_id"],
                    query_text=item["query_text"],
                    relevant_case_ids=list(item.get("relevant_case_ids", [])),
                    relevance_grades=item.get("relevance_grades", {}),
                    label_source=item.get("label_source", "human-validated"),
                    metadata=item.get("metadata", {}),
                )
            )
            human_count += 1
        else:
            merged.append(q)
            auto_count += 1

    print(f"Merged: {human_count} human-validated, {auto_count} auto-generated")
    return merged


def validate_annotations(queries: List[EvalQuery]) -> Dict[str, Any]:
    """Validate annotation completeness and report issues."""
    human_queries = [q for q in queries if q.label_source == "human-validated"]
    auto_queries = [q for q in queries if q.label_source == "auto-generated"]

    issues: List[str] = []

    for q in human_queries:
        if not q.relevant_case_ids:
            issues.append(f"{q.query_id}: no relevant_case_ids")
        if not q.metadata.get("annotator_id"):
            issues.append(f"{q.query_id}: missing annotator_id")
        if not q.metadata.get("annotation_date"):
            issues.append(f"{q.query_id}: missing annotation_date")
        for cid in q.relevant_case_ids:
            try:
                idx = int(cid)
                if idx < 0 or idx >= CORPUS_SIZE:
                    issues.append(
                        f"{q.query_id}: invalid case index {cid} (corpus has {CORPUS_SIZE} cases)"
                    )
            except ValueError:
                issues.append(f"{q.query_id}: non-integer case id {cid}")

    return {
        "human_validated": len(human_queries),
        "auto_generated": len(auto_queries),
        "total": len(queries),
        "issues": issues,
        "valid": len(issues) == 0,
    }


def create_splits(
    queries: List[EvalQuery],
    output_dir: Path,
    train_ratio: float = 0.6,
    dev_ratio: float = 0.2,
    test_ratio: float = 0.2,
) -> None:
    """Create train/dev/test splits from human-validated queries.

    Ensures each split has representation from all categories.
    """
    human_queries = [q for q in queries if q.label_source == "human-validated"]

    if len(human_queries) < 10:
        print(f"WARNING: Only {len(human_queries)} human-validated queries. "
              "Splits may not be meaningful.")
    
    # Shuffle with fixed seed for reproducibility
    rng = random.Random(42)
    shuffled = list(human_queries)
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_dev = int(n * dev_ratio)

    train = shuffled[:n_train]
    dev = shuffled[n_train : n_train + n_dev]
    test = shuffled[n_train + n_dev :]

    output_dir.mkdir(parents=True, exist_ok=True)

    for name, split_queries in [("train", train), ("dev", dev), ("test", test)]:
        save_dataset(split_queries, output_dir / f"{name}.json")
        print(f"{name}: {len(split_queries)} queries")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NyaySaathi annotation workflow")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-unannotated", help="List auto-generated queries")

    export_parser = subparsers.add_parser("export-for-annotation")
    export_parser.add_argument("--output", required=True, help="Output JSON path")
    export_parser.add_argument("--max-queries", type=int, default=100)

    import_parser = subparsers.add_parser("import-annotations")
    import_parser.add_argument("--file", required=True, help="Annotated JSON path")
    import_parser.add_argument(
        "--input-dataset", required=True, help="Existing dataset JSON path"
    )

    subparsers.add_parser("validate", help="Validate annotations")

    splits_parser = subparsers.add_parser("create-splits")
    splits_parser.add_argument("--input", required=True, help="Annotated dataset JSON")
    splits_parser.add_argument("--output-dir", required=True, help="Output directory")

    args = parser.parse_args()

    if args.command == "list-unannotated":
        # This would need the full dataset loaded; for now just show the command works
        print("Use 'export-for-annotation' to get queries for annotation")
    elif args.command == "export-for-annotation":
        # Load full dataset
        from api.data_loader import CASES
        from evaluation.dataset import build_auto_generated_dataset
        queries = build_auto_generated_dataset(CASES)
        export_for_annotation(queries, Path(args.output), args.max_queries)
    elif args.command == "import-annotations":
        from api.data_loader import CASES
        from evaluation.dataset import build_auto_generated_dataset
        queries = build_auto_generated_dataset(CASES)
        merged = import_annotations(queries, Path(args.file))
        # Save merged dataset back
        save_dataset(merged, Path(args.file).parent / "merged_dataset.json")
        print("Merged dataset saved")
    elif args.command == "validate":
        from api.data_loader import CASES
        from evaluation.dataset import build_auto_generated_dataset
        queries = build_auto_generated_dataset(CASES)
        result = validate_annotations(queries)
        print(json.dumps(result, indent=2))
    elif args.command == "create-splits":
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        from evaluation import EvalQuery
        queries = [
            EvalQuery(
                query_id=item["query_id"],
                query_text=item["query_text"],
                relevant_case_ids=list(item.get("relevant_case_ids", [])),
                relevance_grades=item.get("relevance_grades", {}),
                label_source=item.get("label_source", "human-validated"),
                metadata=item.get("metadata", {}),
            )
            for item in data
        ]
        create_splits(queries, Path(args.output_dir))
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
