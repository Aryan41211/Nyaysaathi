# ⚖️ NyaySaathi – AI-Based Legal Procedural Guidance System

> **Empowering ordinary Indian citizens with free, accessible legal procedural knowledge.**  
> Describe your problem → Get step-by-step guidance, required documents, and helpline numbers.

---

## ⚠️ Legal Disclaimer

NyaySaathi provides **procedural guidance only** and does **NOT** constitute legal advice.  
For legal advice, consult a qualified advocate.  
**Free legal aid:** Call **15100** (DLSA – District Legal Services Authority)

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Quick Start (Local)](#quick-start-local)
5. [Dataset Import](#dataset-import)
6. [API Reference](#api-reference)
7. [Deployment Guide](#deployment-guide)
8. [Environment Variables](#environment-variables)
9. [Future Improvements](#future-improvements)

---

## Project Overview

NyaySaathi is a full-stack MVP that helps citizens navigate the Indian legal system procedurally.

**What it does:**
- User types a legal problem in plain language
- AI search (TF-IDF keyword or semantic embeddings) matches it to the correct legal workflow
- Returns: step-by-step procedure, required documents, authorities to approach, escalation path, complaint template, online portals, and helpline numbers

**Coverage (201 workflows across 10 categories):**

| Category | Workflows |
|----------|-----------|
| Land and Property Disputes | 27 |
| Labour and Wage Issues | 23 |
| Cyber Fraud and Digital Scams | 21 |
| Consumer Complaints | 21 |
| Environmental and Public Nuisance | 19 |
| Senior Citizen Protection Issues | 19 |
| Government Scheme Issues | 20 |
| Police Complaints and Local Crime | 20 |
| Domestic Violence and Family | 15 |
| Tenant–Landlord Disputes | 16 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Django 4.2 + Django REST Framework |
| Database | MongoDB Atlas (via PyMongo) |
| AI Search | TF-IDF (scikit-learn) / Sentence Transformers (optional) |
| Frontend | React 18 + Vite + React Router |
| Deployment – Backend | Render |
| Deployment – Database | MongoDB Atlas (free tier) |
| Deployment – Frontend | Vercel |

---

## Project Structure

```
nyaysaathi/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── import_dataset.py              # Standalone import script
│   ├── nyaysaathi_project/
│   │   ├── __init__.py
│   │   ├── settings.py                # All config, env vars
│   │   ├── urls.py                    # Root URL routing
│   │   └── wsgi.py
│   └── legal_cases/
│       ├── __init__.py
│       ├── apps.py
│       ├── db_connection.py           # MongoDB singleton
│       ├── services.py                # Search + data retrieval logic
│       ├── views.py                   # API views
│       ├── urls.py                    # API URL patterns
│       ├── migrations/
│       └── management/commands/
│           └── import_dataset.py      # Django management command
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css                  # Design system + CSS variables
│       ├── components/
│       │   ├── Navbar.jsx
│       │   ├── Footer.jsx
│       │   ├── SearchBox.jsx
│       │   ├── CaseCard.jsx
│       │   └── Feedback.jsx           # LoadingSpinner, ErrorMessage, EmptyState
│       ├── pages/
│       │   ├── HomePage.jsx
│       │   ├── SearchPage.jsx
│       │   ├── ResultsPage.jsx
│       │   ├── CategoriesPage.jsx
│       │   └── CaseDetailPage.jsx
│       └── services/
│           └── api.js                 # Axios API client
│
└── dataset/
    └── legal_cases.json               # 201 legal workflows
```

---

## Quick Start (Local)

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running locally OR a MongoDB Atlas account

---

### 1. Clone & setup

```bash
git clone https://github.com/your-username/nyaysaathi.git
cd nyaysaathi
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env – set MONGODB_URI and DJANGO_SECRET_KEY

# Run migrations (SQLite – Django internals only)
python manage.py migrate

# Start backend
python manage.py runserver
# API available at: http://localhost:8000/api/
```

### 3. Import the dataset

```bash
# From inside backend/ with venv active:
python manage.py import_dataset

# Or with options:
python manage.py import_dataset --file ../dataset/legal_cases.json
python manage.py import_dataset --wipe   # drop and re-import
```

### 4. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional in dev – Vite proxies /api → localhost:8000)
cp .env.example .env

# Start dev server
npm run dev
# Frontend at: http://localhost:3000
```

---

## Dataset Import

The import script uses **upsert** logic — it inserts new records and updates existing ones based on `subcategory`. Running it multiple times is safe (no duplicates).

```bash
# Django management command (recommended)
python manage.py import_dataset

# Or standalone script
python import_dataset.py
python import_dataset.py --file /path/to/file.json --wipe
```

**MongoDB collection:** `nyaysaathi.legal_cases`  
**Unique index on:** `subcategory`

---

## API Reference

Base URL: `http://localhost:8000/api/` (local) | `https://your-app.onrender.com/api/` (production)

---

### GET `/api/categories/`

Returns all categories with subcategory counts.

**Response:**
```json
{
  "success": true,
  "disclaimer": "...",
  "total": 10,
  "data": [
    {
      "category": "Cyber Fraud and Digital Scams",
      "subcategory_count": 21,
      "subcategories": ["UPI / Online Payment Fraud", "OTP Scam / Vishing", "..."]
    }
  ]
}
```

---

### GET `/api/cases/`

Returns summary of all cases (or filtered by category).

**Query params:** `?category=Labour+and+Wage+Issues`

---

### GET `/api/search/?query=text`

Natural language search. Returns top-5 matching cases with full details.

**Example:**
```
GET /api/search/?query=my employer has not paid my salary for 3 months
```

**Response:**
```json
{
  "success": true,
  "query": "my employer has not paid my salary for 3 months",
  "total": 5,
  "message": "Here is the procedural guidance for your problem.",
  "data": [
    {
      "category": "Labour and Wage Issues",
      "subcategory": "Salary Not Paid by Employer",
      "problem_description": "...",
      "workflow_steps": ["Step 1 – ...", "Step 2 – ..."],
      "required_documents": ["Appointment letter", "Salary slips", "..."],
      "authorities": [{"name": "Labour Inspector", "level": "District"}],
      "escalation_path": ["Labour Inspector → Regional Labour Commissioner → Labour Court"],
      "complaint_template": "To,\nThe Labour Inspector...",
      "online_portals": ["https://shramsuvidha.gov.in"],
      "helplines": ["National Labour Helpline: 1800-11-2142"],
      "score": 0.6821,
      "match_type": "keyword"
    }
  ]
}
```

---

### GET `/api/case/<subcategory>/`

Returns full details for one specific subcategory.

**Example:**
```
GET /api/case/Salary%20Not%20Paid%20by%20Employer/
GET /api/case/UPI-Online-Payment-Fraud/
```

---

### GET `/health/`

Health check endpoint.

```json
{ "status": "ok", "service": "NyaySaathi API", "version": "1.0.0" }
```

---

## Deployment Guide

### Step 1: MongoDB Atlas (Database)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → Create free account
2. Create a **Free Tier (M0)** cluster
3. Create a database user (Settings → Database Access)
4. Whitelist all IPs: `0.0.0.0/0` (Network Access)
5. Get connection string: `mongodb+srv://<user>:<pass>@cluster0.xxxxx.mongodb.net/`
6. Create database: `nyaysaathi`, collection: `legal_cases`

---

### Step 2: Backend on Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate`
   - **Start Command:** `gunicorn nyaysaathi_project.wsgi:application`
  - **Root Directory:** `nyaysaathi/backend`
5. Add Environment Variables (see section below)
6. Deploy → note your Render URL (e.g. `https://nyaysaathi-backend.onrender.com`)
7. After deploy, import dataset via Render Shell:
   ```bash
   python manage.py import_dataset
   ```

---

### Step 3: Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. **Root Directory:** `nyaysaathi/frontend`
3. **Build Command:** `npm run build`
4. **Output Directory:** `dist`
5. Add Environment Variable:
   ```
   VITE_API_URL = https://nyaysaathi-backend.onrender.com/api
   ```
6. Deploy → note your Vercel URL

---

### Step 4: Connect frontend ↔ backend

On Render, add to Environment Variables:
```
CORS_ALLOWED_ORIGINS = https://your-app.vercel.app
```

Redeploy backend. Done! ✅

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | ✅ | Long random secret key |
| `DEBUG` | ✅ | `True` (dev) / `False` (prod) |
| `ALLOWED_HOSTS` | ✅ | Comma-separated hostnames |
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string |
| `MONGODB_DB` | ✅ | Database name (default: `nyaysaathi`) |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated allowed frontend origins |
| `SEARCH_MODE` | ❌ | `keyword` (default) or `semantic` |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Production | Backend API URL |

---

## Enabling Semantic Search (Optional)

For better search quality, enable sentence-transformer embeddings:

1. Uncomment in `requirements.txt`:
   ```
   sentence-transformers==2.7.0
   ```
2. Set in `.env`:
   ```
   SEARCH_MODE=semantic
   ```
3. Restart. Embeddings are computed on first search and cached to disk.

⚠️ Requires ~1GB RAM and ~500MB disk. Not recommended on Render free tier.

---

## Future Improvements

| Feature | Priority | Notes |
|---------|----------|-------|
| Hindi / multilingual UI | High | Critical for rural users |
| Voice input | High | Accessibility for non-literate users |
| SMS/WhatsApp bot | High | Reach users without smartphones |
| Semantic search upgrade | Medium | Better accuracy |
| User feedback on results | Medium | Improve search quality |
| PDF complaint generator | Medium | Auto-fill templates |
| Lawyer directory | Low | Connect to DLSA advocate list |
| Offline PWA | Low | Rural low-connectivity areas |
| Admin dashboard | Low | Add/edit cases without code |

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit and push
4. Open a Pull Request

---

## License

MIT License. Free to use, modify, and distribute.

---

*Built with ❤️ for the people of India.*  
*NyaySaathi – न्यायसाथी – Your Companion in Justice*
