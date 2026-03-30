from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Dict, List

import numpy as np

from .faiss_index import FaissCaseIndex

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_FILES = [
    (BASE_DIR / "dataset" / "legal_cases.json", "en"),
    (BASE_DIR / "nyaysaathi_with_descriptions.json", "en"),
    (BASE_DIR / "nyaysaathi_hindi.json", "hi"),
    (BASE_DIR / "nyaysaathi_marathi.json", "mr"),
]
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """Loads multilingual legal cases and provides semantic retrieval."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cases: List[Dict] = []
        self._embeddings = None
        self._model = None
        self._index = None
        self._ready = False
        self._model_error = None

    @property
    def model_error(self):
        return self._model_error

    def _load_json(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _normalize_case(self, case: Dict, language: str, source: str, idx: int) -> Dict:
        category = case.get("category", "Unknown")
        subcategory = case.get("subcategory", "General Legal Issue")
        problem_description = case.get("problem_description", "")
        descriptions = case.get("descriptions", [])

        if not isinstance(descriptions, list):
            descriptions = []

        authorities = case.get("authorities", [])
        if not isinstance(authorities, list):
            authorities = []

        searchable_chunks = [
            str(category),
            str(subcategory),
            str(problem_description),
            " ".join(str(x) for x in descriptions),
            " ".join(str(x) for x in case.get("workflow_steps", [])),
        ]

        searchable_text = " ".join(chunk for chunk in searchable_chunks if chunk).strip()

        return {
            "id": f"{source}:{idx}",
            "language": language,
            "source": source,
            "category": category,
            "subcategory": subcategory,
            "problem_description": problem_description,
            "workflow_steps": case.get("workflow_steps", []),
            "required_documents": case.get("required_documents", []),
            "authorities": authorities,
            "escalation_path": case.get("escalation_path", []),
            "online_portals": case.get("online_portals", []),
            "helplines": case.get("helplines", []),
            "descriptions": descriptions,
            "searchable_text": searchable_text,
            "raw": case,
        }

    def _load_cases(self) -> List[Dict]:
        merged = []
        seen = set()

        for path, language in DATA_FILES:
            source = path.name
            records = self._load_json(path)
            for i, case in enumerate(records):
                item = self._normalize_case(case, language, source, i)
                dedupe_key = (
                    item["category"].strip().lower(),
                    item["subcategory"].strip().lower(),
                    item["problem_description"].strip().lower(),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                merged.append(item)

        return merged

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(MODEL_NAME)
            return self._model
        except Exception as exc:
            self._model_error = str(exc)
            return None

    def _build_embeddings(self, model, cases: List[Dict]):
        corpus = [c["searchable_text"] for c in cases]
        vectors = model.encode(corpus, convert_to_numpy=True, normalize_embeddings=True)
        return np.asarray(vectors, dtype="float32")

    def ensure_ready(self) -> None:
        if self._ready:
            return

        with self._lock:
            if self._ready:
                return

            cases = self._load_cases()
            logger.info("semantic_engine: loaded_cases=%s", len(cases))
            model = self._get_model()

            if not cases or model is None:
                self._cases = cases
                self._embeddings = None
                self._index = None
                self._ready = True
                if model is None:
                    logger.warning("semantic_engine: model unavailable, using lexical fallback")
                return

            embeddings = self._build_embeddings(model, cases)
            index = FaissCaseIndex(embeddings.shape[1])
            index.build(embeddings)

            self._cases = cases
            self._embeddings = embeddings
            self._index = index
            self._ready = True
            logger.info("semantic_engine: embeddings_ready count=%s dim=%s", len(cases), embeddings.shape[1])

    def keyword_search(self, query_terms: List[str], top_k: int = 5) -> List[Dict]:
        self.ensure_ready()
        if not self._cases:
            return []

        terms = [term.lower().strip() for term in query_terms if term.strip()]
        if not terms:
            return []

        scored = []
        for case in self._cases:
            text = case.get("searchable_text", "").lower()
            overlap = sum(1 for term in terms if term in text)
            if overlap <= 0:
                continue
            score = min(1.0, overlap / max(1, len(terms)))
            scored.append({"case": case, "semantic_score": float(score)})

        scored.sort(key=lambda x: x["semantic_score"], reverse=True)
        return scored[:top_k]

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        self.ensure_ready()

        if not query.strip():
            return []

        if not self._cases:
            return []

        model = self._get_model()
        if model is None or self._index is None:
            # Embedding model unavailable. Graceful lexical fallback.
            q = query.lower().strip()
            scored = []
            for case in self._cases:
                text = case["searchable_text"].lower()
                score = 1.0 if q in text else 0.0
                if score == 0.0:
                    overlap = sum(1 for token in q.split() if token in text)
                    score = min(0.9, overlap / max(1, len(q.split())))
                scored.append({"case": case, "semantic_score": float(score)})
            scored.sort(key=lambda x: x["semantic_score"], reverse=True)
            top = scored[:top_k]
            logger.info("semantic_engine: lexical_fallback_matches=%s query='%s'", len(top), query)
            return top

        query_vec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        result = self._index.search(np.asarray(query_vec, dtype="float32")[0], top_k=top_k)

        hits = []
        for idx, score in zip(result.indices.tolist(), result.scores.tolist()):
            if 0 <= idx < len(self._cases):
                hits.append({
                    "case": self._cases[idx],
                    "semantic_score": float(max(0.0, min(1.0, score))),
                })
        logger.info("semantic_engine: semantic_matches=%s query='%s'", len(hits), query)
        return hits


_ENGINE = SemanticSearchEngine()


def get_semantic_engine() -> SemanticSearchEngine:
    return _ENGINE
