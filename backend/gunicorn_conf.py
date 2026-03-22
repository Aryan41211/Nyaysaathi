# Gunicorn tuning for low-memory Render free tier (512MB)
workers = 1
threads = 2
timeout = 120
worker_class = "sync"
max_requests = 200
max_requests_jitter = 20
