# PERFORMANCE_BENCHMARKS.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Benchmark date:** 2026-11-24  
**Hardware:** Developer workstation, CPU-only (no GPU)  
**Software:** Python 3.12.10, PyTorch 2.13.0+cu126, FAISS 1.14.3, sentence-transformers

## Corpus

| Metric | Value | Unit |
|---|---:|---|
| Total documents | 201 | count |
| Embedding dimensions | 384 | count |
| Vectors stored | 201 | count |
| FAISS index type | IndexFlatIP | text |
| TF-IDF vocabulary terms | 1,291 | count |

## Retrieval Benchmarks (Auto-generated labels, 201 queries)

| System | Recall@1 | Recall@3 | Recall@5 | Precision@5 | MRR | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|
| TF-IDF | 0.046 | 0.091 | 0.120 | 0.482 | 0.951 | 0.569 |
| BM25 | 0.050 | 0.120 | 0.183 | 0.725 | 1.000 | 0.778 |
| Dense (MiniLM+FAISS) | 0.050 | 0.130 | 0.202 | 0.813 | 1.000 | 0.848 |
| Hybrid (RRF) | 0.050 | 0.120 | 0.183 | 0.725 | 1.000 | 0.778 |
| Hybrid + CrossEncoder | 0.050 | 0.134 | 0.207 | 0.829 | 1.000 | 0.862 |

> **NOTE:** MRR = 1.000 for BM25/Dense/Hybrid is expected with category-based proxy labels — the first result is usually same-category. MRR is not discriminative with these labels.

## Latency Benchmarks

| Component | p50 | p95 | p99 | Mean | n |
|---|---:|---:|---:|---:|---:|
| End-to-end retrieval | 7.27ms | 12.68ms | 16.13ms | 7.82ms | 50 |
| Embedding generation | 3.77ms | 4.71ms | 5.18ms | 3.93ms | 50 |
| FAISS search | 0.008ms | 0.014ms | 0.036ms | 0.010ms | 200 |

## Throughput

| Metric | Value | Unit |
|---|---:|---|
| End-to-end throughput | 222 | queries/sec |

## Cross-Encoder Reranking Latency

| Config | p50 | p95 | p99 | Mean | Overhead vs Dense |
|---|---:|---:|---:|---:|---:|
| Dense only | 13.40ms | 22.60ms | 22.60ms | 13.99ms | — |
| Dense + CrossEncoder | 50.87ms | 56.82ms | 56.82ms | 50.12ms | +36.13ms (+258%) |

## Reproducibility

- Model: sentence-transformers/all-MiniLM-L6-v2 (cached)
- Random seed: 42 (configured in pipeline)
- Warm-up: 5 retrievals before timed runs
- Measurements: 50 end-to-end, 50 embedding, 200 FAISS search
- No GPU used
- Single-threaded CPU

## Commands

```
cd C:\projects\NyaySaathi\backend
python backend/run_eval.py
python backend/experiment_runner.py
```
