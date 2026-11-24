# IMPLEMENTATION_CHANGELOG.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform

## [Unreleased]

### Added
- BM25 sparse retrieval index (`backend/api/nlp/bm25_index.py`)
- Hybrid weighted fusion retriever (`backend/api/nlp/hybrid_retrieval.py`)
- Cross-encoder reranker (`backend/api/nlp/cross_encoder_reranker.py`)
- Retrieval evaluation framework (`backend/evaluation/`)
- Corpus engineering module (`backend/api/nlp/corpus_engineering.py`)
- Experiment runner (`backend/experiment_runner.py`)
- Evaluation dataset builder (`backend/evaluation/dataset.py`)
- Annotation guidelines (`backend/evaluation/annotation_guidelines.md`)
- Annotation workflow (`backend/evaluation/annotation_workflow.py`)
- Template dataset (`backend/evaluation/datasets/human_validated_template.json`)

### Changed
- `query_processor.py`: Now uses HybridRetriever as primary retrieval path
- `query_processor.py`: Added hybrid retriever singleton caching
- `hybrid_retrieval.py`: Rewrote with weighted score fusion + content-key matching

### Removed
- None

### Fixed
- BM25 index now handles empty tokenized documents
- Hybrid fusion matches documents by content key across systems

### Metrics Changed

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Dense Recall@5 | 0.2018 | 0.2018 | 0.00 (unchanged) |
| Hybrid Recall@5 (RRF) | 0.1825 | 0.1887 | +0.0062 (+3.4%) |
| Hybrid Recall@5 (Weighted) | — | 0.2010 | New config |
| Hybrid + CrossEncoder Recall@5 | — | 0.2070 | New config |
| Precision@5 (Weighted) | — | 0.8080 | New config |
| nDCG@5 (Weighted) | — | 0.8451 | New config |

## [2.0.0] — Previous Release

- Initial Django REST API
- Semantic search with MiniLM + FAISS
- TF-IDF baseline search
- 201 legal cases corpus
- 3 API tests
