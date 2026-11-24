# BASELINE_METRICS.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Baseline date:** 2026-11-24  
**Git baseline commit:** 77b3963

## Corpus Baseline

| Metric | Value | Unit | Evidence | Confidence |
|---|---:|---|---|---|
| Total indexed cases | 201 | count | `backend/dataset/legal_cases.json` | HIGH |
| Categories | 10 | count | Corpus analysis | HIGH |
| Subcategories | 201 | count | Corpus analysis (1 per case) | HIGH |
| Documents per category | ~20 | avg | Corpus analysis | HIGH |

## Retrieval Baseline (Auto-generated labels — NOT human-validated)

**Evaluation dataset:** 201 auto-generated queries, one per case  
**Relevance judgment:** Same category as source case (proxy label)  
**Label source:** `auto-generated`

| System | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@5 | MRR | nDCG@5 | Hit Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | ? | ? | 0.120 | ? | ? | ? | ? | ? |
| BM25 | ? | ? | 0.183 | ? | ? | ? | ? | ? |
| Dense (MiniLM+FAISS) | ? | ? | 0.202 | ? | ? | 1.000 | 0.848 | ? |
| Hybrid (RRF) | ? | ? | 0.183 | ? | ? | ? | ? | ? |

> **WARNING:** MRR = 1.000 for Dense is suspicious and requires audit (Phase A3).  
> All labels are auto-generated proxies, not human-validated ground truth.

## Performance Baseline

| Metric | Value | Unit | Evidence | Confidence |
|---|---:|---|---|---|
| Embedding model | all-MiniLM-L6-v2 | text | `semantic_engine.py` | HIGH |
| Embedding dimensions | 384 | count | Model output | HIGH |
| FAISS index type | IndexFlatIP | text | `faiss_index.py` | HIGH |
| Vectors stored | 201 | count | `semantic_engine.py` | HIGH |

## Test Baseline

| Metric | Value | Unit | Evidence | Confidence |
|---|---:|---|---|---|
| Tests passed | 3 | count | `python manage.py test` | HIGH |
| Tests failed | 0 | count | `python manage.py test` | HIGH |

## Known Limitations (to address in optimization)

1. Corpus is only 201 cases — too small for meaningful retrieval evaluation
2. All evaluation labels are auto-generated (category-based proxy)
3. Hybrid RRF performs worse than dense alone (Recall@5: 0.183 vs 0.202) — needs investigation
4. MRR = 1.000 for Dense is suspicious — may be computed incorrectly
5. No human-validated evaluation dataset exists
6. No cross-encoder reranking implemented
7. No document provenance/licensing tracking
