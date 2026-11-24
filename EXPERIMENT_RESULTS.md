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

> **WARNING:** All labels are auto-generated (category-based proxy), NOT human-validated. MRR = 1.000 is expected with category-based proxy labels — not indicative of perfect ranking.

## Experiments Executed

| Exp ID | Hypothesis | Config | Status | Result |
|---|---|---|---|---|
| E001 | Weighted hybrid (dense-weighted) beats RRF | w_dense=0.7, w_bm25=0.2, w_tfidf=0.1 | COMPLETED | R@5: 0.2010 vs RRF 0.1887 (+6.5%) |
| E002 | Cross-encoder reranking on top-20 improves Recall@5 | cross-encoder/ms-marco-MiniLM-L-6-v2 | COMPLETED | R@5: 0.2070 vs dense 0.2018 (+2.6%), P@5: 0.8289 vs 0.8129 (+2.0%), nDCG@5: 0.8621 vs 0.8484 (+1.6%), **+36ms latency** |
| E003 | BM25 parameter tuning | BM25 k1=1.2, b=0.75 | SKIPPED | BM25 already weak; weighted fusion gives it low weight |
| E004 | Query expansion with legal synonyms | Hinglish + domain synonyms | PARTIAL | Already implemented in query_processor.py |
| E005 | Embedding model upgrade (MiniLM → MPNet) | sentence-transformers/all-mpnet-base-v2 (768d) | COMPLETED | R@5: 0.2145 vs MiniLM 0.2018 (**+6.3%**), P@5: 0.8587 vs 0.8129 (**+5.6%**), nDCG@5: 0.8836 vs 0.8484 (+4.1%), eval time: 14.8s vs 10.2s (+5.9s) |
| E006 | MPNet + CrossEncoder reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 | COMPLETED | R@5: 0.2058 vs MPNet 0.2145 (**-3.4% worse**), P@5: 0.8239 vs 0.8587, nDCG@5: 0.8581 vs 0.8836, eval time: 59.6s vs 14.8s |

## Latency Trade-off (Cross-Encoder)

| Config | p50 | p95 | p99 | Mean | Overhead vs Dense |
|---|---:|---:|---:|---:|---:|
| Dense only (MiniLM) | 13.40ms | 22.60ms | 22.60ms | 13.99ms | — |
| Dense + CrossEncoder | 50.87ms | 56.82ms | 56.82ms | 50.12ms | +36.13ms (+258%) |

## Final Selected Configuration

**Embedding model: sentence-transformers/all-mpnet-base-v2 (768 dims)**
- Recall@5: 0.2145 (+6.3% vs MiniLM 0.2018)
- Precision@5: 0.8587 (+5.6% vs MiniLM 0.8129)
- nDCG@5: 0.8836 (+4.1% vs MiniLM 0.8484)
- Evaluation time: 14.8s for 201 queries (+5.9s vs MiniLM)

**Cross-encoder reranking: NOT recommended**
- Decreases Recall@5 from 0.2145 to 0.2058 (-3.4%)
- Adds 44.8s to evaluation time for 201 queries
- Not worth the latency/quality trade-off

**Hybrid fusion (TF-IDF + BM25 + Dense):**
- With MiniLM: Recall@5 = 0.2010 (essentially same as dense alone 0.2018)
- RRF fusion actually decreases Recall@5 to 0.1825
- Not worth the complexity for this corpus size

## Summary of Verified Improvements

| Change | Recall@5 | Precision@5 | nDCG@5 | Latency Impact |
|---|---:|---:|---:|---:|
| Baseline (MiniLM) | 0.2018 | 0.8129 | 0.8484 | 10.2s |
| MPNet embeddings | **0.2145** | **0.8587** | **0.8836** | 14.8s (+5.9s) |
| MPNet + CrossEncoder | 0.2058 | 0.8239 | 0.8581 | 59.6s (+48.8s) |

**Best configuration:** MPNet embeddings alone — best quality with acceptable latency.
