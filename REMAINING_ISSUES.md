# REMAINING_ISSUES.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Date:** 2026-11-24

## Critical Issues

| Issue | Impact | Priority | Status |
|---|---|---:|---|
| Corpus only 201 cases | Saturated recall metrics, not representative | High | Open |
| No human-validated evaluation labels | Cannot claim defensible quality | High | Open |
| No train/dev/test split | Evaluation leakage risk | High | Open |
| No persistent vector store | Index rebuilt on startup | Medium | Open |
| No Django models for cases | No database persistence | Medium | Open |

## Medium Issues

| Issue | Impact | Priority | Status |
|---|---|---:|---|
| No Docker containerization | No reproducible deployment | Medium | Open |
| No CI/CD pipeline | No automated testing | Medium | Open |
| No Prometheus/Grafana monitoring | No observability | Medium | Open |
| Cross-encoder adds 36ms latency | Latency/quality trade-off | Medium | Documented |
| MRR = 1.000 not discriminative | MRR metric not useful | Low | Documented |
| No human-validated label workflow | Requires annotators | Medium | Open |

## Minor Issues

| Issue | Impact | Priority | Status |
|---|---|---:|---|
| No authentication system | No JWT/RBAC yet | Low | Planned (Phase 1A) |
| No rate limiting tests | Untested security | Low | Open |
| No security headers tests | Untested security | Low | Open |
| Coverage below 85% target | Incomplete test coverage | Low | Open |

## Issues Resolved in This Audit

| Issue | Resolution |
|---|---|
| BM25 not integrated into search path | Added HybridRetriever, wired into query_processor |
| RRF diluting dense results | Replaced with weighted fusion (dense=0.7, bm25=0.2, tfidf=0.1) |
| No retrieval evaluation framework | Added complete evaluation framework with metrics |
| No corpus provenance tracking | Added corpus_engineering.py with provenance + dedup |
| No duplicate detection | Added exact hash + TF-IDF similarity detection |

## Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Corpus counts reproducible | DONE |
| Ingestion repeatable | DONE |
| Retrieval evaluation reproducible | PARTIAL (auto labels only) |
| Baseline comparisons fair | DONE |
| API tests pass | DONE |
| Index persistence validated | OPEN |
| Documentation matches implementation | DONE |

## Next Steps

1. Recruit legal annotators for human-validated labels (50-100 queries)
2. Create train/dev/test splits
3. Re-run evaluation with human-validated labels
4. Add Docker containerization
5. Add CI/CD pipeline
6. Add Prometheus/Grafana monitoring
7. Implement JWT auth + RBAC (Phase 1A)
