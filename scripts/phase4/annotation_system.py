"""
NyayaSaathi Phase 4 — Legal Retrieval Annotation System.

Provides:
1. Annotation schema for graded relevance judgments (0-3).
2. Candidate query generation from the legal corpus.
3. Annotation workflow: query creation, document search, relevance labeling.
4. Train/validation/test split creation.
5. Inter-annotator agreement (Cohen's kappa, Krippendorff's alpha).
6. Export of human-validated evaluation dataset.

Usage:
    python annotation_system.py generate-candidates --output candidate_queries.jsonl
    python annotation_system.py export-for-annotation --input candidate_queries.jsonl --output annotation_batch.jsonl
    python annotation_system.py import-annotations --input annotated_queries.jsonl --output validated_dataset.jsonl
    python annotation_system.py create-splits --input validated_dataset.jsonl --output-dir splits/
    python annotation_system.py compute-agreement --input annotated_queries.jsonl
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.api.data_loader import CASES

BACKEND = Path(__file__).resolve().parent.parent.parent
PHASE4_DIR = BACKEND / "backend" / "evaluation" / "phase4"
ANNOTATIONS_DIR = PHASE4_DIR / "annotations"
PHASE4_DIR.mkdir(parents=True, exist_ok=True)
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Annotation schema
# ---------------------------------------------------------------------------

@dataclass
class AnnotationCandidate:
    """A candidate query awaiting human annotation."""
    query_id: str
    query_text: str
    language: str  # en, hi, mr, hinglish
    category: str
    subcategory: str
    difficulty: str  # easy, medium, hard
    source: str  # seed, synthetic, user-submitted
    case_candidates: list[dict[str, Any]]  # candidate cases for relevance labeling
    created_at: str
    annotator: str | None = None
    annotated_at: str | None = None
    relevant_case_ids: list[str] = field(default_factory=list)
    relevance_grades: dict[str, int] = field(default_factory=dict)  # case_id -> 0-3
    adjudicator: str | None = None
    adjudicated_at: str | None = None
    adjudication_status: str = "pending"  # pending, approved, rejected, needs_revision
    label_source: str = "candidate"  # candidate, human-validated, auto-generated


@dataclass
class ValidatedQuery:
    """A fully human-validated evaluation query."""
    query_id: str
    query_text: str
    language: str
    category: str
    subcategory: str
    difficulty: str
    source: str
    relevant_case_ids: list[str]
    relevance_grades: dict[str, int]
    annotator: str
    annotated_at: str
    adjudicator: str | None
    adjudicated_at: str | None
    adjudication_status: str
    label_source: str = "human-validated"


# ---------------------------------------------------------------------------
# Corpus utilities
# ---------------------------------------------------------------------------

def _case_content_key(case: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(case.get("category", "")).strip().lower(),
        str(case.get("subcategory", "")).strip().lower(),
        str(case.get("problem_description", "")).strip().lower(),
    )


def build_deduped_corpus(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate cases by content key, returning unique cases."""
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for case in cases:
        key = _case_content_key(case)
        if key not in seen:
            seen.add(key)
            unique.append(case)
    return unique


def case_to_searchable_text(case: dict[str, Any]) -> str:
    """Build searchable text from a case."""
    chunks = [
        str(case.get("category", "")),
        str(case.get("subcategory", "")),
        str(case.get("problem_description", "")),
    ]
    for key in ("descriptions", "workflow_steps"):
        val = case.get(key, [])
        if isinstance(val, list):
            chunks.append(" ".join(str(x) for x in val))
    return " ".join(chunk for chunk in chunks if chunk).strip()


# ---------------------------------------------------------------------------
# Candidate query generation
# ---------------------------------------------------------------------------

def _query_variants(problem: str, subcategory: str, rng: random.Random) -> list[str]:
    """Generate multiple query formulations from a single problem description."""
    variants: list[str] = []

    # Variant 1: First clause of problem description
    first_clause = problem.split(".")[0].strip() if problem else ""
    if len(first_clause) >= 10:
        variants.append(first_clause)

    # Variant 2: Question format
    if problem:
        variants.append(f"How do I handle {problem[:120].strip()}?")

    # Variant 3: Short keyword form
    if problem:
        words = problem.split()[:8]
        variants.append(" ".join(words))

    # Variant 4: "What should I do" format
    if problem:
        variants.append(f"What should I do about {problem[:100].strip()}?")

    # Variant 5: Hinglish-ish informal variant (for multilingual coverage)
    if problem:
        variants.append(f"Mera case hai: {problem[:100].strip()} kya karna chahiye?")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            unique.append(v)

    return unique if unique else [f"{subcategory} legal query"]


def generate_candidate_queries(
    cases: list[dict[str, Any]],
    n_per_category: int = 50,
) -> list[AnnotationCandidate]:
    """Generate candidate evaluation queries from the corpus.

    For each subcategory, generates multiple query formulations derived from
    the problem description. These are CANDIDATES — they need human annotation.
    """
    rng = random.Random(RANDOM_SEED)

    # Group cases by subcategory
    subcat_to_cases: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        subcat = str(case.get("subcategory", "Unknown"))
        subcat_to_cases.setdefault(subcat, []).append(case)

    candidates: list[AnnotationCandidate] = []
    query_counter = 0

    for subcategory, subcat_cases in sorted(subcat_to_cases.items()):
        category = subcat_cases[0].get("category", "Unknown")
        n = min(n_per_category, len(subcat_cases))
        selected = rng.sample(subcat_cases, n)

        for case in selected:
            problem = str(case.get("problem_description", ""))
            variants = _query_variants(problem, subcategory, rng)

            for variant_idx, query_text in enumerate(variants):
                query_counter += 1

                # Candidate cases: same subcategory cases (for human to label relevance)
                candidate_cases = []
                for c in subcat_cases:
                    candidate_cases.append({
                        "case_id": str(cases.index(c)),
                        "category": c.get("category", ""),
                        "subcategory": c.get("subcategory", ""),
                        "problem_description": c.get("problem_description", "")[:200],
                        "searchable_text": case_to_searchable_text(c)[:500],
                    })

                candidates.append(AnnotationCandidate(
                    query_id=f"cand-{query_counter:04d}",
                    query_text=query_text,
                    language="en",
                    category=str(category),
                    subcategory=str(subcategory),
                    difficulty=rng.choice(["easy", "medium", "hard"]),
                    source="seed",
                    case_candidates=candidate_cases[:10],
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))

    return candidates


def save_candidates(candidates: list[AnnotationCandidate], output_path: Path) -> None:
    """Save candidate queries to JSONL for human annotation."""
    with open(output_path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    print(f"Saved {len(candidates)} candidate queries to {output_path}")


# ---------------------------------------------------------------------------
# Annotation import and validation
# ---------------------------------------------------------------------------

def import_annotations(
    input_path: Path,
    deduped_cases: list[dict[str, Any]],
) -> list[ValidatedQuery]:
    """Import annotated queries and validate them against the deduped corpus."""
    # Build mapping from expanded case index -> deduped case index
    expanded_to_deduped: dict[int, int] = {}
    deduped_keys = {_case_content_key(c): i for i, c in enumerate(deduped_cases)}

    # We need the expanded cases to build the mapping. Load them.
    expanded_path = BACKEND / "backend" / "dataset" / "expanded_cases.json"
    with open(expanded_path, "r", encoding="utf-8") as f:
        expanded_cases = json.load(f)

    for orig_idx, case in enumerate(expanded_cases):
        key = _case_content_key(case)
        if key in deduped_keys:
            expanded_to_deduped[orig_idx] = deduped_keys[key]

    validated: list[ValidatedQuery] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            # Map case IDs from expanded to deduped corpus
            mapped_ids = []
            for cid_str in obj.get("relevant_case_ids", []):
                orig_idx = int(cid_str)
                if orig_idx in expanded_to_deduped:
                    mapped_ids.append(str(expanded_to_deduped[orig_idx]))

            validated.append(ValidatedQuery(
                query_id=obj["query_id"],
                query_text=obj["query_text"],
                language=obj.get("language", "en"),
                category=obj.get("category", ""),
                subcategory=obj.get("subcategory", ""),
                difficulty=obj.get("difficulty", "medium"),
                source=obj.get("source", "human-validated"),
                relevant_case_ids=mapped_ids,
                relevance_grades=obj.get("relevance_grades", {}),
                annotator=obj.get("annotator", "unknown"),
                annotated_at=obj.get("annotated_at", datetime.now(timezone.utc).isoformat()),
                adjudicator=obj.get("adjudicator"),
                adjudicated_at=obj.get("adjudicated_at"),
                adjudication_status=obj.get("adjudication_status", "pending"),
            ))

    print(f"Imported {len(validated)} validated queries")
    return validated


def save_validated(queries: list[ValidatedQuery], output_path: Path) -> None:
    """Save validated queries to JSONL."""
    with open(output_path, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(asdict(q), ensure_ascii=False) + "\n")
    print(f"Saved {len(queries)} validated queries to {output_path}")


# ---------------------------------------------------------------------------
# Train/validation/test splits
# ---------------------------------------------------------------------------

def create_splits(
    queries: list[ValidatedQuery],
    output_dir: Path,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
) -> None:
    """Create train/validation/test splits with category stratification."""
    rng = random.Random(RANDOM_SEED)

    # Group by category for stratified splits
    cat_to_queries: dict[str, list[ValidatedQuery]] = {}
    for q in queries:
        cat_to_queries.setdefault(q.category, []).append(q)

    output_dir.mkdir(parents=True, exist_ok=True)

    train: list[ValidatedQuery] = []
    val: list[ValidatedQuery] = []
    test: list[ValidatedQuery] = []

    for category, cat_queries in cat_to_queries.items():
        rng.shuffle(cat_queries)
        n = len(cat_queries)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))
        n_test = n - n_train - n_val
        if n_test < 1 and n >= 3:
            n_test = 1
            n_val = n - n_train - n_test

        train.extend(cat_queries[:n_train])
        val.extend(cat_queries[n_train:n_train + n_val])
        test.extend(cat_queries[n_train + n_val:])

    for name, split_queries in [("train", train), ("val", val), ("test", test)]:
        save_validated(split_queries, output_dir / f"{name}.jsonl")
        print(f"{name}: {len(split_queries)} queries")


# ---------------------------------------------------------------------------
# Inter-annotator agreement
# ---------------------------------------------------------------------------

def compute_cohens_kappa(
    annotations_a: dict[str, int],
    annotations_b: dict[str, int],
    n_categories: int = 4,  # grades 0-3
) -> float:
    """Compute Cohen's kappa between two annotators on shared case IDs."""
    shared_ids = sorted(set(annotations_a.keys()) & set(annotations_b.keys()))
    if not shared_ids:
        return 0.0

    ratings_a = [annotations_a[cid] for cid in shared_ids]
    ratings_b = [annotations_b[cid] for cid in shared_ids]

    n = len(shared_ids)
    # Observed agreement
    agree = sum(1 for a, b in zip(ratings_a, ratings_b) if a == b)
    po = agree / n

    # Expected agreement by chance
    prob_a = [sum(1 for r in ratings_a if r == k) / n for k in range(n_categories)]
    prob_b = [sum(1 for r in ratings_b if r == k) / n for k in range(n_categories)]
    pe = sum(prob_a[k] * prob_b[k] for k in range(n_categories))

    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def compute_krippendorff_alpha(
    annotations: list[dict[str, int]],
    n_categories: int = 4,
) -> float:
    """Compute Krippendorff's alpha for multiple annotators.

    Each element of annotations is a dict mapping case_id -> grade.
    """
    # Collect all case IDs annotated by at least 2 annotators
    case_to_ratings: dict[str, list[int]] = {}
    for ann in annotations:
        for cid, grade in ann.items():
            case_to_ratings.setdefault(cid, []).append(grade)

    # Filter to cases with >= 2 annotations
    pairable = {cid: ratings for cid, ratings in case_to_ratings.items() if len(ratings) >= 2}
    if not pairable:
        return 0.0

    # Observed disagreement: average pairwise disagreement within each case
    total_disagreement = 0.0
    total_pairs = 0
    for ratings in pairable.values():
        for i in range(len(ratings)):
            for j in range(i + 1, len(ratings)):
                total_disagreement += (ratings[i] - ratings[j]) ** 2
                total_pairs += 1

    do = total_disagreement / total_pairs if total_pairs > 0 else 0.0

    # Expected disagreement by chance
    all_ratings = [r for ratings in pairable.values() for r in ratings]
    n = len(all_ratings)
    prob_k = [sum(1 for r in all_ratings if r == k) / n for k in range(n_categories)]
    de = sum(
        prob_k[i] * prob_k[j] * (i - j) ** 2
        for i in range(n_categories)
        for j in range(n_categories)
    )

    if de == 0.0:
        return 1.0 if do == 0.0 else 0.0
    return 1.0 - (do / de)


def compute_agreement_report(input_path: Path) -> dict[str, Any]:
    """Compute inter-annotator agreement from annotated queries."""
    annotator_ratings: dict[str, dict[str, int]] = {}
    all_annotations: list[dict[str, int]] = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            annotator = obj.get("annotator", "unknown")
            grades = obj.get("relevance_grades", {})
            annotator_ratings.setdefault(annotator, {}).update(grades)
            all_annotations.append(grades)

    report: dict[str, Any] = {
        "annotators": list(annotator_ratings.keys()),
        "n_annotators": len(annotator_ratings),
        "n_queries": len(all_annotations),
    }

    # Pairwise Cohen's kappa
    annotators = list(annotator_ratings.keys())
    pairwise: dict[str, float] = {}
    for i in range(len(annotators)):
        for j in range(i + 1, len(annotators)):
            key = f"{annotators[i]}_vs_{annotators[j]}"
            pairwise[key] = round(
                compute_cohens_kappa(
                    annotator_ratings[annotators[i]],
                    annotator_ratings[annotators[j]],
                ),
                4,
            )
    report["pairwise_cohens_kappa"] = pairwise

    # Krippendorff's alpha
    report["krippendorff_alpha"] = round(
        compute_krippendorff_alpha(all_annotations), 4
    )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NyayaSaathi Phase 4 Annotation System")
    subparsers = parser.add_subparsers(dest="command")

    gen = subparsers.add_parser("generate-candidates")
    gen.add_argument("--output", required=True, help="Output JSONL path")
    gen.add_argument("--n-per-category", type=int, default=30)

    imp = subparsers.add_parser("import-annotations")
    imp.add_argument("--input", required=True, help="Annotated JSONL path")
    imp.add_argument("--output", required=True, help="Validated dataset JSONL path")

    split = subparsers.add_parser("create-splits")
    split.add_argument("--input", required=True, help="Validated dataset JSONL path")
    split.add_argument("--output-dir", required=True, help="Output directory for splits")

    agree = subparsers.add_parser("compute-agreement")
    agree.add_argument("--input", required=True, help="Annotated JSONL path")

    args = parser.parse_args()

    deduped_cases = build_deduped_corpus(CASES)
    print(f"Loaded {len(deduped_cases)} deduplicated cases")

    if args.command == "generate-candidates":
        candidates = generate_candidate_queries(deduped_cases, args.n_per_category)
        save_candidates(candidates, Path(args.output))

    elif args.command == "import-annotations":
        validated = import_annotations(Path(args.input), deduped_cases)
        save_validated(validated, Path(args.output))

    elif args.command == "create-splits":
        with open(args.input, "r", encoding="utf-8") as f:
            queries = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                queries.append(ValidatedQuery(
                    query_id=obj["query_id"],
                    query_text=obj["query_text"],
                    language=obj.get("language", "en"),
                    category=obj.get("category", ""),
                    subcategory=obj.get("subcategory", ""),
                    difficulty=obj.get("difficulty", "medium"),
                    source=obj.get("source", "human-validated"),
                    relevant_case_ids=obj.get("relevant_case_ids", []),
                    relevance_grades=obj.get("relevance_grades", {}),
                    annotator=obj.get("annotator", "unknown"),
                    annotated_at=obj.get("annotated_at", ""),
                    adjudicator=obj.get("adjudicator"),
                    adjudicated_at=obj.get("adjudicated_at"),
                    adjudication_status=obj.get("adjudication_status", "pending"),
                ))
        create_splits(queries, Path(args.output_dir))

    elif args.command == "compute-agreement":
        report = compute_agreement_report(Path(args.input))
        print(json.dumps(report, indent=2))
        report_path = PHASE4_DIR / "agreement_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Agreement report saved to {report_path}")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())