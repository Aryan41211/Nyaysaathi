# PHASE 4 — NyayaSaathi Legal Dataset Card

**Project:** NyayaSaathi — Legal Information Retrieval System  
**Phase:** 4 — Benchmark Breakthrough  
**Date:** 2026-11-25  
**Repository:** `C:\projects\NyaySaathi`  
**Git SHA:** e34ad6e (HEAD)

---

## 1. Corpus

### 1.1 Expanded Cases (`backend/dataset/expanded_cases.json`)

| Metric | Value |
|--------|-------|
| Total cases | 500 |
| Unique cases after dedup | 232 |
| Duplicate content keys removed | 142 |
| Categories | 10 |
| Subcategories | 201 |
| Language metadata | "Unknown" for all cases |

### 1.2 Category Distribution

| Category | Count |
|----------|-------|
| Land and Property Disputes | 76 |
| Labour and Wage Issues | 56 |
| Government Scheme and Public Service Issues | 52 |
| Cyber Fraud and Digital Scams | 50 |
| Consumer Complaints | 50 |
| Domestic Violence and Family Disputes | 48 |
| Police Complaints and Local Crime | 46 |
| Senior Citizen Protection Issues | 44 |
| Environmental and Public Nuisance Complaints | 41 |
| Tenant–Landlord Disputes | 37 |

### 1.3 Deduplication

Method: Content key = (category.lower(), subcategory.lower(), problem_description.lower())

500 expanded cases → 232 unique cases after removing 142 duplicate content keys.

### 1.4 Limitations

- All cases are synthetic/template-based expansions of 201 seed cases
- No real legal documents from public sources
- Language metadata missing (all marked "Unknown")
- No document-level versioning
- No source provenance beyond synthetic generation

---

## 2. Evaluation Dataset

### 2.1 Candidate Queries (`backend/evaluation/phase4/annotations/candidate_queries.jsonl`)

| Metric | Value |
|--------|-------|
| Total candidate queries | 1,160 |
| Queries per category | ~116 (10 categories) |
| Difficulty distribution | easy / medium / hard (random) |
| Language | English (all) |
| Source | seed (derived from corpus problem descriptions) |

### 2.2 Human-Validated Queries

| Metric | Value |
|--------|-------|
| Human-reviewed queries | 0 |
| Annotators | 0 |
| Inter-annotator agreement | Not computed |

**Status:** No human-validated queries exist. The candidate queries (1,160) await human annotation. Per Phase 4 rules, no annotations are fabricated — no query is marked "human-validated" until a person has actually reviewed it.

### 2.3 Previous Human-Eval Queries (`backend/dataset/human_eval_queries.jsonl`)

| Metric | Value |
|--------|-------|
| Queries | 6 |
| Label source | "human-validated" (claimed) |
| Issue | Sequential block relevance labels (cases 0-4, 50-54, etc.) — not genuine human judgments |
| Case ID range | 0-154 (all within expanded_cases.json) |

**Status:** These 6 queries use the same problematic sequential block labeling as the Phase 2 dataset. They are NOT reliable human judgments.

---

## 3. Annotation Schema

Each validated query includes:

| Field | Type | Description |
|-------|------|-------------|
| query_id | string | Unique identifier |
| query_text | string | The user's legal question |
| language | string | en / hi / mr / hinglish |
| category | string | Legal category (10 categories) |
| subcategory | string | Legal subcategory |
| difficulty | string | easy / medium / hard |
| source | string | seed / synthetic / user-submitted |
| relevant_case_ids | list[string] | Case IDs judged relevant |
| relevance_grades | dict[string, int] | case_id → grade (0-3) |
| annotator | string | Reviewer identity |
| annotated_at | ISO datetime | Annotation timestamp |
| adjudicator | string | Adjudicator identity (if adjudicated) |
| adjudicated_at | ISO datetime | Adjudication timestamp |
| adjudication_status | string | pending / approved / rejected / needs_revision |
| label_source | string | human-validated |

### Relevance Grades

| Grade | Meaning |
|-------|---------|
| 0 | Not relevant |
| 1 | Partially relevant (tangentially related) |
| 2 | Relevant (directly addresses the query) |
| 3 | Highly relevant (comprehensive guidance) |

---

## 4. Annotation Workflow

See `PHASE4_ANNOTATION_GUIDE.md` for complete instructions.

### Steps

1. **Candidate generation** — 1,160 candidate queries generated from corpus
2. **Annotation** — Human reviewer labels relevant cases with grades 0-3
3. **Adjudication** — Second reviewer resolves disagreements
4. **Split creation** — Train/validation/test stratified by category
5. **Evaluation** — Retrieval benchmarks run on test split only

---

## 5. Reproducibility

| Item | Value |
|------|-------|
| Random seed | 42 |
| Dedup method | Content key (category + subcategory + problem_description) |
| Candidate generation script | `scripts/phase4/annotation_system.py` |
| Candidate output | `backend/evaluation/phase4/annotations/candidate_queries.jsonl` |
| Deduped corpus | 232 cases (from `backend/api/data_loader.py` CASES) |

---

## 6. Next Steps

1. Recruit human annotators with legal knowledge
2. Annotate candidate queries using the annotation system
3. Compute inter-annotator agreement (Cohen's kappa, Krippendorff's alpha)
4. Create train/validation/test splits
5. Run retrieval benchmarks on held-out test split
6. Expand corpus toward 5,000-10,000 distinct legal documents from legitimate sources
