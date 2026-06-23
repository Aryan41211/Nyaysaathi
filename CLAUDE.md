# CLAUDE.md — NyaySaathi Permanent Project Memory (AI Coding Rules)

This file is the permanent instruction set for AI assistants editing this repository.  
Treat it as the “source of truth” for architecture, contracts, security expectations, and coding standards.

---

## # Project Identity

**Name:** NyaySaathi  
**Vision:** Make multilingual legal guidance accessible, safe, and operationally reliable—turning user legal problems into clear next steps and escalation guidance.  
**Purpose:** Provide a Django REST API + ML/NLP retrieval pipeline + React UI that converts user questions into procedural actions, required documents, and authority escalation paths.  
**Target Users:**
- Individuals seeking procedural legal guidance (Hindi/Marathi/mixed inputs)
- Non-lawyers needing “what to do next” instructions
- Support teams validating and improving the guidance system

**Core Features (Phase-aligned):**
- Multilingual normalization (incl. Hinglish variants)
- Intent detection / routing (classify query type)
- Semantic retrieval (embedding + FAISS-like index)
- Lexical fallback when semantic model unavailable
- Reranking of candidate workflows (when available)
- Response generation into stable JSON API envelope
- Frontend search + case detail pages
- Health checks + operational safety middleware (rate limiting, request validation, security headers)
- (Planned by sprint scope) JWT auth: access + refresh + expiry + logout-all-sessions + RBAC
- (Planned ML improvements) embedding cache/FAISS warmup/persistent vector store integration + fallback retrieval + model versioning + health checks/integrity verification (no full auto rebuild)

**Long Term Goal:** Production-grade, secure, observable legal guidance with continuous improvement loops, reliable ML retrieval, and strong security posture.

---

## # Architecture (Complete)

### High-level Architecture
**Request Flow:**
1. **Frontend** collects user input and calls the backend.
2. **Backend (Django/DRF)**:
   - middleware applies: request validation + security headers + rate limit
   - routing maps endpoints to views
   - views delegate to service/repository/core modules
3. **ML/NLP core**:
   - normalize/language handling
   - intent classification/routing
   - embedding retrieval (semantic engine)
   - reranking (optional / configured)
   - fallback retrieval (lexical) when semantic components unavailable
4. **Response contract**:
   - stable success/error JSON envelope
   - consistent fields for UI rendering and future auditing

### Frontend
- **Tech:** React + Vite
- **Entrypoints:** `frontend/src/main.jsx`
- **Routing/Pages:** `frontend/src/pages/*`
- **API Client:** `frontend/src/services/api.js`
- **Key Components:** `SearchBox`, `ResultsPage`, `CaseDetailPage`, `ProtectedRoute`, `AuthContext`, `LanguageContext`

### Backend
- **Tech:** Django + Django REST Framework
- **Entry points:**
  - `manage.py`
  - `nyayasaathi/urls.py`
- **Middleware:** `nyayasaathi/middleware/*`
- **Transport layer / HTTP views:** `api/transport/views.py` (layered skeleton exists)
- **Legacy endpoints:** implemented historically in `api/views.py` (ensure parity)
- **Service layer / ML orchestration:** `api/services/*`
- **Repository layer:** `api/repositories/*`
- **Core ML logic:** `api/nlp/*` and/or `local_nyaysaathi/*` (depending on which is active)

### APIs (base)
Documentation:
- `docs/api.md`
- `docs/architecture.md`

### Database
- **Primary runtime expectation:** MongoDB (via env vars)
- **Local/test runtime:** Django test DB (sqlite/memory) used for endpoint tests
- **Collections/models:** should be treated as Mongo-backed “legal workflow retrieval” data

### Authentication / Authorization
- **Planned (current sprint scope):** JWT access + refresh + expiry + logout-all-sessions + RBAC
- **Email verification + password reset:** disabled stubs (must be present but no-op or safe “not enabled” responses)

### AI/ML Components
- **Semantic engine:** embedding + retrieval
- **FAISS index:** retrieval acceleration
- **Reranker:** candidate ranking
- **Fallback:** lexical/keyword retrieval if semantic model unavailable or fails
- **Model versioning:** required for safe rollout and integrity checks
- **Health checks/integrity verification:** verify index availability, embedding cache warm state, model version, and fallback readiness

### Caching
- Cache expensive operations:
  - query embedding cache
  - retrieval results keyed by canonical normalized query + top_k
  - “hot query TTL” extension rules

### Monitoring / Observability
- Structured logging (JSON when configured)
- Track rates:
  - fallback_rate, low_confidence_rate, error_rate, cache_hit_rate
- Metrics/health endpoints (document in `docs/scalability_observability_architecture.md`)

### Deployment Flow
- Backend: Render (gunicorn + migrations + collectstatic)
- Frontend: Vercel
- Config via environment variables (`backend/.env.example` and `frontend/.env.example` if present)

---

## # Folder Structure (Tree)

Use `list_files` to regenerate exact tree when needed; the repo currently includes:
- `frontend/` (React app)
- `nyayasaathi/` (Django project package + middleware + settings)
- `api/` (Django app with HTTP endpoints and ML orchestration skeleton)
- `local_nyaysaathi/` (alternate/local ML implementation)
- `scripts/` (operational utilities: embeddings/index/import scripts)
- `dataset/` (training/synthetic data)
- `docs/` (architecture, API, deployment guidance)
- `tests/` (API test suite)

---

## # Request & Response Contracts (API Safety)

**General Rules**
- Stable JSON envelope for all responses.
- Error payloads must be consistent: `code`, `message`, and appropriate `status` indicator.
- Never leak stack traces or secrets.
- Maintain backward compatibility—versioning only when absolutely necessary.

**Response Utility Convention**
- Success/error envelopes must follow existing utilities (refer to `docs/api.md` and existing `response_utils` patterns).

---

## # Coding Standards (Strict)

### SOLID / DRY / OOP
- **Single Responsibility:** Each module class/function must have one primary responsibility.
- **Open/Closed:** Add behavior via extension points; avoid editing large switch statements.
- **Liskov:** Keep interfaces consistent.
- **Interface Segregation:** Split responsibilities for auth, retrieval, reranking, response formatting.
- **Dependency Inversion:** transport → service → repository → core; avoid core importing transport.

### Type hints / Docstrings
- Add explicit type hints to public functions/classes.
- Add docstrings for non-trivial functions:
  - purpose
  - inputs/outputs
  - side effects
  - exceptions/errors

### Naming conventions
- Python:
  - `snake_case` for functions/vars
  - `CamelCase` for classes
  - constants in `UPPER_SNAKE_CASE`
- JavaScript:
  - `camelCase` for functions/vars
  - `PascalCase` for components

### File structure rules
- Keep transport/HTTP logic in `api/transport/*` and/or view modules.
- Keep ML logic in `api/nlp/*` or `local_nyaysaathi/*`.
- Keep persistence/retrieval access in `api/repositories/*`.
- Keep orchestration in services.

### Error handling rules
- Validate inputs at the boundary (DRF serializer or middleware).
- Handle “model unavailable” deterministically:
  - return successful responses using fallback retrieval
  - log degraded mode
- Raise/return controlled error payloads (never raw exceptions to clients).

### Logging rules (secure)
- Prefer structured logs:
  - request method/path/status/duration
  - request id / user id if present (no PII)
  - normalized_query, detected intent, confidence, decision path (answer vs fallback)
- Never log secrets:
  - API keys, DB URIs, JWTs, refresh tokens, passwords, Authorization headers

---

## # API Contracts (Endpoint Inventory Guidance)

This agent must maintain a current inventory of endpoints by reading:
- `nyayasaathi/urls.py`
- `api/urls.py`
- `api/views.py`
- `api/transport/views.py`

**Contract checklist per endpoint**
- Route + method
- Request schema (body/query/path)
- Response schema (success + error)
- Authentication requirement (if any)
- Permissions/RBAC requirement (if any)
- Rate limiting and validation behavior
- Example requests/responses

**Known endpoints from docs (validate in code):**
- `GET /api/health`
- `GET /api/categories/`
- `GET /api/cases/`
- `GET /api/case/<subcategory>/`
- `GET|POST /api/search/`
- `POST /api/classify`
- `GET /api/health/ai/`
- `GET /api/user/history`
- Auth:
  - `POST /api/auth/signup`
  - `POST /api/auth/login`

---

## # Database Analysis Expectations

Any Mongo-backed workflow retrieval should define:
- Data models (collections)
- Relationships (if any)
- Constraints/indexes for query patterns
- Pagination/limit enforcement
- Migration/seed scripts (if any)

If Django models exist in `api/models.py`, treat them as authoritative for local/test structure; Mongo remains runtime.

---

## # Machine Learning System (Detailed Rules)

### Embeddings
- Embedding cache must be keyed by canonical normalized query.
- Cache TTL rules:
  - separate TTL for “hot queries”
- Guard against concurrency stampedes (use locks/semaphores)

### Vector DB / Storage
- Supported retrieval backends:
  - FAISS index artifacts
  - persistent vector store integration (planned)
- Must support “index not available”:
  - detect at startup or health check
  - automatically degrade to lexical fallback

### Retrieval
- Retrieval pipeline:
  1. semantic retrieval (embedding search)
  2. candidate selection
  3. reranking (if configured)
  4. workflow mapping to response contract

### Fallbacks
- Lexical fallback when semantic model unavailable or errors occur.
- Fallback decision must be visible in logs and/or response metadata (if contract allows).

### Health checks & integrity
- AI health endpoint must verify:
  - embedding model availability
  - FAISS/persistent vector store readiness
  - embedding cache warm strategy status
  - model version compatibility

### Versioning
- Model version must be included in logs.
- Responses may include model version metadata if schema allows (do not break UI).

---

## # Security Audit Standards (Hard Requirements)

**JWT / RBAC (Phase 1A)**
- JWT access token: short expiry
- JWT refresh token: longer expiry
- Refresh token rotation (recommended if library supports)
- Logout-all-sessions:
  - server-side invalidation list or token versioning
- RBAC enforcement:
  - endpoints must check permissions
- Email verification/password reset:
  - stubs must not allow bypass

**Rate limiting**
- Apply to auth & search/classify endpoints.
- Ensure rate limit middleware does not break legitimate clients.

**CORS**
- Only allow configured origins.
- Must include Vercel frontend host(s) in production.

**CSRF**
- For cookie-based auth routes: enforce CSRF properly.
- For bearer-token auth routes: CSRF generally not required (but confirm implementation).

**Prompt injection defense / RAG poisoning defense**
- Treat retrieved content as untrusted:
  - strip malicious instructions patterns
  - apply allowlist/neutralization heuristics in response generator
- Never allow user query to directly alter system behavior beyond retrieval.
- Ensure response generator has strict formatting constraints.

**SQL injection**
- Not relevant if using Mongo, but keep ORM queries parameterized if any SQL exists.

**XSS**
- Ensure frontend sanitizes any server-provided HTML.
- API should not return raw HTML unless explicitly required.

**Unsafe file uploads**
- Currently none; if added, strictly validate type/size and store safely.

**Dependency vulnerabilities**
- Keep dependencies pinned by range.
- Update with security fixes; document changes.

**Secure logging**
- Never log secrets or tokens.

---

## # Deployment (Production Readiness)

### Docker
- If Docker is introduced later:
  - multi-stage build
  - non-root user
  - explicit healthcheck endpoint

### CI/CD
- Expected pipeline:
  - tests + lint (if present)
  - build frontend
  - run migrations (backend)
  - deploy to Render/Vercel

### Environment variables / secrets management
- Use environment variables.
- Do not commit secrets.
- Provide `.env.example` with required keys.

### Rollback & backups
- Maintain database/collection backup strategy (Mongo snapshots).
- Ensure safe rollback plan for ML artifacts:
  - keep previous FAISS/vector store artifacts
  - model version pinning

---

## # Monitoring (Production Observability)

**Metrics (recommended)**
- fallback_rate
- low_confidence_rate
- error_rate
- cache_hit_rate
- avg_latency_ms
- feedback_accuracy

**Health endpoints**
- `/api/health`
- `/api/health/ai/`

**Error tracking**
- Structured logs + optional integration (if added later)

**Logging**
- Include request metadata:
  - method/path/status/duration/request_id
- Include ML metadata:
  - normalized_query, detected intent, confidence, decision path

**Prometheus (if introduced)**
- Provide exporters for the metrics above.

---

## # Testing Policy (Strict)

### Existing tests (keep passing)
- `tests/test_basic_api.py`
- `tests/test_health_endpoint.py`
- `tests/test_search_smoke.py`
- `api/tests.py`

### Required test types for new changes
1. **Unit tests** (core/service logic)
2. **Integration/API tests** (contract and error paths)
3. **Security tests**:
   - auth failures
   - RBAC denies
   - rate limit behavior
4. **ML tests**:
   - semantic unavailable → lexical fallback works
   - index/model integrity checks
   - deterministic response shape

### Coverage goals
- Critical-path endpoints must be covered for:
  - happy path
  - validation error path
  - “model unavailable” fallback path
  - unexpected internal error (no secrets leakage)

### Stress/performance tests (as feasible)
- Search/classify burst load tests
- Embedding cache hit-rate validation

---

## # AI Agent Rules (Non-negotiable)

Before changing code:
1. Understand architecture and current contracts.
2. Identify transport → service → repository → core boundaries.
3. Identify impacted endpoints and response schemas.
4. Ensure backward compatibility.

During implementation:
- Never break existing APIs.
- Update tests for the changed behavior.
- Update documentation when contracts/schema change.
- Preserve backward compatibility; if impossible, introduce new endpoints.
- Never expose secrets.
- Prefer scalable solutions (caching, concurrency guards, bounded resources).

---

## # Production Checklist (Phase gate)

Authentication: ✓ (after Phase 1A work is merged)  
Authorization: ✓  
Security: ✓  
Caching: ✓  
Monitoring: ✓  
CI/CD: ✓  
Docker: ✓ (if introduced)  
Tests: ✓  
Logging: ✓  
Backups: ✓  
Secrets: ✓  
Health checks: ✓  

---

## # File-Specific Guardrail (Known Critical Issue)

- `api/transport/views.py` must preserve parity with legacy behavior in `api/views.py`.
- Ensure `case_detail` returns correct 404 semantics consistent with legacy implementation.

---

End of CLAUDE.md

