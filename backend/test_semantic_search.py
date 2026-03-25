"""Quick semantic category matching test examples."""

from __future__ import annotations

import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()

from ai_engine.semantic_search import find_best_category  # noqa: E402


TESTS = [
    "My employer not paying salary",
    "mere paise nahi mile",
    "मेरे नियोक्ता ने 2 महीने से वेतन नहीं दिया",
    "mere niyokta ne 2 mahine se vetan nahi diya",
    "online fraud hua",
]


if __name__ == "__main__":
    out = {q: find_best_category(q) for q in TESTS}
    print(json.dumps(out, ensure_ascii=True, indent=2))
