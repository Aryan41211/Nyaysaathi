from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "local_nyaysaathi" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DATA_FILES = [
    (BASE_DIR / "dataset" / "legal_cases.json", "en"),
]

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_CACHE_PATH = CACHE_DIR / "case_embeddings.npz"
