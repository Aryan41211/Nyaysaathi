# NyaySaathi Scalability and Observability Architecture

## Runtime Layers

1. API Layer (Django/DRF)
- Sync endpoints for low-latency read traffic.
- Async endpoints:
  - `POST /api/search/async`
  - `GET /api/search/async/{task_id}`
- Search throttling and classify throttling enabled to protect backend under burst.

2. Search Service Layer
- Query result cache keyed by canonical normalized query + `top_k`.
- Hot query extension: frequently repeated queries get longer cache TTL.
- Concurrency guard: bounded semaphore for semantic retrieval path.
- Overload shedding: if semantic concurrency pool is saturated, route to keyword fallback.

3. Embedding Layer
- FAISS index with configurable type:
  - `flat` for exact similarity
  - `hnsw` for high-throughput approximation
- Query embedding cache in semantic engine to avoid repeated model encoding.

4. Async/Queue Layer
- Primary: Celery + Redis broker/backend when configured.
- Fallback: local ThreadPoolExecutor for single-node deployments.

## Horizontal Scaling Plan

1. Stateless API pods
- Deploy multiple API replicas behind load balancer.
- Keep local cache for hot reads; use shared Redis cache for multi-replica coherence.

2. Queue workers
- Separate worker deployment for async search tasks.
- Autoscale worker count by queue depth and latency SLO.

3. Data and index strategy
- Prebuild FAISS artifacts during CI/CD and mount read-only volume at startup.
- Warm query embedding cache for top frequent queries from logs.

## Monitoring and Alerting

Tracked rates over rolling window:
- `fallback_rate`
- `low_confidence_rate`
- `error_rate`
- `cache_hit_rate`
- `avg_latency_ms`
- `feedback_accuracy` (when feedback events exist)

Alert rules:
- warning when `low_confidence_rate >= ALERT_LOW_CONF_RATE`
- warning when `fallback_rate >= ALERT_FALLBACK_RATE`
- critical when `error_rate >= ALERT_ERROR_RATE`

Structured JSON logs contain:
- request metadata (method/path/status/duration/request_id)
- query and normalized_query
- detected intent
- confidence
- final decision (`answer` or `fallback`)

## Production Environment Variables

- `SEMANTIC_MAX_CONCURRENCY`
- `SEARCH_RESULT_CACHE_TTL_SECONDS`
- `HOT_SEARCH_RESULT_CACHE_TTL_SECONDS`
- `HOT_QUERY_THRESHOLD`
- `OVERLOAD_ALLOW_KEYWORD_FALLBACK`
- `QUERY_EMBED_CACHE_TTL_SECONDS`
- `QUERY_EMBED_CACHE_SIZE`
- `THROTTLE_SEARCH_RATE`
- `LOG_JSON`
- `OBS_WINDOW_SECONDS`
- `ALERT_LOW_CONF_RATE`
- `ALERT_FALLBACK_RATE`
- `ALERT_ERROR_RATE`
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` (optional)
