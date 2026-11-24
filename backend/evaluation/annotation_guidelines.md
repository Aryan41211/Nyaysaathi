# Human-Validated Evaluation Guidelines — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Purpose:** Guidelines for human annotators to create labeled evaluation queries  
**Status:** Template — no human labels have been applied yet

## 1. Objective

Create a human-validated evaluation dataset for retrieval quality assessment.
Auto-generated labels (category-based proxy) are used for development but
are NOT sufficient for claiming retrieval quality. Human-validated labels
are required for defensible metrics.

## 2. Annotation Workflow

### Step 1: Select Queries
- Select 50-100 diverse legal queries across all 10 categories
- Include easy, difficult, ambiguous, and out-of-domain queries
- Ensure queries reflect real user intent (not just case subcategories)

### Step 2: Label Relevant Documents
For each query, an annotator with legal knowledge identifies which cases
in the corpus are relevant. A case is "relevant" if it provides useful
procedural guidance for the user's legal problem.

### Step 3: Assign Relevance Grades (Optional)
- 0: Not relevant
- 1: Partially relevant (tangentially related)
- 2: Relevant (directly addresses the query)
- 3: Highly relevant (comprehensive guidance for the query)

### Step 4: Record Metadata
- Annotator ID
- Annotation date
- Query source (user-submitted, synthetic, etc.)
- Label source: "human-validated"

## 3. Output Format

Each evaluation query is a JSON object:

```json
{
  "query_id": "human-001",
  "query_text": "My neighbor built a fence on my land without permission",
  "relevant_case_ids": ["3", "12", "45"],
  "relevance_grades": {"3": 3, "12": 2, "45": 2},
  "label_source": "human-validated",
  "metadata": {
    "annotator_id": "annotator_1",
    "annotation_date": "2026-11-24",
    "query_category": "Land and Property Disputes",
    "difficulty": "medium"
  }
}
```

- `relevant_case_ids`: List of case index positions (0-based) in the corpus
- `relevance_grades`: Optional mapping from case ID to grade (0-3)
- `label_source`: Must be "human-validated" for human labels

## 4. Dataset Splits

To prevent evaluation leakage:

| Split | Purpose | Size |
|---|---|---|
| Train | Development, tuning fusion weights | ~60% |
| Dev | Selecting best configuration | ~20% |
| Test | Final reported metrics | ~20% |

**Never tune hyperparameters on the test set.**

## 5. Quality Checks

- Each query should be annotated by at least one annotator
- For critical queries, use dual annotation and compute inter-annotator agreement
- Remove queries where annotators disagree significantly
- Verify all `relevant_case_ids` refer to valid corpus indices

## 6. Current Status

| Item | Status |
|---|---|
| Auto-generated labels | 201 queries (category-based proxy) |
| Human-validated labels | 0 queries (not yet created) |
| Annotation guidelines | This document |
| Template dataset | `backend/evaluation/datasets/human_validated_template.json` |

## 7. Next Steps

1. Recruit annotators with legal knowledge
2. Select 50-100 diverse queries
3. Annotate relevance judgments
4. Resolve inter-annotator disagreements
5. Create train/dev/test splits
6. Re-run evaluation with human-validated labels
7. Compare against auto-generated baseline
