"""Semantic engine for NyaySaathi with explicit intent classification.

Pipeline order:
query processing -> intent classification -> semantic retrieval -> dynamic confidence layer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Protocol, Tuple

import faiss
import numpy as np
from rapidfuzz import fuzz
from utils.ai_runtime import load_sentence_transformer

from .query_processor import process_query
from .ranking import hybrid_score, keyword_overlap, select_by_confidence, title_similarity

logger = logging.getLogger(__name__)


class VectorIndex(Protocol):
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


class FaissHNSWIndex:
    """Approximate FAISS HNSW index with cosine distance via inner-product graph."""

    def __init__(self, dim: int, m: int = 32, ef_search: int = 96) -> None:
        self.index = faiss.IndexHNSWFlat(dim, m, faiss.METRIC_INNER_PRODUCT)
        self.index.hnsw.efSearch = ef_search

    def add(self, vectors: np.ndarray) -> None:
        self.index.add(vectors)

    def search(self, query_vector: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        return self.index.search(query_vector, top_k)


@dataclass
class IntentDefinition:
    label: str
    legal_domain: str
    problem_type: str
    authority_type: str
    examples: List[str]
    clarification_questions: List[str]
    intent_keywords: List[str]


@dataclass
class IntentMatch:
    matched_intent: str
    legal_domain: str
    problem_type: str
    authority_type: str
    confidence_score: float
    confidence: str
    ambiguous: bool
    query_for_retrieval: str
    clarification_questions: List[str]
    reasoning_signals: Dict[str, float]
    intent_keywords: List[str]


class IntentClassifier:
    """Embedding-based intent layer that runs before semantic retrieval."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = None
        self._definitions = self._build_intent_definitions()
        self._embeddings: np.ndarray | None = None

    def load_model(self):
        if self.model is None:
            self.model = load_sentence_transformer(self.model_name)
        return self.model

    def reset(self) -> None:
        self.model = None
        self._embeddings = None

    def classify(self, query_text: str, query_tokens: List[str], query_keywords: List[str]) -> IntentMatch:
        self._ensure_embeddings()
        query_vector = self.load_model().encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        scores = np.dot(self._embeddings, query_vector[0])
        ranking = np.argsort(scores)[::-1]
        top_idx = int(ranking[0])
        second_idx = int(ranking[1]) if len(ranking) > 1 else top_idx
        top_score = float(scores[top_idx])
        second_score = float(scores[second_idx])
        margin = max(0.0, top_score - second_score)

        best = self._definitions[top_idx]
        coverage = self._keyword_coverage(best.intent_keywords, query_tokens + query_keywords)

        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        adaptive_margin = max(0.04, std_score * 0.60)
        intent_score = max(0.0, min(1.0, (0.58 * top_score) + (0.22 * margin) + (0.20 * coverage)))

        high_threshold = max(0.58, mean_score + (0.95 * std_score))
        medium_threshold = max(0.44, mean_score + (0.35 * std_score))

        confidence = "High" if intent_score >= high_threshold else ("Medium" if intent_score >= medium_threshold else "Low")
        ambiguous = margin < adaptive_margin

        if ambiguous and confidence == "High":
            confidence = "Medium"
        if ambiguous and confidence == "Medium" and coverage < 0.35:
            confidence = "Low"

        enriched_query = " ".join([query_text, best.label, best.problem_type]).strip()
        return IntentMatch(
            matched_intent=best.label,
            legal_domain=best.legal_domain,
            problem_type=best.problem_type,
            authority_type=best.authority_type,
            confidence_score=round(intent_score, 4),
            confidence=confidence,
            ambiguous=ambiguous,
            query_for_retrieval=enriched_query,
            clarification_questions=best.clarification_questions,
            reasoning_signals={
                "top_intent_similarity": round(top_score, 4),
                "intent_margin": round(margin, 4),
                "intent_keyword_coverage": round(coverage, 4),
                "intent_mean_similarity": round(mean_score, 4),
                "intent_std_similarity": round(std_score, 4),
            },
            intent_keywords=best.intent_keywords,
        )

    def _ensure_embeddings(self) -> None:
        if self._embeddings is not None:
            return
        model = self.load_model()
        rep_texts = [" ".join(d.examples + d.intent_keywords + [d.label, d.problem_type]) for d in self._definitions]
        self._embeddings = model.encode(
            rep_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

    def _keyword_coverage(self, intent_keywords: List[str], query_terms: List[str]) -> float:
        query_norm = {str(term).lower() for term in query_terms if term}
        if not query_norm:
            return 0.0
        matched = 0
        for keyword in intent_keywords:
            key = str(keyword).lower()
            if key in query_norm:
                matched += 1
                continue
            if any(fuzz.ratio(key, q) >= 88 for q in query_norm):
                matched += 1
        return min(1.0, matched / max(1, len(intent_keywords)))

    def _build_intent_definitions(self) -> List[IntentDefinition]:
        return [
            IntentDefinition(
                label="Salary Non-Payment",
                legal_domain="Labour and Wage Issues",
                problem_type="Salary/Wage Dispute",
                authority_type="Labour Department",
                examples=[
                    "salary not paid by employer",
                    "mera salary nahi mila",
                    "वेतन नहीं मिला",
                    "pagar milala nahi",
                    "company not paying wages",
                ],
                clarification_questions=[
                    "Is this salary delay, partial payment, or complete non-payment?",
                    "Are you private employee, contract worker, or daily wage worker?",
                    "How many months are pending and do you have salary proof?",
                ],
                intent_keywords=["salary", "wage", "employer", "labour", "not", "paid"],
            ),
            IntentDefinition(
                label="Police FIR Refusal",
                legal_domain="Police Complaints and Local Crime",
                problem_type="Police Inaction",
                authority_type="Police",
                examples=[
                    "police complaint kaise kare",
                    "police fir nahi le rahe",
                    "पोलीस तक्रार घेत नाहीत",
                    "एफआईआर दर्ज नहीं हो रही",
                    "complaint not registered in police station",
                ],
                clarification_questions=[
                    "Is the issue FIR refusal, delayed action, or harassment?",
                    "Which police station did you approach and on what date?",
                    "Do you have complaint copy or acknowledgment?",
                ],
                intent_keywords=["police", "complaint", "fir", "station", "refusal"],
            ),
            IntentDefinition(
                label="UPI / Cyber Fraud",
                legal_domain="Cyber Fraud and Digital Scams",
                problem_type="Digital Fraud",
                authority_type="Cyber Cell / Bank",
                examples=[
                    "upi fraud paisa gaya",
                    "online scam money lost",
                    "फोनपे फ्रॉड",
                    "cyber fraud complaint",
                    "otp scam bank transaction",
                ],
                clarification_questions=[
                    "Was it UPI fraud, card fraud, or OTP/social-media scam?",
                    "When did the transaction happen and what amount was involved?",
                    "Do you have transaction ID and screenshots?",
                ],
                intent_keywords=["upi", "fraud", "cyber", "bank", "transaction"],
            ),
            IntentDefinition(
                label="Tenant-Landlord Deposit Dispute",
                legal_domain="Tenant-Landlord Disputes",
                problem_type="Security Deposit Dispute",
                authority_type="Rent Authority / Civil Court",
                examples=[
                    "landlord not returning deposit",
                    "घरमालक डिपॉझिट परत देत नाही",
                    "security amount nahi de raha",
                    "rent agreement deposit dispute",
                ],
                clarification_questions=[
                    "Is this about rent, eviction, or security deposit refund?",
                    "Do you have rent agreement and payment receipts?",
                    "How long has the dispute been pending?",
                ],
                intent_keywords=["landlord", "tenant", "rent", "deposit", "return"],
            ),
            IntentDefinition(
                label="Property and Land Dispute",
                legal_domain="Land and Property Disputes",
                problem_type="Property Ownership/Boundary Dispute",
                authority_type="Revenue Office / Civil Court",
                examples=[
                    "zameen boundary dispute",
                    "property kabza issue",
                    "जमीन विवाद",
                    "land record mutation problem",
                ],
                clarification_questions=[
                    "Is this ownership dispute, boundary encroachment, or registry issue?",
                    "Which documents do you already have (sale deed, 7/12, mutation)?",
                    "Who is the opposite party in this dispute?",
                ],
                intent_keywords=["land", "property", "registry", "encroachment", "ownership"],
            ),
            IntentDefinition(
                label="Domestic Violence / Family Safety",
                legal_domain="Domestic Violence and Family Disputes",
                problem_type="Domestic Violence Protection",
                authority_type="Protection Officer / Court",
                examples=[
                    "husband beating and harassment",
                    "ghar me jhagda hua kya kare",
                    "ghar ka jhagda legal help",
                    "family fight legal complaint",
                    "घरगुती हिंसा तक्रार",
                    "domestic violence help",
                    "wife harassment legal protection",
                ],
                clarification_questions=[
                    "Is there immediate physical threat right now?",
                    "Is the issue physical violence, verbal abuse, or financial abuse?",
                    "Do you need protection order, shelter, or police complaint support?",
                ],
                intent_keywords=["violence", "husband", "wife", "harassment", "family", "jhagda", "home"],
            ),
            IntentDefinition(
                label="Consumer Complaint",
                legal_domain="Consumer Complaints",
                problem_type="Defective Product/Service Dispute",
                authority_type="Consumer Forum",
                examples=[
                    "defective product refund not given",
                    "consumer complaint ka process kya hai",
                    "consumer complaint against seller",
                    "रिफंड नहीं मिला",
                    "service warranty issue",
                ],
                clarification_questions=[
                    "Is this product defect, service deficiency, or refund delay?",
                    "What is purchase date and invoice amount?",
                    "Did the seller reject replacement or refund in writing?",
                ],
                intent_keywords=["consumer", "complaint", "process", "refund", "warranty", "defect", "seller", "forum"],
            ),
            IntentDefinition(
                label="Government Scheme / Service Delay",
                legal_domain="Government Scheme and Public Service Issues",
                problem_type="Public Service Delay",
                authority_type="Department Grievance Cell",
                examples=[
                    "pension nahi mil rahi",
                    "scheme benefit delay",
                    "सरकारी योजना लाभ नहीं मिला",
                    "public service complaint",
                ],
                clarification_questions=[
                    "Which scheme or public service is delayed?",
                    "What application number or document reference do you have?",
                    "How long has the delay been pending?",
                ],
                intent_keywords=["scheme", "government", "pension", "benefit", "service"],
            ),
        ]


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
    intent_confidence_score: float = 0.0
    overall_confidence_score: float = 0.0
    ambiguity_score: float = 1.0
    clarification_required: bool = False
    clarification_message: str = ""
    clarification_questions: List[str] | None = None
    reasoning_signals: Dict[str, float] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_language": self.detected_language,
            "normalized_query": self.normalized_query,
            "search_ready_query": self.search_ready_query,
            "understood_as": self.search_ready_query,
            "keywords": self.keywords,
            "problem_domain": self.problem_domain,
            "problem_type": self.problem_type,
            "likely_authority": self.likely_authority,
            "matched_intent": self.matched_intent,
            "confidence": self.confidence,
            "nlp_source": self.nlp_source,
            "intent_confidence_score": round(float(self.intent_confidence_score), 4),
            "overall_confidence_score": round(float(self.overall_confidence_score), 4),
            "ambiguity_score": round(float(self.ambiguity_score), 4),
            "clarification_required": bool(self.clarification_required),
            "clarification_message": self.clarification_message,
            "clarification_questions": list(self.clarification_questions or []),
            "reasoning_signals": dict(self.reasoning_signals or {}),
        }


@dataclass
class RetrievalCandidate:
    case: Dict[str, Any]
    semantic_score: float
    keyword_overlap: float
    title_similarity: float
    intent_alignment: float
    final_score: float


class SemanticSearchEngine:
    """Singleton-friendly semantic retrieval engine."""

    def __init__(
        self,
        cache_dir: Path,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.model_name = model_name
        self.model = None
        self.intent_classifier = IntentClassifier(model_name=model_name)
        self.index_type = str(os.getenv("FAISS_INDEX_TYPE", "flat")).strip().lower()
        self.hnsw_m = int(os.getenv("FAISS_HNSW_M", "32"))
        self.hnsw_ef_search = int(os.getenv("FAISS_HNSW_EF_SEARCH", "96"))
        self.embedding_batch_size = max(16, int(os.getenv("EMBEDDING_BATCH_SIZE", "64")))
        self.query_embedding_ttl_seconds = max(30, int(os.getenv("QUERY_EMBED_CACHE_TTL_SECONDS", "900")))
        self.query_embedding_cache_size = max(256, int(os.getenv("QUERY_EMBED_CACHE_SIZE", "4096")))
        self._query_embedding_cache: Dict[str, Tuple[float, np.ndarray]] = {}
        self._query_cache_lock = threading.Lock()

        self._cases: List[Dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._index: VectorIndex | None = None

        self._meta_path = self.cache_dir / "semantic_meta.json"
        self._emb_path = self.cache_dir / "semantic_embeddings.npy"
        self._faiss_path = self.cache_dir / "semantic_index.faiss"

    def load_model(self):
        if self.model is None:
            self.model = load_sentence_transformer(self.model_name)
            logger.info("Semantic model loaded: %s", self.model_name)
        return self.model

    def reset(self) -> None:
        self._cases = []
        self._embeddings = None
        self._index = None
        self.model = None
        self.intent_classifier.reset()
        with self._query_cache_lock:
            self._query_embedding_cache = {}

    def ensure_index(self, cases: List[Dict[str, Any]]) -> None:
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
        corpus = [self._build_case_text(c) for c in self._cases]
        vectors = self.load_model().encode(
            corpus,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=self.embedding_batch_size,
        ).astype("float32")

        idx = self._build_index(vectors.shape[1])
        idx.add(vectors)

        self._embeddings = vectors
        self._index = idx
        self._save_cache(fingerprint)
        logger.info("Built FAISS semantic index for %d cases", len(corpus))

    def _build_index(self, dim: int) -> VectorIndex:
        if self.index_type == "hnsw":
            return FaissHNSWIndex(dim=dim, m=self.hnsw_m, ef_search=self.hnsw_ef_search)
        return FaissCosineIndex(dim=dim)

    def embed_query(self, text: str) -> np.ndarray:
        key = " ".join(str(text or "").strip().lower().split())
        now = time.time()
        with self._query_cache_lock:
            cached = self._query_embedding_cache.get(key)
            if cached and (now - float(cached[0])) <= self.query_embedding_ttl_seconds:
                return cached[1]
            if cached:
                self._query_embedding_cache.pop(key, None)

        embedding = self.load_model().encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        with self._query_cache_lock:
            if len(self._query_embedding_cache) >= self.query_embedding_cache_size:
                # Lightweight eviction: remove oldest insertion order entry.
                oldest_key = next(iter(self._query_embedding_cache.keys()), None)
                if oldest_key:
                    self._query_embedding_cache.pop(oldest_key, None)
            self._query_embedding_cache[key] = (now, embedding)
        return embedding

    def semantic_search(self, query: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not query or not query.strip():
            return [], {}
        if self._index is None:
            raise RuntimeError("Semantic index is not initialized")

        q = process_query(query)
        intent = self.intent_classifier.classify(
            query_text=q.expanded,
            query_tokens=q.tokens,
            query_keywords=q.keywords,
        )

        query_vector = self.embed_query(intent.query_for_retrieval)
        candidate_k = min(len(self._cases), max(24, top_k * 8))
        distances, indices = self._index.search(query_vector, candidate_k)

        scored_candidates: List[RetrievalCandidate] = []
        for semantic, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._cases):
                continue

            case = dict(self._cases[idx])
            case_keywords = case.get("keywords") or []
            if isinstance(case_keywords, str):
                case_keywords = [case_keywords]

            overlap = keyword_overlap(q.keywords, [str(k) for k in case_keywords])
            title_sim = title_similarity(q.expanded, str(case.get("subcategory", "")))
            intent_align = self._intent_alignment(intent.intent_keywords, case)
            final = min(1.0, hybrid_score(float(semantic), overlap, title_sim, intent_align))
            scored_candidates.append(
                RetrievalCandidate(
                    case=case,
                    semantic_score=float(semantic),
                    keyword_overlap=float(overlap),
                    title_similarity=float(title_sim),
                    intent_alignment=float(intent_align),
                    final_score=float(final),
                )
            )

        ranked = self._to_ranked_dicts(scored_candidates, query_keywords=q.keywords, matched_intent=intent.matched_intent)
        ranked = sorted(ranked, key=lambda d: float(d.get("similarity_score", 0.0)), reverse=True)
        if (not ranked) or float(ranked[0].get("similarity_score", 0.0)) < 0.46:
            ranked = self._merge_fuzzy_fallback(ranked, q.expanded, top_k=max(5, top_k))

        ranked = sorted(ranked, key=lambda d: float(d.get("similarity_score", 0.0)), reverse=True)
        ranked = self._diversified_top_k(ranked, top_k=max(5, top_k))
        confidence_label, confidence_score, need_clarification, confidence_signals = self._dynamic_confidence(
            ranked,
            intent,
            q.ambiguity_score,
            q.keywords,
        )

        for row in ranked:
            row["confidence"] = confidence_label

        limited = select_by_confidence(ranked)

        nlp_meta = QueryMeta(
            detected_language=q.language,
            normalized_query=q.normalized,
            search_ready_query=q.expanded,
            keywords=q.keywords,
            problem_domain=intent.legal_domain,
            problem_type=intent.problem_type,
            likely_authority=intent.authority_type,
            matched_intent=intent.matched_intent,
            confidence=confidence_label,
            intent_confidence_score=intent.confidence_score,
            overall_confidence_score=confidence_score,
            ambiguity_score=q.ambiguity_score,
            clarification_required=need_clarification,
            clarification_message=(
                "Your query is ambiguous for legal guidance. Please answer follow-up questions for a safe and precise match."
                if need_clarification
                else ""
            ),
            clarification_questions=intent.clarification_questions if need_clarification else [],
            reasoning_signals={**intent.reasoning_signals, **confidence_signals, **q.debug_signals},
        ).to_dict()

        return limited[:top_k], nlp_meta

    def _to_ranked_dicts(
        self,
        candidates: List[RetrievalCandidate],
        query_keywords: List[str],
        matched_intent: str,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in candidates:
            case = dict(item.case)
            case["score"] = round(float(item.final_score), 4)
            case["similarity_score"] = round(float(item.final_score), 4)
            case["match_type"] = "semantic"
            case["matched_keywords"] = self._matched_keywords(query_keywords, case)
            case["matched_intent"] = matched_intent
            case["semantic_score"] = round(float(item.semantic_score), 4)
            case["keyword_overlap"] = round(float(item.keyword_overlap), 4)
            case["title_similarity"] = round(float(item.title_similarity), 4)
            case["intent_alignment"] = round(float(item.intent_alignment), 4)
            out.append(case)
        return out

    def _diversified_top_k(self, ranked: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not ranked:
            return []
        selected: List[Dict[str, Any]] = []
        category_count: Dict[str, int] = {}
        max_per_category = 2

        for row in ranked:
            category = str(row.get("category", "Unknown"))
            count = category_count.get(category, 0)
            if count >= max_per_category:
                continue
            selected.append(row)
            category_count[category] = count + 1
            if len(selected) >= top_k:
                break

        if len(selected) < min(top_k, len(ranked)):
            for row in ranked:
                if row in selected:
                    continue
                selected.append(row)
                if len(selected) >= top_k:
                    break
        return selected

    def _dynamic_confidence(
        self,
        ranked: List[Dict[str, Any]],
        intent: IntentMatch,
        query_ambiguity: float,
        query_keywords: List[str],
    ) -> Tuple[str, float, bool, Dict[str, float]]:
        if not ranked:
            return "Low", 0.0, True, {
                "top_similarity": 0.0,
                "top_margin": 0.0,
                "keyword_hit_ratio": 0.0,
                "adaptive_high_threshold": 0.0,
                "adaptive_medium_threshold": 0.0,
            }

        scores = [float(row.get("similarity_score", 0.0)) for row in ranked[:10]]
        top = scores[0]
        second = scores[1] if len(scores) > 1 else 0.0
        margin = max(0.0, top - second)

        matched_keywords = ranked[0].get("matched_keywords") or []
        keyword_hit_ratio = min(1.0, len(matched_keywords) / max(1, len(query_keywords)))
        clarity_score = 1.0 - max(0.0, min(1.0, float(query_ambiguity)))
        intent_alignment_bonus = min(0.10, max(0.0, intent.confidence_score - 0.55))

        confidence_score = max(
            0.0,
            min(
                1.0,
                (0.52 * top)
                + (0.08 * margin)
                + (0.30 * intent.confidence_score)
                + (0.06 * keyword_hit_ratio)
                + (0.10 * clarity_score)
                + intent_alignment_bonus,
            ),
        )

        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        adaptive_high = max(0.54, mean_score + (0.45 * std_score))
        adaptive_medium = max(0.40, mean_score + (0.10 * std_score))

        label = "High" if confidence_score >= adaptive_high else ("Medium" if confidence_score >= adaptive_medium else "Low")

        ambiguity_flag = intent.ambiguous or margin < max(0.045, std_score * 0.40) or query_ambiguity > 0.62
        if ambiguity_flag and label == "High" and confidence_score < (adaptive_high + 0.08):
            label = "Medium"
        if ambiguity_flag and (label == "Medium") and confidence_score < (adaptive_medium - 0.04):
            label = "Low"

        if (
            intent.matched_intent != "General legal issue"
            and intent.confidence_score >= 0.56
            and clarity_score >= 0.60
            and top >= 0.50
            and query_ambiguity <= 0.60
        ):
            label = "High"

        if top < 0.42 and intent.confidence_score < 0.52:
            label = "Low"

        need_clarification = label == "Low"

        return label, round(confidence_score, 4), need_clarification, {
            "top_similarity": round(top, 4),
            "top_margin": round(margin, 4),
            "keyword_hit_ratio": round(keyword_hit_ratio, 4),
            "query_clarity": round(clarity_score, 4),
            "adaptive_high_threshold": round(adaptive_high, 4),
            "adaptive_medium_threshold": round(adaptive_medium, 4),
        }

    def _merge_fuzzy_fallback(self, ranked: List[Dict[str, Any]], query_text: str, top_k: int) -> List[Dict[str, Any]]:
        seen = {r.get("subcategory", "") for r in ranked}
        for case in self._cases:
            base = " ".join(
                [
                    str(case.get("subcategory", "")),
                    str(case.get("category", "")),
                    " ".join(case.get("keywords", []) or []),
                ]
            )
            fuzzy_score = fuzz.token_set_ratio(query_text, base.lower()) / 100.0
            if fuzzy_score < 0.58:
                continue

            sub = case.get("subcategory", "")
            if sub in seen:
                continue

            out = dict(case)
            out["score"] = round(float(fuzzy_score), 4)
            out["similarity_score"] = round(float(fuzzy_score), 4)
            out["match_type"] = "fuzzy"
            out["matched_keywords"] = []
            out["matched_intent"] = "General legal issue"
            out["semantic_score"] = round(float(fuzzy_score), 4)
            out["keyword_overlap"] = 0.0
            out["title_similarity"] = round(float(fuzzy_score), 4)
            out["intent_alignment"] = 0.0
            ranked.append(out)
            seen.add(sub)

            if len(ranked) >= top_k * 2:
                break

        return ranked

    def _intent_alignment(self, intent_keywords: List[str], case: Dict[str, Any]) -> float:
        if not intent_keywords:
            return 0.0
        haystack = " ".join(
            [
                str(case.get("category", "")),
                str(case.get("subcategory", "")),
                str(case.get("problem_description", "")),
                " ".join(str(k) for k in (case.get("keywords") or []) if k),
            ]
        ).lower()

        hits = 0
        for keyword in intent_keywords:
            k = str(keyword).lower()
            if k in haystack:
                hits += 1
                continue
            if fuzz.partial_ratio(k, haystack) >= 90:
                hits += 1
        return min(1.0, hits / max(1, len(intent_keywords)))

    def _build_case_text(self, case: Dict[str, Any]) -> str:
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

        query_set = {k.lower() for k in query_keywords if k}
        matched = []
        for ck in [str(k).lower() for k in case_keywords]:
            if ck in query_set:
                matched.append(ck)
                continue
            if any(fuzz.ratio(ck, qq) >= 86 for qq in query_set):
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
                and str(meta.get("index_type", "flat")) == self.index_type
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
                    "index_type": self.index_type,
                    "count": len(self._cases),
                    "vector_dim": int(self._embeddings.shape[1]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
