"""Script to precompute and store semantic category embeddings."""

from __future__ import annotations

import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()

from ai_engine.embedding_generator import generate_and_store_embeddings  # noqa: E402


if __name__ == "__main__":
    result = generate_and_store_embeddings()
    print(json.dumps(result, ensure_ascii=True, indent=2))
