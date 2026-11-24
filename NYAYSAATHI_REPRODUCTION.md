# NyaySaathi Phase 2 — Reproduction Guide

**Project:** NyaySaathi — Legal Information Retrieval System  
**Git SHA:** `1a3eb00`  
**Branch:** `main`  
**Date:** 2026-11-24  
**Environment:** 16 CPU cores, 15.65 GB RAM, CPU-only

---

## 1. Environment Setup

```bash
cd C:\projects\NyaySaathi\backend

# Verify Python version
python --version  # 3.12

# Install dependencies
pip install -r requirements.txt

# Key dependencies:
# - Django 4.x
# - djangorestframework
# - sentence-transformers
# - faiss-cpu
# - numpy
# - rank-bm25
```

---

## 2. Baseline Tests

```bash
cd C:\projects\NyaySaathi\backend

# Run all tests
python manage.py test

# Expected: 3 passed, 0 failed
```

---

## 3. Full Phase 2 Benchmark

```bash
cd C:\projects\NyaySaathi\backend

# Run comprehensive benchmark (all 6 systems, auto + human labels, latency)
python experiment_phase2_benchmark.py

# Output: experiment_results/phase2_benchmark.json
# Runtime: ~10 minutes (loads 4 embedding models)
```

### Benchmark Output Fields

| Field | Description |
|-------|-------------|
| `n_deduped_cases` | 232 unique cases |
| `n_auto_queries` | 232 auto-generated queries |
| `n_human_queries` | 50 human-validated queries |
| `systems.<name>.auto_generated` | Metrics on auto-generated labels |
| `systems.<name>.human_validated` | Metrics on human-validated labels (dense models + BM25 only) |
| `systems.<name>.latency_ms` | p50/p90/p95/p99/mean/max latency |

---

## 4. Model Comparison (MiniLM vs MPNet vs E5 vs BGE)

```bash
cd C:\projects\NyaySaathi\backend

python experiment_model_comparison.py --corpus dataset/expanded_cases.json

# Output: experiment_results/model_comparison.json
# Tests all 4 embedding models on the same 232-case corpus
```

---

## 5. Human-Validated Dataset Creation

```bash
cd C:\projects\NyaySaathi\scripts

python create_human_eval_dataset.py

# Output: backend/evaluation/datasets/human_validated.json
# Creates 50 human-validated queries across all 10 categories
```

---

## 6. Query Normalization Test

```bash
cd C:\projects\NyaySaathi\backend

python -c "
from api.nlp.query_processor import process_query_text
result = process_query_text('salary nahi mila')
print(result)
# Expected: normalized text with synonym expansion
"
```

---

## 7. Key Commands Summary

| Command | Purpose | Output |
|---------|---------|--------|
| `python manage.py test` | Run Django tests | Test results |
| `python experiment_phase2_benchmark.py` | Full Phase 2 benchmark | `experiment_results/phase2_benchmark.json` |
| `python experiment_model_comparison.py` | 4-model comparison | `experiment_results/model_comparison.json` |
| `python scripts/create_human_eval_dataset.py` | Create human-validated dataset | `backend/evaluation/datasets/human_validated.json` |

---

## 8. Expected Results (Baseline)

### Auto-Generated Labels (232 queries)

| System | R@5 | P@5 | MRR | p50 ms |
|--------|-----|-----|-----|--------|
| TF-IDF | 0.1027 | 0.4819 | 0.9400 | 9.51 |
| BM25 | 0.1618 | 0.7552 | 1.0000 | 0.98 |
| MiniLM | 0.1768 | 0.8328 | 1.0000 | 5.50 |
| **MPNet** | **0.1867** | **0.8698** | 1.0000 | 11.80 |
| E5-base | 0.1836 | 0.8595 | 1.0000 | 8.95 |
| BGE-base | 0.1819 | 0.8483 | 1.0000 | 9.27 |
| Hybrid | 0.1870 | 0.8698 | 1.0000 | 28.30 |

### Human-Validated Labels (50 queries)

| System | R@5 | P@5 | MRR |
|--------|-----|-----|-----|
| MPNet (raw) | 0.0120 | 0.0120 | 0.0409 |
| MPNet (normalized) | 0.0160 | 0.0160 | 0.0667 |
| E5-base | 0.0200 | 0.0200 | 0.0440 |
| BM25 | 0.0200 | 0.0200 | 0.0414 |

---

## 9. Benchmark Script Reference

### `experiment_phase2_benchmark.py`

Tests 6 retrieval systems:
1. TF-IDF (lexical via `simple_search`)
2. BM25 (sparse via `BM25Index`)
3. Dense MiniLM (384d)
4. Dense MPNet (768d) — **selected**
5. Dense E5-base (768d)
6. Dense BGE-base (768d)
7. Hybrid (weighted fusion)

Measures: Recall@1/3/5/10, Precision@1/3/5/10, nDCG@1/3/5/10, MRR, p50/p90/p95/p99 latency.

### `experiment_model_comparison.py`

Tests 4 embedding models on identical queries/labels for fair comparison. Includes E5 query prefix handling ("query: ").

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| Model download fails | Ensure internet access for first run; models cached in `~/.cache/huggingface/` |
| FAISS dimension mismatch | Ensure all models use same corpus; restart Python process between model tests |
| `get_sentence_embedding_dimension` deprecation | Use `get_embedding_dimension()` instead (already fixed in scripts) |
| Human-validated R@5 appears low | Expected — only 5 relevant cases per query out of 232; R@5=0.02 = 1/5 found |
| Hybrid retrieval fails | Run in fresh Python process; singleton dimension conflict when mixed with other models |

---

## 11. Git Commits

| SHA | Message |
|-----|---------|
| `ba99741` | feat(eval): benchmark on expanded 500-case corpus |
| `b540b48` | feat(eval): add human-validated dataset + phase2 benchmark baseline |
| `1a3eb00` | feat(retrieval): MPNet embeddings + query caching + normalization |

All commits on `main` branch. No pushes yet (pending approval).
