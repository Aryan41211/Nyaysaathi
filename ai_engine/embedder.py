from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
import re
from difflib import SequenceMatcher

import numpy as np
from sentence_transformers import SentenceTransformer

from models.db import get_feedback_collection

logger = logging.getLogger(__name__)


CANONICAL_CATEGORY_MAP = {
    "land and property disputes": "land_and_property_disputes",
    "labour and wage issues": "labour_and_wage_issues",
    "domestic violence and family disputes": "domestic_violence_and_family_disputes",
    "cyber fraud and digital scams": "cyber_fraud_and_digital_scams",
    "consumer complaints": "consumer_complaints",
    "police complaints and local crime": "police_complaints_and_local_crime",
    "government scheme and public service issues": "government_scheme_and_public_service_issues",
    "tenant–landlord disputes": "tenant_landlord_disputes",
    "tenant-landlord disputes": "tenant_landlord_disputes",
    "environmental and public nuisance complaints": "environmental_and_public_nuisance_complaints",
    "senior citizen protection issues": "senior_citizen_protection_issues",
}


def _normalize_vector(v: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(v, axis=1, keepdims=True)
    denom = np.where(denom == 0, 1.0, denom)
    return v / denom


class SemanticEmbedder:
    def __init__(self, model: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model = model
        self.encoder: SentenceTransformer | None = None
        self.base_dir = Path(__file__).resolve().parents[1]
        self.data_path = self.base_dir / "data" / "legal_categories.json"
        self.embeddings_path = self.base_dir / "data" / "category_embeddings.npy"

        self.entries: list[dict] = self._load_entries()
        self._load_encoder()
        self.embedding_matrix = self._build_or_load_embeddings()

    def _load_encoder(self) -> None:
        try:
            self.encoder = SentenceTransformer(self.model)
        except Exception as exc:
            logger.warning("Sentence-transformer model unavailable locally; using lexical fallback. Error: %s", exc)
            self.encoder = None

    def _load_entries(self) -> list[dict]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        rows: list[dict] = []
        for entry in data:
            category_raw = str(entry.get("category", "")).strip()
            category_id = CANONICAL_CATEGORY_MAP.get(category_raw.lower(), "unknown")
            subcategory = str(entry.get("subcategory", "")).strip()
            problem_description = str(entry.get("problem_description", "")).strip()
            descriptions = entry.get("descriptions") or []
            if isinstance(descriptions, str):
                descriptions = [descriptions]

            for description in descriptions[:10]:
                rows.append(
                    {
                        "category_id": category_id,
                        "category": category_raw,
                        "subcategory": subcategory,
                        "problem_description": problem_description,
                        "description": str(description or problem_description),
                    }
                )
        return rows

    def _embed_text_batch(self, texts: list[str]) -> np.ndarray:
        if self.encoder is None:
            raise RuntimeError("Sentence transformer encoder is unavailable")
        vectors = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        vectors = np.array(vectors, dtype=np.float32)
        return _normalize_vector(vectors)

    def _build_or_load_embeddings(self) -> np.ndarray:
        if self.embeddings_path.exists():
            cached = np.load(self.embeddings_path)
            expected_dim = self.encoder.get_sentence_embedding_dimension() if self.encoder else 384
            if len(cached) == len(self.entries) and cached.ndim == 2 and cached.shape[1] == expected_dim:
                return cached

        if not self.entries:
            return np.zeros((0, 384), dtype=np.float32)

        texts = [row["description"] for row in self.entries]
        try:
            chunks: list[np.ndarray] = []
            step = 128
            for i in range(0, len(texts), step):
                chunks.append(self._embed_text_batch(texts[i : i + step]))
            matrix = np.vstack(chunks).astype(np.float32)
            np.save(self.embeddings_path, matrix)
            return matrix
        except Exception as exc:
            logger.warning("Falling back to lexical mode because embedding precompute failed: %s", exc)
            return np.zeros((0, 384), dtype=np.float32)

    @lru_cache(maxsize=1024)
    def _embed_query_cached(self, query: str) -> np.ndarray:
        vector = self._embed_text_batch([query])[0]
        return vector

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9\u0900-\u097f]+", text.lower()))

    def _lexical_fallback(self, query: str, k: int) -> list[dict]:
        q_tokens = self._tokens(query)
        if not q_tokens:
            return []

        best_by_subcategory: dict[tuple[str, str], float] = {}
        for row in self.entries:
            search_text = " ".join(
                [
                    row.get("description", ""),
                    row.get("subcategory", ""),
                    row.get("category", ""),
                    row.get("problem_description", ""),
                ]
            )
            d_tokens = self._tokens(search_text)
            if not d_tokens or not search_text.strip():
                continue
            intersection = len(q_tokens & d_tokens)
            coverage = intersection / max(1, len(q_tokens))
            jaccard = intersection / max(1, len(q_tokens | d_tokens))
            seq = SequenceMatcher(None, query.lower(), search_text.lower()).ratio()
            score = min(1.0, (0.70 * coverage) + (0.10 * jaccard) + (0.20 * seq))
            key = (row["category_id"], row["subcategory"])
            current = best_by_subcategory.get(key)
            if current is None or score > current:
                best_by_subcategory[key] = score

        ranked = sorted(best_by_subcategory.items(), key=lambda item: item[1], reverse=True)[:k]
        return [
            {
                "category_id": key[0],
                "subcategory": key[1],
                "score": float(score),
            }
            for key, score in ranked
        ]

    def _apply_home_theft_bias(self, query: str, matches: list[dict]) -> list[dict]:
        q = (query or "").lower()
        if not matches:
            return matches

        is_home_theft = (("ghar" in q and ("chori" in q or "theft" in q or "robbery" in q)) or ("house" in q and ("theft" in q or "robbery" in q)))
        if not is_home_theft:
            return matches

        adjusted: list[dict] = []
        for item in matches:
            row = dict(item)
            sub = str(row.get("subcategory", "")).strip().lower()
            score = float(row.get("score", 0.0))

            if sub in {"domestic robbery / house break-in", "theft complaint"}:
                score += 0.15
            if sub == "vehicle theft complaint":
                score -= 0.20

            row["score"] = max(0.0, min(1.0, score))
            adjusted.append(row)

        adjusted.sort(key=lambda m: float(m.get("score", 0.0)), reverse=True)
        return adjusted

    @staticmethod
    def _similarity(a_tokens: set[str], b_tokens: set[str]) -> float:
        if not a_tokens or not b_tokens:
            return 0.0
        return len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))

    def boost_from_feedback(self, query: str, matches: list[dict]) -> list[dict]:
        if not matches:
            return matches

        feedback = get_feedback_collection()
        docs = list(
            feedback.find(
                {
                    "was_helpful": False,
                    "correct_category": {"$exists": True, "$ne": None, "$ne": ""},
                }
            ).sort("created_at", -1).limit(200)
        )

        if not docs:
            return matches

        q_tokens = self._tokens(query)
        adjusted = [dict(item) for item in matches]

        for doc in docs:
            feedback_text = str(doc.get("query_text") or "").strip().lower()
            if not feedback_text:
                continue
            if self._similarity(q_tokens, self._tokens(feedback_text)) < 0.30:
                continue

            correct_category = str(doc.get("correct_category") or "").strip().lower()
            for item in adjusted:
                category_id = str(item.get("category_id") or "").strip().lower()
                subcategory = str(item.get("subcategory") or "").strip().lower()
                if correct_category in {category_id, subcategory}:
                    item["score"] = max(0.0, min(1.0, float(item.get("score", 0.0)) + 0.10))

        adjusted.sort(key=lambda m: float(m.get("score", 0.0)), reverse=True)
        return adjusted

    def top_k_matches(self, query: str, k: int = 3) -> list[dict]:
        try:
            if self.embedding_matrix.size == 0:
                base = self._lexical_fallback(query, k)
                base = self._apply_home_theft_bias(query, base)
                return self.boost_from_feedback(query, base)

            q = self._embed_query_cached(query)
            scores = self.embedding_matrix @ q

            best_by_subcategory: dict[tuple[str, str], float] = {}
            for idx, score in enumerate(scores):
                row = self.entries[idx]
                key = (row["category_id"], row["subcategory"])
                current = best_by_subcategory.get(key)
                if current is None or float(score) > current:
                    best_by_subcategory[key] = float(score)

            ranked = sorted(best_by_subcategory.items(), key=lambda item: item[1], reverse=True)[:k]
            results = [
                {
                    "category_id": key[0],
                    "subcategory": key[1],
                    "score": max(0.0, min(1.0, (score + 1.0) / 2.0)),
                }
                for key, score in ranked
            ]
            results = self._apply_home_theft_bias(query, results)
            return self.boost_from_feedback(query, results)
        except Exception as exc:
            logger.warning("Embedding retrieval failed; using lexical fallback: %s", exc)
            base = self._lexical_fallback(query, k)
            base = self._apply_home_theft_bias(query, base)
            return self.boost_from_feedback(query, base)