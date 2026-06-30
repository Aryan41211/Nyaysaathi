import json
from pathlib import Path

# Get base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔥 IMPORTANT: your dataset file name
DATA_FILE = BASE_DIR / "nyaysaathi_with_descriptions.json"


def load_cases():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("ERROR loading dataset:", e)
        return []


# Load once at startup
CASES = load_cases()