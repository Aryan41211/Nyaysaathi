# PHASE 4 — NyayaSaathi Retrieval Benchmark

**Project:** NyayaSaathi — Legal Information Retrieval System  
**Phase:** 4 — Benchmark Breakthrough  
**Date:** 2026-11-25  
**Git SHA:** e67c41b  
**Environment:** 16 CPU cores, 15.65 GB RAM, CPU-only

---

## 1. Evaluation Dataset

### 1.1 Label Source

| Metric | Value |
|--------|-------|
| Evaluation queries | 1,160 |
| Label source | auto-generated (category proxy) |
| Human-validated queries | 0 |
| Deduped corpus size | 232 cases |
| Categories | 10 |

**WARNING:** All metrics in this benchmark are computed on **auto-generated category-proxy labels**. A case is considered "relevant" to a query if it shares the same subcategory as the query's source case. This is NOT a human relevance judgment.

Per Phase 4 rules, no human-annotated data exists. The 1,160 candidate queries in `backend/evaluation/phase4/annotations/candidate_queries.jsonl` await human annotation. No query is marked "human-validated" because no person has reviewed them.

### 1.2 Label Limitation

With 232 cases across 10 categories (~23 cases per category), category-proxy labels are weakly discriminative. Many cases in the same subcategory are retrieved, inflating Recall@5 to near 1.0 for dense models. These scores **cannot** be compared to human-validated results.

---

## 2. Retrieval System Comparison

### 2.1 Metrics (Auto-Generated Labels)

| Model | Recall@5 | 95% CI | Precision@5 | MRR | nDCG@5 | MAP | p50 ms | p95 ms |
|-------|----------|--------|-------------|-----|--------|-----|--------|--------|
| TF-IDF (baseline) | 0.7306 | [0.7079, 0.7550] | 0.1679 | 0.7008 | 0.6626 | 0.6139 | 7.55 | 12.35 |
| BM25 (baseline) | 1.0000 | [1.0000, 1.0000] | 0.2621 | 0.9950 | 0.9962 | 0.9947 | 0.70 | 1.64 |
| MiniLM (384d) | 0.9759 | [0.9668, 0.9839] | 0.2553 | 0.9467 | 0.9514 | 0.9440 | 4.96 | 10.11 |
| MPNet (768d) | 0.9839 | [0.9767, 0.9902] | 0.2566 | 0.9559 | 0.9610 | 0.9533 | 9.55 | 17.98 |
| E5-base (768d) | 0.9968 | [0.9934, 0.9994] | 0.2609 | 0.9841 | 0.9871 | 0.9837 | 7.97 | 15.31 |
| BGE-base (768d) | 0.9968 | [0.9934, 0.9994] | 0.2609 | 0.9846 | 0.9869 | 0.9833 | 7.89 | 14.89 |

### 2.2 Query Normalization Impact

| Model | R@5 (baseline) | R@5 (+norm) | Change | Significant? |
|-------|---------------|-------------|--------|-------------|
| MiniLM | 0.9759 | 0.9759 | 0.0000 | No (CI overlaps) |
| MPNet | 0.9839 | 0.9839 | 0.0000 | No (CI overlaps) |
| E5-base | 0.9968 | 0.9957 | -0.0011 | No (CI overlaps) |
| BGE-base | 0.9968 | 0.9960 | -0.0008 | No (CI overlaps) |

**Conclusion:** Query normalization produces no statistically significant improvement on auto-generated labels.

### 2.3 Best Model (Auto-Generated Labels)

E5-base and BGE-base tie at R@5 = 0.9968. However, this is on weak category-proxy labels. On genuinely human-validated data, these rankings may differ significantly.

---

## 3. Latency Analysis

| Model | p50 ms | p95 ms | p99 ms |
|-------|--------|--------|--------|
| BM25 | 0.70 | 1.64 | 2.37 |
| MiniLM | 4.96 | 10.11 | 13.71 |
| E5-base | 7.97 | 15.31 | 21.06 |
| BGE-base | 7.89 | 14.89 | 19.65 |
| MPNet | 9.55 | 17.98 | 22.20 |
| TF-IDF | 7.55 | 12.35 | 14.53 |

BM25 offers the best latency but lower discrimination on human-relevant queries (per Phase 3 findings).

---

## 4. Reproduction Commands

```bash
# Run Phase 4 retrieval evaluation
cd C:\projects\NyaySaathi\scripts\phase4
python retrieval_evaluation.py

# Output: backend/evaluation/phase4/retrieval_results.json

# Generate candidate queries for annotation
python annotation_system.py generate-candidates \
  --output backend/evaluation/phase4/annotations/candidate_queries.jsonl \
  --n-per-category 50

# Import human annotations (when available)
python annotation_system.py import-annotations \
  --input annotated_queries.jsonl \
  --output backend/evaluation/phase4/annotations/validated_dataset.jsonl

# Create train/val/test splits
python annotation_system.py create-splits \
  --input backend/evaluation/phase4/annotations/validated_dataset.jsonl \
  --output-dir backend/evaluation/phase4/splits/

# Compute inter-annotator agreement
python annotation_system.py compute-agreement \
  --input annotated_queries.jsonl
```

---

## 5. Limitations

1. **No human-validated labels** — All 1,160 queries are candidates awaiting annotation
2. **Auto-generated labels are weak** — Category-proxy labels inflate Recall@5
3. **Small corpus** — 232 unique cases after dedup
4. **Synthetic data** — All cases are template-based expansions, not real legal documents
5. **No language diversity** — All queries in English; no Hindi/Marathi/Hinglish evaluation
6. **No train/val/test split** — No splits created yet (no validated queries)

---

## 6. Next Steps

1. Recruit human annotators with legal knowledge
2. Annotate 200+ candidate queries using the annotation system
3. Compute inter-annotator agreement (Cohen's kappa, Krippendorff's alpha)
4. Create train/validation/test splits
5. Re-run benchmarks on held-out test split
6. Expand corpus toward 5,000-10,000 distinct legal documents
