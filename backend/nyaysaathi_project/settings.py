"""
NyaySaathi – Django Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DEBUG", "True") == "True"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or ("unsafe-dev-key-change-before-deploy" if DEBUG else "")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app,.onrender.com").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "legal_cases",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "legal_cases.middleware.ApiExceptionMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "legal_cases.middleware.ApiInputValidationMiddleware",
    "legal_cases.middleware.ApiRequestLogMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nyaysaathi_project.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "nyaysaathi_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB  = os.getenv("MONGODB_DB", "nyaysaathi")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

_cors = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors if o.strip()]
CORS_ALLOW_ALL_ORIGINS = DEBUG

_cors_regex = os.getenv("CORS_ALLOWED_ORIGIN_REGEXES", r"https://.*\.vercel\.app").split(",")
CORS_ALLOWED_ORIGIN_REGEXES = [r.strip() for r in _cors_regex if r.strip()]

_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf if o.strip()]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "300/day"),
        "classify": os.getenv("THROTTLE_CLASSIFY_RATE", "20/min"),
    },
    "EXCEPTION_HANDLER": "legal_cases.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NyaySaathi API",
    "DESCRIPTION": "Production API for NyaySaathi legal guidance system",
    "VERSION": "1.0.0",
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

CACHES = {
    "default": {
        "BACKEND": os.getenv("DJANGO_CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": os.getenv("DJANGO_CACHE_LOCATION", "nyaysaathi-local-cache"),
        "TIMEOUT": int(os.getenv("DJANGO_CACHE_TIMEOUT", "300")),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "ai_engine": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "legal": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "legal.monitoring": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "legal_cases": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
    },
}

SEARCH_MODE = os.getenv("SEARCH_MODE", "semantic")
SEARCH_CACHE_DIR = BASE_DIR / "search_cache"
FAISS_INDEX_PATH = SEARCH_CACHE_DIR / "semantic_index.faiss"
EMBEDDINGS_CACHE_PATH = SEARCH_CACHE_DIR / "semantic_embeddings.npy"

# Local semantic understanding layer
UNDERSTANDING_CACHE_TTL_SECONDS = int(os.getenv("UNDERSTANDING_CACHE_TTL_SECONDS", "300"))
HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.75"))
MEDIUM_CONFIDENCE_THRESHOLD = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.55"))
FALLBACK_SIMILARITY_THRESHOLD = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", "0.50"))
AI_MONITOR_SNAPSHOT_EVERY = int(os.getenv("AI_MONITOR_SNAPSHOT_EVERY", "25"))

# Multilingual intelligence layer
SUPPORTED_LANGUAGES = ["en", "hi", "mr"]
TRANSLATION_TIMEOUT = float(os.getenv("TRANSLATION_TIMEOUT", "10"))
TRANSLATION_RETRIES = int(os.getenv("TRANSLATION_RETRIES", "2"))
TRANSLATION_CB_THRESHOLD = int(os.getenv("TRANSLATION_CB_THRESHOLD", "4"))
TRANSLATION_CB_COOLDOWN = float(os.getenv("TRANSLATION_CB_COOLDOWN", "45"))
ROMAN_NORMALIZER_TIMEOUT = float(os.getenv("ROMAN_NORMALIZER_TIMEOUT", "8"))
ROMAN_NORMALIZER_RETRIES = int(os.getenv("ROMAN_NORMALIZER_RETRIES", "1"))

# Auth/JWT runtime settings
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", "24"))
