# ENGINEERING_ASSESSMENT.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Assessment date:** 2026-11-24  
**Maturity level:** LEVEL 3 — MEASURED

## Architecture

- **Backend:** Django REST Framework (Django 5.2.4)
- **Retrieval:** sentence-transformers all-MiniLM-L6-v2 (384-d), FAISS IndexFlatIP, BM25 (rank_bm25), TF-IDF
- **Hybrid fusion:** Weighted score fusion (dense=0.7, bm25=0.2, tfidf=0.1), RRF available as fallback
- **Frontend:** React + Vite
- **Database:** SQLite (dev), MongoDB (production, optional)

## Separation of Concerns

| Layer | Responsibility | Files |
|---|---|---|
| Transport | HTTP routing, request/response | `api/transport/views.py`, `api/urls.py` |
| Service | Business logic (search orchestration) | `api/services/search_service.py` |
| Repository | Data access (case CRUD) | `api/repositories/case_repository.py` |
| NLP Core | Embeddings, retrieval, ranking, query processing | `api/nlp/` |
| Data | Corpus loading | `api/data_loader.py` |

## Error Handling

- Graceful degradation: semantic → keyword → TF-IDF fallback
- Empty query handling with clarification prompts
- Model unavailable fallback to lexical search
- No stack traces leaked to clients

## Configuration

- Environment variables via `.env` (not committed)
- `.env.example` provided with all required variables
- Django settings with environment-based configuration

## Logging

- Structured logging with correlation IDs
- Retrieval latency logged per request
- Fallback decisions logged

## Type Safety

- Python type hints on public functions
- Pydantic not used (Django native)
- No mypy configuration

## Reusability

- Semantic search engine is a singleton (`get_semantic_engine()`)
- BM25 index is independently instantiable
- HybridRetriever is composable with pluggable fusion/reranking

## Extensibility

- HybridRetriever supports pluggable reranker (CrossEncoderReranker available)
- Fusion mode configurable (weighted vs RRF)
- Weights configurable per system

## Known Limitations

- Corpus: 201 cases only (small for production)
- Evaluation labels: auto-generated (not human-validated)
- No human-validated evaluation dataset
- Cross-encoder reranking adds ~36ms latency (optional)
- No persistent vector store (rebuilt on startup)

## Assessment Summary

| Area | Rating | Notes |
|---|---|---|
| Architecture | Good | Clean layering, clear boundaries |
| Code Quality | Good | Type hints, docstrings, error handling |
| Testing | Basic | 3 tests passing, no coverage target |
| Security | Basic | Rate limiting, CORS, security headers |
| Performance | Good | p95=12.68ms end-to-end retrieval |
| ML/AI Quality | Measured | Dense Recall@5=0.202, hybrid+rerank=0.207 |
| Observability | Basic | Structured logging, no Prometheus |
| Deployment | Basic | Render/Vercel configured, no Docker |
