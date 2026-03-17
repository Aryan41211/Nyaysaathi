# NyaySaathi

NyaySaathi is an AI legal guidance platform for India that turns plain-language complaints into actionable legal next steps.

Users describe a problem in Hindi, English, or Hinglish. NyaySaathi returns:
- likely legal category and subcategory
- what to do next (step-by-step)
- required documents
- who to contact
- laws, portals, helplines, and complaint templates where available

## Why it stands out

- Hinglish-aware intent understanding (real-world, mixed language input)
- FastAPI + MongoDB production API
- JWT auth with role-based admin access
- Admin dashboard for users, queries, and workflow management
- Confidence-aware responses with clarification prompts
- Caching + feedback loop for better speed and quality over time

## Tech stack

- Backend: Python, FastAPI, MongoDB, PyMongo
- AI: sentence-transformers, fallback-safe classification pipeline
- Frontend: React, TypeScript, Vite

## Quick start

1. Install backend dependencies from `nyaysaathi/backend/requirements.txt`.
2. Start API (`api.main`) on port `8010`.
3. Start frontend from `nyaysaathi/nyaysathi-frontend-main`.
4. Verify API health at `/health`.

## Core APIs

- Auth: `POST /auth/signup`, `POST /auth/login`
- Classify: `POST /api/classify` (and `POST /classify`)
- Admin: `GET /admin/users`, `GET /admin/queries`, `POST|PUT|DELETE /admin/workflows`
- Feedback: `POST /api/feedback`

## Project structure

- AI and API modules at root: `ai_engine`, `api`, `auth`, `admin`, `routes`, `models`, `middleware`, `data`
- Platform workspace: `nyaysaathi/backend`, `nyaysaathi/frontend`, `nyaysaathi/nyaysathi-frontend-main`

## Legal disclaimer

NyaySaathi provides procedural guidance only, not formal legal advice.
For legal advice, consult a qualified advocate.
