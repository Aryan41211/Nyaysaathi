# IMPLEMENTATION_ROADMAP.md — NyaySaathi

**Project:** NyaySaathi  
**Roadmap date:** 2026-11-24

## Phase 1: Corpus Engineering (IN PROGRESS)

| Task | Status | Description |
|---|---|---|
| Corpus provenance tracking | DONE | `corpus_engineering.py` with DocumentProvenance |
| Duplicate detection | DONE | Exact hash + TF-IDF similarity |
| Corpus validation report | DONE | `validate_corpus()`, `generate_validation_report()` |
| Incremental update pipeline | DONE | `incremental_update()` skips exact duplicates |
| Expand corpus with legally accessible sources | PLANNED | Research Indian Kanoon, court portals, government datasets |

## Phase 2: Retrieval Engine (DONE)

| Task | Status | Description |
|---|---|---|
| BM25 sparse index | DONE | `bm25_index.py` |
| Hybrid weighted fusion | DONE | `hybrid_retrieval.py` (dense=0.7, bm25=0.2, tfidf=0.1) |
| Cross-encoder reranker | DONE | `cross_encoder_reranker.py` |
| Wired into API search path | DONE | `query_processor.py` uses HybridRetriever |

## Phase 3: Evaluation (PARTIAL)

| Task | Status | Description |
|---|---|---|
| Auto-generated labels | DONE | 201 queries, category-based proxy |
| Human-validated annotation guidelines | DONE | `annotation_guidelines.md` |
| Annotation workflow script | DONE | `annotation_workflow.py` |
| Template dataset | DONE | `human_validated_template.json` |
| Human-validated labels (50-100 queries) | PLANNED | Requires legal annotators |
| Train/dev/test splits | PLANNED | Requires human-validated labels |

## Phase 4: API & Performance (DONE)

| Task | Status | Description |
|---|---|---|
| End-to-end p95 latency | DONE | 12.68ms |
| Latency breakdown | PLANNED | Component-level measurement |

## Phase 5: Quality Gate

| Criterion | Status |
|---|---|
| Corpus counts reproducible | DONE |
| Ingestion repeatable | DONE |
| Retrieval evaluation reproducible | PARTIAL (auto labels only) |
| Baseline comparisons fair | DONE |
| API tests pass | DONE |
| Index persistence validated | PLANNED |
| Documentation matches implementation | DONE |

## Not Started

- Docker containerization
- CI/CD pipeline
- Prometheus/Grafana monitoring
- Human-validated evaluation (requires annotators)
