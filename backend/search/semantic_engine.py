"""Semantic engine for NyaySaathi.

Provides production-grade semantic retrieval with:
- sentence-transformers embeddings (all-MiniLM-L6-v2)
- FAISS cosine similarity index
- Hybrid ranking (semantic + overlap + title)
- Typo tolerant fallback
- Disk cache and singleton-friendly lifecycle

Designed to be vector-DB ready via a VectorIndex interface.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Protocol, Tuple

import faiss
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer

from .intent_extractor import extract_intent
from .query_processor import process_query
from .ranking import confidence_bucket, hybrid_score, keyword_overlap, select_by_confidence, title_similarity

logger = logging.getLogger(__name__)


class VectorIndex(Protocol):
    """Vector index protocol to support FAISS now and vector DB later."""

    def add(self, vectors: np.ndarray) -> None:
        ...

    def search(self, query_vector: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        ...


class FaissCosineIndex:
    """FAISS inner-product index over normalized vectors == cosine similarity."""

    def __init__(self, dim: int) -> None:
        self.index = faiss.IndexFlatIP(dim)

    def add(self, vectors: np.ndarray) -> None:
        self.index.add(vectors)

    def search(self, query_vector: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        return self.index.search(query_vector, top_k)


@dataclass
class QueryMeta:
    detected_language: str
    normalized_query: str
    search_ready_query: str
    keywords: List[str]
    problem_domain: str
    problem_type: str
    likely_authority: str
    matched_intent: str
    confidence: str
    nlp_source: str = "local_semantic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_language": self.detected_language,
            "normalized_query": self.normalized_query,
            "search_ready_query": self.search_ready_query,
            "keywords": self.keywords,
            "problem_domain": self.problem_domain,
            "problem_type": self.problem_type,
            "likely_authority": self.likely_authority,
            "matched_intent": self.matched_intent,
            "confidence": self.confidence,
            "nlp_source": self.nlp_source,
        }


class SemanticSearchEngine:
    """Singleton-friendly semantic search engine."""

    def __init__(self, cache_dir: Path, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.model_name = model_name
        self.model: SentenceTransformer | None = None

        self._cases: List[Dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._index: VectorIndex | None = None

        self._meta_path = self.cache_dir / "semantic_meta.json"
        self._emb_path = self.cache_dir / "semantic_embeddings.npy"
        self._faiss_path = self.cache_dir / "semantic_index.faiss"

    def load_model(self) -> SentenceTransformer:
        """Load embedding model once per process."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Semantic model loaded: %s", self.model_name)
        return self.model

    def reset(self) -> None:
        """Reset in-memory search state."""
        self._cases = []
        self._embeddings = None
        self._index = None
        self.model = None

    def ensure_index(self, cases: List[Dict[str, Any]]) -> None:
        """Build/load embeddings and FAISS index once for current dataset snapshot."""
        if not cases:
            self.reset()
            return

        fingerprint = self._dataset_fingerprint(cases)
        current_fp = self._dataset_fingerprint(self._cases) if self._cases else None
        if self._index is not None and current_fp == fingerprint:
            return

        self._cases = list(cases)
        self.load_model()

        if self._can_load_cache(fingerprint):
            self._embeddings = np.load(self._emb_path)
            index = FaissCosineIndex(int(self._embeddings.shape[1]))
            index.index = faiss.read_index(str(self._faiss_path))
            self._index = index
            logger.info("Loaded semantic cache with %d vectors", len(self._embeddings))
            return

        self._build_case_embeddings(fingerprint)

    def _build_case_embeddings(self, fingerprint: str) -> None:
        """Create semantic vectors for all cases and build FAISS index."""
        corpus = [self._build_case_text(c) for c in self._cases]
        vectors = self.load_model().encode(
            corpus,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        idx = FaissCosineIndex(vectors.shape[1])
        idx.add(vectors)

        self._embeddings = vectors
        self._index = idx
        self._save_cache(fingerprint)
        logger.info("Built FAISS semantic index for %d cases", len(corpus))

    def embed_query(self, text: str) -> np.ndarray:
        """Encode one query into normalized embedding vector."""
        return self.load_model().encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

    def semantic_search(self, query: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Run end-to-end semantic pipeline and return (results, nlp_meta)."""
        if not query or not query.strip():
            return [], {}
        if self._index is None:
            raise RuntimeError("Semantic index is not initialized")

        q = process_query(query)
        intent = extract_intent(q.expanded)
        query_vector = self.embed_query(q.expanded)

        # Retrieve wider candidate pool, then apply hybrid ranking.
        distances, indices = self._index.search(query_vector, max(20, top_k * 4))

        ranked: List[Dict[str, Any]] = []
        for semantic, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._cases):
                continue

            case = dict(self._cases[idx])
            case_keywords = case.get("keywords") or []
            if isinstance(case_keywords, str):
                case_keywords = [case_keywords]

            overlap = keyword_overlap(q.keywords, [str(k) for k in case_keywords])
            title_sim = title_similarity(q.expanded, str(case.get("subcategory", "")))
            final = hybrid_score(float(semantic), overlap, title_sim)
            conf = confidence_bucket(final)

            matched_keywords = self._matched_keywords(q.keywords, case)
            matched_intent = intent.matched_intent

            case["score"] = round(float(final), 4)
            case["similarity_score"] = round(float(final), 4)
            case["confidence"] = conf
            case["match_type"] = "semantic"
            case["matched_keywords"] = matched_keywords
            case["matched_intent"] = matched_intent
            case["semantic_score"] = round(float(semantic), 4)
            case["keyword_overlap"] = round(float(overlap), 4)
            case["title_similarity"] = round(float(title_sim), 4)
            ranked.append(case)

        # Typo-tolerant fallback if top rank is weak.
        ranked = sorted(ranked, key=lambda d: float(d.get("similarity_score", 0.0)), reverse=True)
        if (not ranked) or float(ranked[0].get("similarity_score", 0.0)) < 0.50:
            ranked = self._merge_fuzzy_fallback(ranked, q.expanded, top_k=max(5, top_k))

        ranked = sorted(ranked, key=lambda d: float(d.get("similarity_score", 0.0)), reverse=True)
        limited = select_by_confidence(ranked)

        top_conf = limited[0]["confidence"] if limited else "Low"
        nlp_meta = QueryMeta(
            detected_language=q.language,
            normalized_query=q.normalized,
            search_ready_query=q.expanded,
            keywords=q.keywords,
            problem_domain=intent.legal_domain,
            problem_type=intent.problem_type,
            likely_authority=intent.authority_type,
            matched_intent=intent.matched_intent,
            confidence=top_conf,
        ).to_dict()

        if top_conf == "Low":
            nlp_meta["clarification_message"] = (
                "Your issue is not fully clear yet. Add details like who, what payment/property/service, and timeline."
            )

        return limited[:top_k], nlp_meta

    def _merge_fuzzy_fallback(self, ranked: List[Dict[str, Any]], query_text: str, top_k: int) -> List[Dict[str, Any]]:
        """Add fuzzy matches as fallback candidates when semantic confidence is weak."""
        seen = {r.get("subcategory", "") for r in ranked}
        for case in self._cases:
            base = " ".join([
                str(case.get("subcategory", "")),
                str(case.get("category", "")),
                " ".join(case.get("keywords", []) or []),
            ])
            fuzzy = fuzz.token_set_ratio(query_text, base.lower()) / 100.0
            if fuzzy < 0.56:
                continue
            sub = case.get("subcategory", "")
            if sub in seen:
                continue

            out = dict(case)
            out["score"] = round(float(fuzzy), 4)
            out["similarity_score"] = round(float(fuzzy), 4)
            out["confidence"] = confidence_bucket(float(fuzzy))
            out["match_type"] = "fuzzy"
            out["matched_keywords"] = []
            out["matched_intent"] = "General legal issue"
            ranked.append(out)
            seen.add(sub)

            if len(ranked) >= top_k * 2:
                break

        return ranked

    def _build_case_text(self, case: Dict[str, Any]) -> str:
        """Combine case fields into one embedding text representation."""
        # Keep "title" optional for backward compatibility with dataset variants.
        title = case.get("title") or case.get("subcategory") or ""
        keywords = case.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        descriptions = case.get("descriptions") or []
        if isinstance(descriptions, str):
            descriptions = [descriptions]

        parts = [
            str(case.get("category", "")),
            str(title),
            str(case.get("problem_description", "")),
            " ".join(str(d) for d in descriptions if d),
            " ".join(str(k) for k in keywords if k),
        ]
        return " ".join(parts).strip().lower()

    def _matched_keywords(self, query_keywords: List[str], case: Dict[str, Any]) -> List[str]:
        case_keywords = case.get("keywords") or []
        if isinstance(case_keywords, str):
            case_keywords = [case_keywords]

        q = {k.lower() for k in query_keywords}
        matched = []
        for ck in [str(k).lower() for k in case_keywords]:
            if ck in q:
                matched.append(ck)
                continue
            if any(fuzz.ratio(ck, qq) >= 86 for qq in q):
                matched.append(ck)
        return matched[:8]

    def _dataset_fingerprint(self, cases: Iterable[Dict[str, Any]]) -> str:
        hasher = hashlib.sha256()
        for case in sorted(cases, key=lambda c: str(c.get("subcategory", ""))):
            payload = {
                "category": case.get("category", ""),
                "subcategory": case.get("subcategory", ""),
                "title": case.get("title", ""),
                "problem_description": case.get("problem_description", ""),
                "descriptions": case.get("descriptions", []),
                "keywords": case.get("keywords", []),
            }
            hasher.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        hasher.update(self.model_name.encode("utf-8"))
        return hasher.hexdigest()

    def _can_load_cache(self, fingerprint: str) -> bool:
        if not (self._meta_path.exists() and self._emb_path.exists() and self._faiss_path.exists()):
            return False
        try:
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            return (
                meta.get("fingerprint") == fingerprint
                and meta.get("model_name") == self.model_name
                and int(meta.get("count", -1)) == len(self._cases)
            )
        except Exception:
            return False

    def _save_cache(self, fingerprint: str) -> None:
        if self._embeddings is None:
            return
        np.save(self._emb_path, self._embeddings)
        if isinstance(self._index, FaissCosineIndex):
            faiss.write_index(self._index.index, str(self._faiss_path))
        self._meta_path.write_text(
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "model_name": self.model_name,
                    "count": len(self._cases),
                    "vector_dim": int(self._embeddings.shape[1]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
