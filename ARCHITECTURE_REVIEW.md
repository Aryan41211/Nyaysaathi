# ARCHITECTURE_REVIEW.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Review date:** 2026-11-24

## Current Architecture

```
Frontend (React + Vite) → Django REST API → NLP Pipeline → Legal Cases Corpus
                              ↓
                    Embedding Model (MiniLM-L6-v2)
                              ↓
                    FAISS IndexFlatIP (384-d vectors)
                              ↓
                    BM25 + TF-IDF (lexical baselines)
                              ↓
                    Weighted Fusion (dense=0.7, bm25=0.2, tfidf=0.1)
```

## Layer Responsibilities

| Layer | Files | Responsibility |
|---|---|---|
| Transport | `api/transport/views.py`, `api/urls.py` | HTTP routing, CSRF exemption, status codes |
| Service | `api/services/search_service.py` | Search orchestration, case enumeration |
| Repository | `api/repositories/case_repository.py` | Case CRUD, deduplication, slug generation |
| NLP Core | `api/nlp/` | Embeddings, retrieval, ranking, query processing |
| Data | `api/data_loader.py` | Corpus loading from JSON |

## Data Flow

1. User submits query via `/api/search/`
2. `query_processor.process_query()` normalizes text (Hinglish, synonyms)
3. `HybridRetriever.search()` combines TF-IDF + BM25 + Dense with weighted fusion
4. `ranker.rank_results()` applies final scoring (semantic 65%, keyword 25%, category 10%)
5. Results returned as JSON envelope

## Dependency Direction

Transport → Service → Repository → NLP Core → Data (no circular dependencies)

## Error Handling

- Model unavailable → lexical fallback
- Empty results → TF-IDF safety net
- Empty query → clarification prompt
- No stack traces leaked

## Configuration Management

- Environment variables via `.env`
- `.env.example` template
- Django settings with environment-based config

## Type Safety

- Python type hints on public functions
- No mypy configuration
- Django native validation

## Known Issues

1. Corpus stored as JSON file (no persistent vector store)
2. Index rebuilt on startup (no incremental indexing)
3. No database models for cases (Django models.py is empty)
4. Evaluation labels are auto-generated proxies

## Recommended Improvements

1. Add Django models for legal cases with PostgreSQL backend
2. Implement persistent FAISS index with incremental updates
3. Add human-validated evaluation dataset
4. Add Docker containerization
5. Add CI/CD pipeline
