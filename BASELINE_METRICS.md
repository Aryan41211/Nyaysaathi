# BASELINE_METRICS.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Baseline date:** 2026-11-24  
**Git baseline commit:** 4239f3c65aa1d92f60ba0fdd5b8ca3cf21f32a72  
**Optimized commit:** b23d7b1 (after optimization changes)

## Corpus Baseline

| Metric | Value | Unit | Evidence | Confidence |
|---|---:|---|---|---|
| Total indexed cases | 201 | count | `backend/dataset/legal_cases.json` | HIGH |
| Categories | 10 | count | Corpus analysis | HIGH |
| Subcategories | 201 | count | Corpus analysis (1 per case) | HIGH |
| Documents per category | ~20 | avg | Corpus analysis | HIGH |
| Exact duplicates | 0 | count | `corpus_engineering.py` validation | HIGH |
| Near duplicates | 0 | count | `corpus_engineering.py` validation | HIGH |
| Missing required fields | 0 | count | `corpus_engineering.py` validation | HIGH |

### Corpus distribution
| Category | Count |
|---|---:|
| Land and Property Disputes | 27 |
| Labour and Wage Issues | 23 |
| Cyber Fraud and Digital Scams | 21 |
| Consumer Complaints | 21 |
| Police Complaints and Local Crime | 20 |
| Government Scheme and Public Service Issues | 20 |
| Environmental and Public Nuisance Complaints | 19 |
| Senior Citizen Protection Issues | 19 |
| Tenant–Landlord Disputes | 16 |
| Domestic Violence and Family Disputes | 15 |

## Retrieval Baseline (Auto-generated labels — NOT human-validated)

**Evaluation dataset:** 201 auto-generated queries, one per case  
**Relevance judgment:** Same category as source case (proxy label)  
**Label source:** `auto-generated` — LOW confidence

### Retrieval Metrics Comparison

| System | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@5 | MRR | nDCG@5 | Eval time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | 0.046 | 0.091 | 0.120 | 0.120 | 0.482 | 0.951 | 0.569 | — |
| BM25 | 0.050 | 0.120 | 0.183 | 0.314 | 0.725 | 1.000 | 0.778 | — |
| Dense (MiniLM+FAISS) | 0.050 | 0.130 | 0.202 | 0.362 | 0.813 | 1.000 | 0.848 | 10.2s |
| Hybrid (RRF) | 0.050 | 0.120 | 0.183 | 0.314 | 0.725 | 1.000 | 0.778 | — |
| Hybrid (Weighted 0.7/0.2/0.1) | 0.050 | 0.130 | 0.201 | 0.362 | 0.808 | 1.000 | 0.845 | — |
| **Dense (MPNet)** | **0.050** | **0.134** | **0.215** | **0.382** | **0.859** | **1.000** | **0.884** | **14.8s** |

> **NOTE:** MRR = 1.000 for all systems is expected with category-based proxy labels — the first result is usually same-category. MRR is not discriminative with these labels.  
> **Best configuration:** MPNet embeddings alone — Recall@5 = 0.2145 (+6.3% vs MiniLM), Precision@5 = 0.8587 (+5.6%), nDCG@5 = 0.8836 (+4.1%).

### Latency Benchmarks

| Component | p50 | p95 | p99 | Mean | n |
|---|---:|---:|---:|---:|---:|
| End-to-end retrieval (MiniLM) | 7.27ms | 12.68ms | 16.13ms | 7.82ms | 50 |
| Embedding generation (MiniLM) | 3.77ms | 4.71ms | 5.18ms | 3.93ms | 50 |
| FAISS search (MiniLM) | 0.008ms | 0.014ms | 0.036ms | 0.010ms | 200 |

### Cross-Encoder Reranking Latency

| Config | p50 | p95 | p99 | Mean | Overhead vs Dense |
|---|---:|---:|---:|---:|---:|
| Dense only (MiniLM) | 13.40ms | 22.60ms | 22.60ms | 13.99ms | — |
| Dense + CrossEncoder | 50.87ms | 56.82ms | 56.82ms | 50.12ms | +36.13ms (+258%) |

### Throughput

| Metric | Value | Unit |
|---|---:|---|
| End-to-end throughput | 222 | queries/sec |

## Reproducibility

- Model: sentence-transformers/all-mpnet-base-v2 (768 dims) — RECOMMENDED
- Baseline model: sentence-transformers/all-MiniLM-L6-v2 (384 dims)
- Random seed: 42 (configured in pipeline)
- Warm-up: 5 retrievals before timed runs
- Measurements: 50 end-to-end, 50 embedding, 200 FAISS search
- No GPU used — CPU-only
- Single-threaded

## Commands

```
cd C:\projects\NyaySaathi\backend
python run_eval.py          # Retrieval evaluation (MiniLM baseline)
python experiment_embedding_comparison.py  # Embedding model comparison
python experiment_mpnet_crossencoder.py  # MPNet + cross-encoder comparison
python manage.py test       # Test suite (3 tests)
```

## Known Limitations

- Corpus only 201 cases (small for production-scale retrieval)
- All labels auto-generated (category-based proxy), NOT human-validated
- MRR = 1.000 is not discriminative with category-based labels
- No persistent vector store (rebuilt on startup)
- No human-validated evaluation dataset
- Cross-encoder reranking adds +36ms latency for -3.4% Recall@5 with MPNet (not recommended)
