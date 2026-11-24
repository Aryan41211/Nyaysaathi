# NyaySaathi Dataset Card

**Project:** NyaySaathi — Legal Information Retrieval System  
**Dataset:** expanded_cases.json (500 cases, 232 unique after dedup)  
**Version:** 1.0  
**Date:** 2026-11-24

---

## 1. Corpus Overview

| Attribute | Value |
|-----------|-------|
| File | `backend/dataset/expanded_cases.json` |
| Total records | 500 |
| Unique records after deduplication | 232 |
| Seed records (legal_cases.json) | 201 |
| Synthetic expansion records | 299 |
| Categories | 10 |
| Languages | English (en) |
| Format | JSON array of case objects |

### Deduplication

Records are deduplicated by content key: `(category, subcategory, problem_description)` normalized to lowercase and stripped. This removes near-duplicate synthetic variants while preserving semantically distinct cases.

| Metric | Value |
|--------|-------|
| Before dedup | 500 |
| After dedup | 232 |
| Duplicates removed | 268 (53.6%) |

---

## 2. Category Distribution

| Category | Cases | % of Corpus |
|----------|-------|-------------|
| Land and Property Disputes | 76 | 15.2% |
| Labour and Wage Issues | 56 | 11.2% |
| Domestic Violence and Family Disputes | 48 | 9.6% |
| Cyber Fraud and Digital Scams | 50 | 10.0% |
| Consumer Complaints | 50 | 10.0% |
| Police Complaints and Local Crime | 46 | 9.2% |
| Government Scheme and Public Service Issues | 52 | 10.4% |
| Tenant-Landlord Disputes | 37 | 7.4% |
| Environmental and Public Nuisance Complaints | 41 | 8.2% |
| Senior Citizen Protection Issues | 44 | 8.8% |

---

## 3. Case Schema

Each case object contains:

| Field | Type | Description |
|-------|------|-------------|
| category | string | Legal category (10 values) |
| subcategory | string | Specific legal issue type |
| problem_description | string | Description of the legal problem |
| workflow_steps | array[string] | Step-by-step procedural guidance |
| required_documents | array[string] | Documents needed for the case |
| authorities | array[{name, level}] | Relevant government authorities |
| escalation_path | array[string] | Escalation steps if unresolved |
| online_portals | array[string] | Relevant online portals |
| helplines | array[string] | Contact helplines |
| complaint_template | string | Template for filing complaint |
| descriptions | array[string] | Additional case descriptions |
| id | string | Case identifier |
| source | string | "synthetic_expansion" or original |

### Example Case

```json
{
  "category": "Land and Property Disputes",
  "subcategory": "Land Boundary Dispute",
  "problem_description": "A citizen disputes the boundary of their agricultural or residential land with a neighbouring landowner. The neighbour may have encroached on the land, moved boundary markers, or built a structure on disputed land.",
  "workflow_steps": [
    "Step 1 – Collect all original land documents including the 7/12 extract (Satbara), property card, and old survey maps from the Talathi office.",
    "Step 2 – Take dated photographs of the disputed boundary, encroachment, or construction.",
    ...
  ],
  "required_documents": [
    "7/12 extract (Satbara Utara)",
    "Property card (Malmatta Patrak)",
    ...
  ],
  "authorities": [
    {"name": "Talathi Office", "level": "Local"},
    {"name": "Tehsildar / Revenue Officer", "level": "Taluka"},
    ...
  ]
}
```

---

## 4. Searchable Text Construction

For embedding generation, each case is converted to a single searchable text by concatenating:

```
category + subcategory + problem_description + descriptions + workflow_steps
```

This text is used for:
- FAISS IndexFlatIP embedding index (768d MPNet)
- BM25 sparse index
- TF-IDF lexical search

---

## 5. Human-Validated Evaluation Dataset

**File:** `backend/evaluation/datasets/human_validated.json`

| Attribute | Value |
|-----------|-------|
| Total queries | 50 |
| Queries per category | 5 |
| Categories covered | 10 (all) |
| Relevance scale | 0-3 (3=highly relevant, 0=not relevant) |
| Label source | human-validated |
| Confidence | HIGH |

Each query includes:
- `query_id` (e.g., "human-land-001")
- `query_text` (natural language legal question)
- `relevant_case_ids` (manually assigned case indices)
- `relevance_grades` (case_id → grade mapping)
- `metadata` (category, subcategory, annotator, difficulty)

### Sample Queries by Category

| Category | Sample Query | Difficulty |
|----------|-------------|------------|
| Land and Property | "My neighbour has built a structure on my land and moved the boundary markers. What should I do?" | easy |
| Labour and Wage | "Employer has not paid my salary for three months and is not responding." | easy |
| Domestic Violence | "Husband and in-laws demanding dowry and harassing me mentally and physically." | easy |
| Cyber Fraud | "UPI fraud — money deducted from my bank account without my authorization." | easy |
| Consumer | "Defective electronic product — seller refusing replacement under warranty." | easy |
| Police | "Lost mobile phone — need to file an FIR at the nearest police station." | easy |
| Government | "Ration card not issued despite applying three months ago." | easy |
| Tenant-Landlord | "Landlord refusing to return security deposit after vacating the rented flat." | easy |
| Environmental | "Factory releasing untreated chemical waste into nearby river." | hard |
| Senior Citizen | "Senior citizen being financially exploited by caregiver with power of attorney." | hard |

---

## 6. Auto-Generated Evaluation Dataset

**Source:** `backend/evaluation/dataset.py` — `build_auto_generated_dataset()`

| Attribute | Value |
|-----------|-------|
| Total queries | 232 (one per unique case) |
| Label source | auto-generated |
| Confidence | LOW |
| Label method | Category-matching proxy: a case is relevant to a query if it shares the same category |

**Limitation:** Auto-generated labels are proxy labels, not true relevance judgments. A case in the same category is not necessarily relevant to a specific query. Use only for relative system comparison, not absolute quality assessment.

---

## 7. Data Provenance

- **Seed corpus (201 cases):** Original legal cases from `legal_cases.json`
- **Synthetic expansion (299 cases):** Template-based paraphrase and entity substitution via `scripts/expand_corpus.py` (seed=42, target=500)
- **Human-validated labels:** Manual annotation by legal experts (annotator_1, annotator_2)
- **No real legal documents used:** All cases are synthetic or derived from public legal information templates

---

## 8. Known Limitations

1. **Synthetic corpus:** 299 of 500 cases are synthetic expansions, not real legal documents
2. **Sparse human labels:** Only 5 relevant cases per query out of 232 total cases
3. **Single language:** English only; no Hindi/Marathi/Hinglish corpus despite frontend supporting multilingual input
4. **No legal citations:** Cases reference authorities but no actual case law citations
5. **No version history:** No temporal versioning of legal procedures or authorities
