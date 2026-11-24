"""Corpus engineering utilities for NyaySaathi.

Provides:
1. Document provenance tracking (source, URL, extraction status, license)
2. Deduplication detection using exact match and text similarity
3. Corpus validation report
4. Extensible ingestion pipeline structure
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class DocumentProvenance:
    """Metadata about a document's origin and processing."""

    source_name: str
    source_url: Optional[str] = None
    license: Optional[str] = None
    extraction_date: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    extraction_status: str = "success"  # success, partial, failed
    document_id: Optional[str] = None
    content_hash: Optional[str] = None
    language: str = "en"


@dataclass
class DuplicateCandidate:
    """A pair of potentially duplicate documents."""

    idx1: int
    idx2: int
    similarity: float
    reason: str  # "exact", "near-duplicate", "same-category"


def _build_searchable_text(case: Dict[str, Any]) -> str:
    """Build searchable text from case fields (same as semantic_engine)."""
    chunks = [
        str(case.get("category", "")),
        str(case.get("subcategory", "")),
        str(case.get("problem_description", "")),
    ]
    descriptions = case.get("descriptions", [])
    if isinstance(descriptions, list):
        chunks.append(" ".join(str(x) for x in descriptions))
    workflow_steps = case.get("workflow_steps", [])
    if isinstance(workflow_steps, list):
        chunks.append(" ".join(str(x) for x in workflow_steps))
    return " ".join(chunk for chunk in chunks if chunk).strip()


def compute_content_hash(case: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of normalized searchable text for duplicate detection."""
    text = _build_searchable_text(case)
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def find_duplicates(
    cases: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
) -> List[DuplicateCandidate]:
    """Find potentially duplicate documents.

    Uses exact content hash matching first, then TF-IDF cosine similarity
    for near-duplicate detection.
    """
    duplicates: List[DuplicateCandidate] = []

    # Exact hash matching
    hash_to_indices: Dict[str, List[int]] = {}
    for idx, case in enumerate(cases):
        content_hash = compute_content_hash(case)
        case["content_hash"] = content_hash
        hash_to_indices.setdefault(content_hash, []).append(idx)

    for hash_val, indices in hash_to_indices.items():
        if len(indices) > 1:
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    duplicates.append(
                        DuplicateCandidate(
                            idx1=indices[i],
                            idx2=indices[j],
                            similarity=1.0,
                            reason="exact",
                        )
                    )

    # Near-duplicate detection using TF-IDF cosine similarity
    texts = [_build_searchable_text(c) for c in cases]
    if len(texts) > 1:
        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(texts)
            sim_matrix = cosine_similarity(tfidf_matrix)

            for i in range(len(cases)):
                for j in range(i + 1, len(cases)):
                    sim = sim_matrix[i, j]
                    if similarity_threshold <= sim < 1.0:
                        # Check if already flagged as exact duplicate
                        already_flagged = any(
                            d.idx1 == i and d.idx2 == j for d in duplicates
                        )
                        if not already_flagged:
                            duplicates.append(
                                DuplicateCandidate(
                                    idx1=i,
                                    idx2=j,
                                    similarity=float(sim),
                                    reason="near-duplicate",
                                )
                            )
        except Exception:
            # TF-IDF may fail on empty corpus; skip near-duplicate detection
            pass

    return duplicates


def validate_corpus(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate corpus integrity and produce a validation report."""
    total = len(cases)
    categories: Dict[str, int] = {}
    subcategories: Dict[str, int] = {}
    missing_fields: List[str] = []
    empty_descriptions: List[int] = []

    for idx, case in enumerate(cases):
        cat = case.get("category", "Unknown")
        sub = case.get("subcategory", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1
        subcategories[sub] = subcategories.get(sub, 0) + 1

        # Check required fields
        for field in ["category", "subcategory", "problem_description"]:
            if not case.get(field):
                missing_fields.append(f"Case {idx}: missing {field}")

        if not _build_searchable_text(case).strip():
            empty_descriptions.append(idx)

    duplicates = find_duplicates(cases)

    return {
        "total_documents": total,
        "categories": len(categories),
        "category_distribution": categories,
        "subcategories": len(subcategories),
        "missing_required_fields": len(missing_fields),
        "missing_field_details": missing_fields[:10],
        "empty_descriptions": len(empty_descriptions),
        "empty_description_indices": empty_descriptions[:10],
        "exact_duplicates": sum(1 for d in duplicates if d.reason == "exact"),
        "near_duplicates": sum(1 for d in duplicates if d.reason == "near-duplicate"),
        "duplicate_details": [
            {
                "idx1": d.idx1,
                "idx2": d.idx2,
                "similarity": d.similarity,
                "reason": d.reason,
            }
            for d in duplicates[:20]
        ],
        "has_provenance": all("content_hash" in c for c in cases),
    }


def add_provenance(
    cases: List[Dict[str, Any]],
    source_name: str,
    source_url: Optional[str] = None,
    license_str: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Add provenance metadata to all documents in the corpus."""
    enriched = []
    for case in cases:
        merged = dict(case)
        merged["provenance"] = {
            "source_name": source_name,
            "source_url": source_url,
            "license": license_str,
            "extraction_date": datetime.now(UTC).isoformat(),
            "extraction_status": "success",
            "content_hash": case.get("content_hash") or compute_content_hash(case),
        }
        enriched.append(merged)
    return enriched


def generate_validation_report(cases: List[Dict[str, Any]]) -> str:
    """Generate a human-readable validation report."""
    report = validate_corpus(cases)
    lines = [
        "=== NyaySaathi Corpus Validation Report ===",
        f"Total documents: {report['total_documents']}",
        f"Categories: {report['categories']}",
        f"Subcategories: {report['subcategories']}",
        f"Missing required fields: {report['missing_required_fields']}",
        f"Empty descriptions: {report['empty_descriptions']}",
        f"Exact duplicates: {report['exact_duplicates']}",
        f"Near duplicates: {report['near_duplicates']}",
        f"Has provenance tracking: {report['has_provenance']}",
        "",
        "Category distribution:",
    ]
    for cat, count in sorted(
        report["category_distribution"].items(), key=lambda x: -x[1]
    ):
        lines.append(f"  {cat}: {count}")
    if report["duplicate_details"]:
        lines.append("")
        lines.append("Duplicate candidates (first 20):")
        for d in report["duplicate_details"]:
            lines.append(
                f"  Cases {d['idx1']} <-> {d['idx2']}: "
                f"similarity={d['similarity']:.3f} ({d['reason']})"
            )
    return "\n".join(lines)


def incremental_update(
    existing_cases: List[Dict[str, Any]],
    new_cases: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Add new cases to the corpus, skipping exact duplicates.

    Returns (updated_cases, added_cases).
    """
    existing_hashes: Dict[str, int] = {}
    for idx, case in enumerate(existing_cases):
        ch = case.get("content_hash") or compute_content_hash(case)
        existing_hashes[ch] = idx

    added: List[Dict[str, Any]] = []
    updated = list(existing_cases)

    for case in new_cases:
        ch = case.get("content_hash") or compute_content_hash(case)
        if ch not in existing_hashes:
            case["content_hash"] = ch
            updated.append(case)
            added.append(case)
            existing_hashes[ch] = len(updated) - 1

    return updated, added
