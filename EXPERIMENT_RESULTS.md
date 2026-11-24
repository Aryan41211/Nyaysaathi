# EXPERIMENT_RESULTS.md — NyaySaathi Retrieval Experiments

**Project:** NyaySaathi  
**Baseline:** Auto-generated labels, 201 queries, category-based relevance

## Baseline (measured, before optimization)

| System | Recall@5 | Precision@5 | MRR | nDCG@5 |
|---|---:|---:|---:|---:|
| TF-IDF | 0.1204 | 0.4816 | 0.9515 | 0.5687 |
| BM25 | 0.1825 | 0.7254 | 1.0000 | 0.7781 |
| Dense (MiniLM+FAISS) | 0.2018 | 0.8129 | 1.0000 | 0.8484 |
| Hybrid (RRF, k=60) | 0.1825 | 0.7254 | 1.0000 | 0.7781 |

> **Note:** MRR = 1.000 for BM25/Dense/Hybrid is expected with category-based proxy labels — the first result is usually same-category. MRR is not discriminative with these labels.

## Experiments Executed

| Exp ID | Hypothesis | Config | Status | Result |
|---|---|---|---|---|
| E001 | Weighted hybrid (dense-weighted) beats RRF | w_dense=0.7, w_bm25=0.2, w_tfidf=0.1 | COMPLETED | R@5: 0.2010 vs RRF 0.1887 (+6.5%) |
| E002 | Cross-encoder reranking on top-20 improves Recall@5 | cross-encoder/ms-marco-MiniLM-L-6-v2 | COMPLETED | R@5: 0.2070 vs dense 0.2018 (+2.6%), P@5: 0.8289 vs 0.8129 (+2.0%), nDCG@5: 0.8621 vs 0.8484 (+1.6%) |
| E003 | BM25 parameter tuning | — | SKIPPED | BM25 already weak; weighted fusion gives it low weight |
| E004 | Query expansion with legal synonyms | — | PARTIAL | Already implemented in query_processor.py |
| E005 | Combined: weighted hybrid + reranking | Weighted 0.7/0.2/0.1 + CrossEncoder | COMPLETED | Best overall: R@5=0.2070, P@5=0.8289, nDCG@5=0.8621 |

## Latency Trade-off (Cross-Encoder)

| Config | p50 | p95 | p99 | Mean | Overhead vs dense |
|---|---:|---:|---:|---:|---:|
| Dense only | 13.40ms | 22.60ms | 22.60ms | 13.99ms | — |
| Dense + CrossEncoder | 50.87ms | 56.82ms | 56.82ms | 50.12ms | +36.13ms (+258%) |

**Decision:** Cross-encoder reranking is kept as an **optional** configuration (not default) due to 36ms latency overhead for modest quality gain. Default fusion is Weighted 0.7/0.2/0.1 without reranking.

## Final Selected Configuration

**Weighted fusion: dense=0.7, bm25=0.2, tfidf=0.1**  
- Recall@5: 0.2010 (vs dense-only 0.2018, essentially equivalent)
- Precision@5: 0.8080 (vs dense-only 0.8129, essentially equivalent)
- nDCG@5: 0.8451 (vs dense-only 0.8484, essentially equivalent)
- Latency: ~14ms p50 (no reranking overhead)

**Best quality (with reranking):** Weighted 0.7/0.2/0.1 + CrossEncoder  
- Recall@5: 0.2070 (+2.6% vs dense)  
- Precision@5: 0.8289 (+2.0% vs dense)  
- Latency: ~51ms p50 (+258% vs dense)
