# Deployment Guide

## Render Backend

- Root directory: backend
- Build command:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
```

- Start command:

```bash
gunicorn nyaysaathi_project.wsgi:application --bind 0.0.0.0:$PORT
```

- Required env vars: see backend/.env.example
- Recommended settings module:

```bash
DJANGO_SETTINGS_MODULE=nyaysaathi_project.settings_production
```

## Vercel Frontend

- Build root: frontend
- Environment variables:
  - VITE_API_URL=https://<render-service>.onrender.com
  - VITE_FALLBACK_API_URL=https://<render-service>.onrender.com/api

## Validation Checklist

- /api/health returns status ok.
- CORS includes the deployed Vercel domain.
- ALLOWED_HOSTS contains .onrender.com and .vercel.app.
- Frontend search successfully reaches backend in production.
