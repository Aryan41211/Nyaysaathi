# PHASE 4 — NyayaSaathi Annotation Guide

**Project:** NyayaSaathi — Legal Information Retrieval System  
**Phase:** 4 — Benchmark Breakthrough  
**Date:** 2026-11-25  
**Purpose:** Instructions for human annotators labeling legal retrieval relevance judgments

---

## 1. Objective

Create a human-validated evaluation dataset for legal document retrieval. Each query must have genuinely human-assessed relevance judgments — not auto-generated or synthetic labels.

## 2. Annotation Workflow

### Step 1: Select a Candidate Query

Choose an unannotated query from `candidate_queries.jsonl`. Each candidate includes:
- The query text
- Legal category and subcategory
- Difficulty level
- Up to 10 candidate cases from the same subcategory

### Step 2: Read the Query

Understand what legal problem the user is describing. Consider:
- What is the core legal issue?
- What category does it fall under?
- Is it easy, medium, or hard difficulty?

### Step 3: Review Candidate Cases

For each candidate case, read:
- Case category and subcategory
- Problem description
- Workflow steps (procedural guidance)

### Step 4: Assign Relevance Grades

For each candidate case, assign a relevance grade:

| Grade | Label | Definition |
|-------|-------|------------|
| 0 | Not relevant | Case does not address the user's legal problem |
| 1 | Partially relevant | Case is tangentially related but does not provide useful procedural guidance |
| 2 | Relevant | Case directly addresses the query with relevant procedural steps |
| 3 | Highly relevant | Case provides comprehensive guidance for the user's specific legal problem |

**Guidelines:**
- A case is relevant if it provides useful procedural guidance for the user's legal problem
- The case should be in the same legal category as the query
- Consider the specific subcategory — a land boundary dispute case is not equally relevant to a land acquisition query
- Grade 3 requires the case to be directly on point with the query's specific facts
- A case can have grade 0 even if it's in the same category but addresses a different legal issue

### Step 5: Record Metadata

| Field | Required | Description |
|-------|----------|-------------|
| annotator | Yes | Your identifier (e.g., "annotator_1") |
| annotated_at | Yes | Auto-generated timestamp |
| adjudication_status | Yes | "pending" until second review |

### Step 6: Adjudication (Optional but Recommended)

A second reviewer should:
1. Review queries where the first annotator assigned mixed grades (0 and 3 for the same case)
2. Resolve disagreements
3. Record adjudicator identity and timestamp
4. Set adjudication_status to "approved" or "rejected"

---

## 3. Output Format

Each annotated query is a JSONL record:

```json
{
  "query_id": "cand-0001",
  "query_text": "My neighbour built a fence on my land without permission",
  "language": "en",
  "category": "Land and Property Disputes",
  "subcategory": "Land Boundary Dispute",
  "difficulty": "easy",
  "source": "seed",
  "relevant_case_ids": ["3", "7", "12"],
  "relevance_grades": {"3": 3, "7": 2, "12": 1},
  "annotator": "annotator_1",
  "annotated_at": "2026-11-25T10:00:00Z",
  "adjudicator": null,
  "adjudicated_at": null,
  "adjudication_status": "pending",
  "label_source": "human-validated"
}
```

## 4. Importing Annotations

```bash
cd C:\projects\NyaySaathi\scripts\phase4
python annotation_system.py import-annotations \
  --input annotated_queries.jsonl \
  --output backend/evaluation/phase4/annotations/validated_dataset.jsonl
```

This maps expanded case IDs to the deduplicated corpus indices and validates all references.

## 5. Creating Train/Validation/Test Splits

```bash
python annotation_system.py create-splits \
  --input backend/evaluation/phase4/annotations/validated_dataset.jsonl \
  --output-dir backend/evaluation/phase4/splits/
```

Splits are stratified by legal category (60% train, 20% validation, 20% test).

**Never tune retrieval parameters on the test set.**

## 6. Computing Inter-Annotator Agreement

When two or more annotators label the same queries:

```bash
python annotation_system.py compute-agreement \
  --input annotated_queries.jsonl
```

Reports:
- Pairwise Cohen's kappa between annotators
- Krippendorff's alpha across all annotators

**Interpretation:**
- κ < 0.20: Poor agreement
- 0.21–0.40: Fair
- 0.41–0.60: Moderate
- 0.61–0.80: Substantial
- 0.81–1.00: Almost perfect

---

## 7. Quality Checks

- [ ] Each query has at least one relevant case (grade ≥ 2)
- [ ] All relevant_case_ids refer to valid case indices in the deduped corpus
- [ ] Relevance grades use the full 0-3 scale (not all 3s)
- [ ] No sequential block assignments (e.g., cases 0-4 all marked relevant for different queries)
- [ ] Cross-category reuse is justified (a case can be relevant to multiple queries only if genuinely applicable)
- [ ] Annotator identity is recorded for every query
- [ ] Adjudication status is set for every query

---

## 8. What NOT to Do

- ❌ Do not mark all cases in a subcategory as relevant just because they share a category
- ❌ Do not use sequential blocks (cases 0-4, 50-54) as relevance labels
- ❌ Do not annotate queries you have not personally read
- ❌ Do not mark a query as "human-validated" without a real annotator
- ❌ Do not copy relevance labels from one query to another

---

## 9. Target Sizes

| Metric | Target |
|--------|--------|
| Candidate queries generated | 1,160 ✅ |
| Human-reviewed queries (initial goal) | 200+ |
| Human-reviewed queries (aspirational) | 500+ |
| Categories covered | 10/10 ✅ |
| Difficulty levels | easy, medium, hard ✅ |
| Inter-annotator agreement | κ ≥ 0.60 (substantial) |
