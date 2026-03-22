"""Embedding engine for fully local semantic legal classification."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from sentence_transformers import SentenceTransformer

from .preprocessing import clean_text
from .settings import EMBEDDING_MODEL_NAME

MODEL_NAME = EMBEDDING_MODEL_NAME

# Multi-example category representation for robust phrasing coverage.
LEGAL_DATASET: dict[str, list[str]] = {
    "LABOUR": [
        "Employer not paying salary",
        "Company delayed salary",
        "Wages not received",
        "Office payment pending",
        "Salary not credited",
        "Employer refusing payment",
        "Salary dispute with company",
    ],
    "CYBER": [
        "Online fraud happened",
        "UPI fraud",
        "Bank scam",
        "Account hacked",
        "Money stolen online",
        "Digital payment fraud",
    ],
    "PROPERTY": [
        "Landlord not returning deposit",
        "Tenant dispute",
        "Property conflict",
        "Rent issue",
        "Owner refusing refund",
    ],
}

_MODEL: SentenceTransformer | None = None
_MODEL_LOCK = Lock()
_STORE: EmbeddingStore | None = None
_STORE_LOCK = Lock()


@dataclass(frozen=True)
class EmbeddingStore:
    """Precomputed embedding cache for fast semantic lookup."""

    dataset_texts: list[str]
    dataset_categories: list[str]
    dataset_embeddings: np.ndarray


def load_model() -> SentenceTransformer:
    """Load sentence transformer once per process."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is None:
            _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def get_embedding_model() -> SentenceTransformer:
    """Serverless-safe model singleton accessor."""
    return load_model()


def is_model_loaded() -> bool:
    """Return whether embedding model is already warm in this instance."""
    return _MODEL is not None


def _flatten_dataset() -> tuple[list[str], list[str]]:
    """Flatten category -> phrase list into aligned arrays."""
    dataset_texts: list[str] = []
    dataset_categories: list[str] = []

    for category, phrases in LEGAL_DATASET.items():
        for phrase in phrases:
            normalized = clean_text(phrase)
            if normalized:
                dataset_texts.append(normalized)
                dataset_categories.append(category)

    return dataset_texts, dataset_categories


def generate_dataset_embeddings(dataset_texts: list[str]) -> np.ndarray:
    """Generate embedding matrix for all dataset phrases."""
    if not dataset_texts:
        return np.array([], dtype=np.float32)

    model = load_model()
    matrix = model.encode(dataset_texts, normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(matrix, dtype=np.float32)


def _build_store() -> EmbeddingStore:
    dataset_texts, dataset_categories = _flatten_dataset()
    dataset_embeddings = generate_dataset_embeddings(dataset_texts)
    return EmbeddingStore(
        dataset_texts=dataset_texts,
        dataset_categories=dataset_categories,
        dataset_embeddings=dataset_embeddings,
    )


def get_embedding_store() -> EmbeddingStore:
    """Return startup-cached dataset embeddings without recomputation per request."""
    global _STORE
    if _STORE is not None:
        return _STORE

    with _STORE_LOCK:
        if _STORE is None:
            _STORE = _build_store()
    return _STORE


def get_user_embedding(text: str) -> np.ndarray:
    """Generate one user embedding after normalization."""
    normalized = clean_text(text)
    model = get_embedding_model()
    matrix = model.encode([normalized], normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(matrix[0], dtype=np.float32)
