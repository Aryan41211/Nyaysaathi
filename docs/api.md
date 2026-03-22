# API Design

## Base URL

- Local: http://localhost:8000
- Production: https://<render-service>.onrender.com

## Health

- GET /api/health
- Response:

```json
{
  "status": "ok"
}
```

## Main Routes

- GET or POST /api/search
- POST /api/classify
- GET /api/categories/
- GET /api/cases/
- GET /api/case/<subcategory>/
- GET /api/health/ai/
- GET /api/user/history

## Auth Routes

- POST /api/auth/signup
- POST /api/auth/login

## Admin Routes

- GET /api/admin/users
- GET /api/admin/queries
- POST /api/admin/workflows

## Response Contract

- Success payloads use a stable JSON envelope from legal_cases.response_utils.success_response.
- Errors use legal_cases.response_utils.error_response with code and message.
