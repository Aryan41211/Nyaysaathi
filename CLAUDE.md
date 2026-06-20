# CLAUDE.md — NyaySaathi ML Pipeline Monitor (AI Coding Rules)

This file is the permanent instruction set for AI assistants editing this repository.

## 1) Project overview & goals
NyaySaathi is a multilingual AI legal guidance platform.
- Convert user legal issues into **procedural next steps** (actions, required documents, escalation/authority guidance).
- Provide a **Django REST API** backend with an ML/NLP pipeline and retrieval/reranking.
- Provide a **React + Vite** frontend.
- Support operational safety: rate limiting, request validation, structured logging, and secure configuration.

## 2) Existing architecture (UI → Services → Core → Persistence)
Map by responsibility:
- **UI**: `frontend/` (pages/components + API client)
- **Services**: backend HTTP entrypoints and orchestration (Django/DRF views/handlers)
- **Core**: language/intent/retrieval/ranking/response logic (e.g., `backend/api/nlp/` and related modules)
- **Persistence**: storage/retrieval of legal workflows and any DB access (MongoDB via env vars; see DB rules below)

## 3) Folder structure & responsibilities
Follow these conventions when implementing new features:
- `frontend/` — UI components, pages, and `frontend/src/services/api.js` for backend calls.
- `backend/` — Django app code and AI pipeline components.
- `backend/api/` (or `nyayasaathi/` app modules) — request handlers, service-layer logic, and integration boundaries.
- `backend/api/nlp/` — core NLP/semantic/retrieval/ranking/query processing.
- `scripts/` — one-off operational scripts (dataset import, embedding generation, etc.).
- `tests/` — automated tests (keep smoke/health/search tests passing).

## 4) Coding standards
- **Type hints**: add explicit type hints to public functions/classes.
- **Docstrings**: document non-trivial functions (purpose, inputs/outputs, side effects).
- **Modular design**: keep modules focused; small composable functions.
- **Avoid God classes**: prefer multiple small classes/functions with single responsibility.
- **Avoid duplicate code**: extract shared logic into utilities; don’t copy/paste across services/core.
- Keep changes minimal and consistent with existing code style.

## 5) Database rules
- Use environment variables for DB connection details.
- Validate any query inputs before sending to DB.
- Prefer parameterized/structured queries; avoid dynamic query string construction.
- Ensure safe defaults for pagination/limits.
- When adding new collections/indexes, document expected access patterns.

## 6) API design standards (Django REST)
- Keep response shapes stable.
  - Success/error envelopes must follow existing response utilities (see `docs/api.md`).
- Validate inputs at the boundary (DRF serializer or request validation middleware).
- Error handling:
  - Return consistent `status/code/message` fields.
  - Don’t leak stack traces or secrets.
- Keep endpoints small: delegate orchestration to service/core modules.
- Use clear naming for request/response fields; avoid breaking changes.

## 7) Streamlit page conventions
No Streamlit in this repo currently.
- If Streamlit is introduced later: follow the existing architecture mapping (UI components call services; core contains logic; persistence stays in DB layer).
- Keep Streamlit code thin: presentation only.

## 8) Logging conventions
- Use structured/JSON logging already configured in Django.
- Use consistent logger names (e.g., `api`, `nyayasaathi.middleware`).
- Log at appropriate levels:
  - INFO for normal operations
  - WARNING for validation issues
  - ERROR for failures
- Never log secrets (API keys, DB URIs, tokens).
- Include enough context to debug (request id/user id if available, without PII).

## 9) Testing requirements
- Add/extend tests under `tests/`.
- New endpoints/features must include:
  - at least one unit test (core/service logic)
  - at least one integration/smoke test (API contract)
- Keep existing tests green (health/search/auth smoke tests).

## 10) Git commit format
Use exactly one of these prefixes:
- `feat:`
- `fix:`
- `refactor:`
- `docs:`

Example: `docs: add CLAUDE.md project guidelines`

## 11) Dependency policy
- Prefer existing libraries already in `requirements.txt` / frontend `package.json`.
- Avoid unnecessary new packages.
- If a new dependency is required, justify it in the PR/commit message.

## 12) Performance rules
- Cache expensive operations (embeddings, retrieval/reranking results) when safe.
- Avoid repeated disk I/O (load once, reuse; memoize where appropriate).
- Batch work when possible (e.g., embedding computations).
- Don’t add high-latency calls inside tight loops.

## 13) Security rules
- **bcrypt only** for password hashing.
- Use environment variables for secrets (never hardcode).
- Input validation everywhere (query params, JSON bodies, path params).
- Be careful with prompt injection / unsafe content handling (defensive filtering where relevant).

---
End of CLAUDE.md

