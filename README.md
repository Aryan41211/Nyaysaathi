# NyaySaathi

NyaySaathi is a multilingual AI legal guidance platform that converts user legal problems into procedural next steps, required documents, escalation paths, and authority guidance.

## Project Overview

- **Backend**: Django REST API with modular AI pipeline and MongoDB-backed legal workflow retrieval.
- **Frontend**: React + Vite app deployed on Vercel.
- **AI**: Language detection, normalization, intent routing, semantic embeddings, reranking, and response generation.
- **Deployment**: Render for backend, Vercel for frontend.

## Repository Structure

```text
NyaySaathi/
|-- backend/
|   |-- manage.py
|   |-- requirements.txt
|   |-- requirements.lock.txt
|   |-- runtime.txt
|   |-- .env.example
|   |-- .env
|   |-- nyayasaathi/
|   |-- legal_cases/
|   |-- ai_engine/
|   |-- auth/
|   |-- api/
|   |-- middleware/
|   |-- models/
|   |-- services/
|   |-- utils/
|   |-- search/
|   `-- data/
|-- frontend/
|   |-- src/
|   |-- package.json
|   |-- vite.config.js
|   |-- .env.example
|   |-- .env
|-- dataset/
|-- docs/
|   |-- architecture.md
|   |-- api.md
|   `-- deployment.md
|-- scripts/
|   |-- import_dataset.py
|   `-- generate_embeddings.py
|-- render.yaml
`-- vercel.json
```

## Prerequisites

- **Python** 3.10+ (3.12 recommended)
- **Node.js** 18+ and npm
- **Git**
- **MongoDB** (optional for local development; the app falls back to local dataset without it)

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/NyaySaathi.git
cd NyaySaathi
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

The backend will start at `http://localhost:8000`.

### 3. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

The frontend will start at `http://localhost:5173` (or `http://localhost:3000` depending on your Vite config).

## Environment Variables

### Backend (`backend/.env`)

See `backend/.env.example` for all available variables. Minimum required for local development:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `dev-secret-key-change-in-production` |
| `DEBUG` | Enable debug mode | `True` |
| `DJANGO_ENV` | Environment name | `development` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1,0.0.0.0` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://localhost:5173` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins | `http://localhost:3000,http://localhost:5173` |
| `DATABASE_URL` | Database URL | `sqlite:///db.sqlite3` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB` | MongoDB database name | `nyaysaathi_dev` |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `MODEL_MODE` | AI model mode | `hybrid` |
| `EMAIL_BACKEND` | Email backend | `django.core.mail.backends.console.EmailBackend` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `True` |
| `LOG_LEVEL` | Logging level | `DEBUG` |
| `FRONTEND_URL` | Frontend URL for CORS | `http://localhost:5173` |

### Frontend (`frontend/.env`)

See `frontend/.env.example` for all available variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
| `VITE_FALLBACK_API_URL` | Fallback backend API URL | `http://localhost:8000/api` |

**Note**: In local development, Vite proxies `/api` requests to `http://localhost:8000`, so the frontend will work even if these variables point to production URLs.

## API Routes

- `GET /api/health` -> `{ "status": "ok" }`
- `GET /api/categories/`
- `GET /api/cases/`
- `GET|POST /api/search/`
- `POST /api/classify`
- `GET /api/case/<subcategory>/`
- `GET /api/health/ai/`
- `POST /api/auth/signup`
- `POST /api/auth/login`

## Run Commands

### Backend

```bash
cd backend
python manage.py check        # Verify Django configuration
python manage.py migrate       # Apply database migrations
python manage.py runserver     # Start development server
python manage.py test          # Run tests
```

### Frontend

```bash
cd frontend
npm install                    # Install dependencies
npm run dev                    # Start development server
npm run build                  # Build for production
npm run preview                # Preview production build
```

## Troubleshooting

### Backend

- **`DJANGO_SECRET_KEY` error**: Ensure `.env` exists in the `backend/` directory with a valid `DJANGO_SECRET_KEY`.
- **Database errors**: Delete `db.sqlite3` and run `python manage.py migrate` again.
- **MongoDB connection errors**: MongoDB is optional for local development. The app will use the local JSON dataset.
- **SentenceTransformer model download**: On first run, the app downloads `all-MiniLM-L6-v2` from HuggingFace. This requires internet access and may take a minute.
- **Port 8000 already in use**: Run `python manage.py runserver 8001` to use a different port.

### Frontend

- **`npm install` fails**: Ensure Node.js 18+ is installed. Try `npm install --force`.
- **API requests fail in dev**: Ensure the backend is running on `http://localhost:8000`. Check `frontend/.env` for correct `VITE_API_URL`.
- **Vite proxy not working**: The Vite dev server proxies `/api` to `http://localhost:8000`. Ensure `vite.config.js` has the correct proxy settings.

## Dataset

The legal cases dataset is stored in `backend/dataset/legal_cases.json` (201 cases across 10 categories). The dataset is loaded at startup and indexed for semantic search.

## Deployment

### Render (Backend)

- Root directory: `backend`
- Build command:
  ```bash
  pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
  ```
- Start command:
  ```bash
  gunicorn nyaysaathi.wsgi:application --bind 0.0.0.0:$PORT
  ```

### Vercel (Frontend)

- Uses root `vercel.json` with build output `frontend/dist`.
- Ensure `VITE_API_URL` points to the Render backend host.

## Operational Notes

- Structured logging and request middleware are enabled in Django settings.
- Throttling and rate-limit preparation are active for anonymous and classify paths.
- Mongo client uses retry/backoff and bounded pool settings for deployment resilience.

## Legal Disclaimer

NyaySaathi provides procedural guidance and does not replace formal legal advice.
