# METRICS_AND_EVALUATION.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Date:** 2026-11-24

## Retrieval Metrics

| Metric | TF-IDF | BM25 | Dense | Hybrid+Rerank | Label Confidence |
|---|---:|---:|---:|---:|---:|
| Recall@1 | 0.046 | 0.050 | 0.050 | 0.050 | LOW |
| Recall@3 | 0.091 | 0.120 | 0.130 | 0.134 | LOW |
| Recall@5 | 0.120 | 0.183 | 0.202 | 0.207 | LOW |
| Recall@10 | 0.120 | 0.314 | 0.362 | 0.384 | LOW |
| Precision@5 | 0.482 | 0.725 | 0.813 | 0.829 | LOW |
| MRR | 0.951 | 1.000 | 1.000 | 1.000 | LOW |
| nDCG@5 | 0.569 | 0.778 | 0.848 | 0.862 | LOW |

> **WARNING:** All labels are auto-generated (category-based proxy), NOT human-validated. MRR = 1.000 is expected with category-based labels — not indicative of perfect ranking.

## Latency Metrics

| Component | p50 | p95 | p99 | Mean | n |
|---|---:|---:|---:|---:|---:|
| End-to-end retrieval | 7.27ms | 12.68ms | 16.13ms | 7.82ms | 50 |
| Embedding generation | 3.77ms | 4.71ms | 5.18ms | 3.93ms | 50 |
| FAISS search | 0.008ms | 0.014ms | 0.036ms | 0.010ms | 200 |

## Throughput Metrics

| Metric | Value | Unit | n |
|---|---:|---|---:|
| End-to-end throughput | 222 | queries/sec | 50 |

## Evaluation Dataset

| Property | Value |
|---|---|
| Total queries | 201 |
| Label source | Auto-generated (category-based proxy) |
| Human-validated | 0 |
| Relevance grades | None (binary only) |
| Train/dev/test split | None (all data used for evaluation) |

## Label Quality

| Label Type | Count | Confidence | Use Case |
|---|---:|---|---:|
| Auto-generated | 201 | LOW | Development, ablation |
| Human-validated | 0 | — | Production metrics |

## Evaluation Gaps

| Gap | Impact | Priority |
|---|---|---:|
| No human-validated labels | Cannot claim defensible quality | High |
| No train/dev/test split | Evaluation leakage risk | High |
| MRR not discriminative | MRR metric not useful | Medium |
| No relevance grades | nDCG less meaningful | Medium |
| Small corpus (201 cases) | Saturated recall metrics | High |

## Metric Definitions

| Metric | Formula | Label Source |
|---|---|---|
| Recall@K | |relevant ∩ retrieved[:K]| / |relevant| | Auto-generated (category match) |
| Precision@K | |relevant ∩ retrieved[:K]| / K | Auto-generated (category match) |
| MRR | 1 / rank_of_first_relevant | Auto-generated (category match) |
| nDCG@K | DCG / IDCG | Auto-generated (category match, binary relevance) |

## Reproducibility

- Script: `backend/run_eval.py`
- Experiment script: `backend/experiment_runner.py`
- Results: `experiment_results.json`
- Random seed: 42
- Warm-up: 5 retrievals before timed runs
