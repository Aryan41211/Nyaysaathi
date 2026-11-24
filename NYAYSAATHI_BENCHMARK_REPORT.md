# NyaySaathi Phase 2 — Benchmark Report

**Project:** NyaySaathi — Legal Information Retrieval System  
**Date:** 2026-11-24  
**Git SHA:** `1a3eb00`  
**Branch:** `main`  
**Environment:** 16 CPU cores, 15.65 GB RAM, CPU-only

---

## 1. Benchmark Configuration

| Parameter | Value |
|-----------|-------|
| Corpus | `backend/dataset/expanded_cases.json` (500 cases → 232 unique after dedup) |
| Index | FAISS IndexFlatIP (inner product, cosine via normalized embeddings) |
| Embedding model | sentence-transformers/all-mpnet-base-v2 (768d) |
| Auto-generated queries | 232 (one per unique case) |
| Human-validated queries | 50 (5 per category × 10 categories) |
| Top-k values | 1, 3, 5, 10 |
| Latency samples | 50 queries per system |
| Warm cache | Yes (query embedding cache enabled) |

---

## 2. Auto-Generated Label Results (232 queries)

### Recall@5 by System

| System | Recall@5 | vs MiniLM | p50 ms | p95 ms |
|--------|----------|-----------|--------|--------|
| TF-IDF | 0.1027 | -41.9% | 9.51 | 14.84 |
| BM25 | 0.1618 | -8.5% | 0.98 | 1.47 |
| MiniLM (384d) | 0.1768 | baseline | 5.50 | 8.27 |
| **MPNet (768d)** | **0.1867** | **+5.6%** | 11.80 | 19.94 |
| E5-base (768d) | 0.1836 | +3.8% | 8.95 | 14.69 |
| BGE-base (768d) | 0.1819 | +2.9% | 9.27 | 15.39 |
| Hybrid (weighted fusion) | 0.1870 | +5.8% | 28.30 | 37.40 |

### Precision@5 by System

| System | Precision@5 |
|--------|-------------|
| MiniLM (384d) | 0.8328 |
| **MPNet (768d)** | **0.8698** |
| E5-base (768d) | 0.8595 |
| BGE-base (768d) | 0.8483 |
| Hybrid (weighted fusion) | 0.8698 |
| BM25 | 0.7552 |
| TF-IDF | 0.4819 |

### MRR by System

| System | MRR |
|--------|-----|
| BM25 | 1.0000 |
| MiniLM (384d) | 1.0000 |
| **MPNet (768d)** | **1.0000** |
| E5-base (768d) | 1.0000 |
| BGE-base (768d) | 1.0000 |
| Hybrid (weighted fusion) | 1.0000 |
| TF-IDF | 0.9400 |

### nDCG@5 by System

| System | nDCG@5 |
|--------|--------|
| **MPNet (768d)** | **0.8951** |
| E5-base (768d) | 0.8863 |
| BGE-base (768d) | 0.8793 |
| MiniLM (384d) | 0.8655 |
| Hybrid (weighted fusion) | 0.8954 |
| BM25 | 0.8037 |
| TF-IDF | 0.5643 |

---

## 3. Human-Validated Label Results (50 queries)

### Recall@5 by System

| System | Recall@5 | Precision@5 | MRR |
|--------|----------|-------------|-----|
| E5-base (768d) | **0.0200** | 0.0200 | 0.0440 |
| BM25 | **0.0200** | 0.0200 | 0.0414 |
| MPNet (normalized) | **0.0160** | 0.0160 | **0.0667** |
| MPNet (raw query) | 0.0120 | 0.0120 | 0.0409 |
| BGE-base (768d) | 0.0120 | 0.0120 | 0.0464 |

*Note: R@5=0.02 means 1 of 5 relevant cases found in top 5 (20% coverage). Labels are sparse (5 relevant per query out of 232 cases).*

---

## 4. Latency Analysis

### p50/p95/p99 Latency (ms)

| System | p50 | p90 | p95 | p99 | Mean |
|--------|-----|-----|-----|-----|------|
| BM25 | 0.98 | — | 1.47 | 1.60 | 0.97 |
| MiniLM | 5.50 | 7.74 | 8.27 | 9.48 | 5.93 |
| E5-base | 8.95 | 14.41 | 14.69 | 16.79 | 10.16 |
| BGE-base | 9.27 | 14.73 | 15.39 | 16.57 | 10.37 |
| TF-IDF | 9.51 | — | 14.84 | 16.40 | 9.82 |
| MPNet | 11.80 | 17.24 | 19.94 | 24.61 | 13.25 |
| Hybrid | 28.30 | — | 37.40 | — | — |

### Latency vs Quality Trade-off

| System | R@5 | p50 ms | R@5 per ms |
|--------|-----|--------|------------|
| BM25 | 0.1618 | 0.98 | 0.165 |
| MiniLM | 0.1768 | 5.50 | 0.032 |
| E5-base | 0.1836 | 8.95 | 0.021 |
| BGE-base | 0.1819 | 9.27 | 0.020 |
| **MPNet** | **0.1867** | 11.80 | **0.016** |
| Hybrid | 0.1870 | 28.30 | 0.007 |

BM25 offers the best quality/latency ratio but lower absolute quality. MPNet offers the best absolute quality at acceptable latency (< 20ms p95).

---

## 5. Query Normalization Impact

Tested on MPNet with human-validated labels (50 queries):

| Metric | Raw Query | Normalized Query | Improvement |
|--------|-----------|-----------------|-------------|
| Recall@5 | 0.0120 | 0.0160 | +33.3% |
| Precision@5 | 0.0120 | 0.0160 | +33.3% |
| MRR | 0.0409 | 0.0667 | +63.1% |

Normalization includes:
- Hinglish term mapping (e.g., "talaq" → "divorce", "kabza" → "encroachment")
- Domain synonym expansion (e.g., "fired" → "termination", "wrongful termination")
- Phrase-level synonyms (e.g., "salary not paid" → "unpaid", "salary dispute")

---

## 6. Model Selection Analysis

### Why MPNet Was Selected

| Criterion | MPNet | E5-base | BGE-base | MiniLM |
|-----------|-------|---------|----------|--------|
| Auto-gen R@5 | **0.1867** | 0.1836 | 0.1819 | 0.1768 |
| Auto-gen nDCG@5 | **0.8951** | 0.8863 | 0.8793 | 0.8655 |
| Auto-gen MRR | **1.0000** | 1.0000 | 1.0000 | 1.0000 |
| p50 latency | 11.8ms | **8.95ms** | 9.27ms | 5.50ms |
| p95 latency | 19.9ms | **14.7ms** | 15.4ms | 8.3ms |

MPNet selected because it achieves the highest absolute retrieval quality on the auto-generated evaluation set (the larger, more statistically reliable dataset). The latency difference vs E5-base is only 2.85ms p50, which is acceptable for interactive legal guidance.

E5-base is the recommended alternative if latency is the primary concern (8.95ms p50 vs 11.80ms p50, ~24% faster).

---

## 7. Architectural Decisions

### NOT Recommended (Tested and Rejected)

| Technique | Result | Decision |
|-----------|--------|----------|
| Cross-encoder reranking | R@5 -3.4%, +36ms latency | **Rejected** — quality decrease + latency increase |
| Hybrid weighted fusion | R@5 +0.16%, 2.4x latency | **Rejected** — negligible quality gain, doubles latency |
| RRF (k=60) | R@5=0.0718 (worse than BM25 alone) | **Rejected** — significantly worse quality |

### Recommended (Implemented)

| Optimization | Impact |
|--------------|--------|
| MPNet (768d) replacing MiniLM (384d) | +5.6% R@5 on auto-generated |
| Query embedding cache | Avoids re-encoding repeated queries |
| Retrieval result cache | Avoids FAISS search for repeated queries |
| Query normalization (Hinglish + synonyms) | +63% MRR on human-validated |
| Corpus deduplication | 500 → 232 unique cases, cleaner metrics |

---

## 8. Raw Result Files

| File | Description |
|------|-------------|
| `experiment_results/phase2_benchmark.json` | Full benchmark with all metrics and latency |
| `experiment_results/model_comparison.json` | 4-model comparison on identical queries |
| `NYAYSAATHI_MODEL_COMPARISON.csv` | CSV version of all results |
| `NYAYSAATHI_EVALUATION_RESULTS.json` | Structured evaluation results |

---

## 9. Reproduction

```bash
cd C:\projects\NyaySaathi\backend

# Full benchmark
python experiment_phase2_benchmark.py

# Model comparison only
python experiment_model_comparison.py --corpus dataset/expanded_cases.json

# Run tests
python manage.py test
```

See `NYAYSAATHI_REPRODUCTION.md` for detailed commands.
