"""Runtime helpers for memory-safe AI model loading on low-tier cloud instances."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_TORCH_CONFIGURED = False
_TORCH_LOCK = threading.Lock()
_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_CACHE: dict[str, object] = {}


def configure_torch_runtime() -> None:
    """Apply conservative torch settings once per process.

    This keeps CPU usage and memory pressure lower on 512MB deployments.
    """
    global _TORCH_CONFIGURED
    if _TORCH_CONFIGURED:
        return

    with _TORCH_LOCK:
        if _TORCH_CONFIGURED:
            return
        try:
            import torch

            torch.set_num_threads(1)
            torch.set_grad_enabled(False)
            logger.info("Torch runtime configured for low-memory mode")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Torch runtime optimization skipped: %s", exc)
        finally:
            _TORCH_CONFIGURED = True


def load_sentence_transformer(model_name: str):
    """Lazy-load SentenceTransformer after applying torch runtime settings."""
    configure_torch_runtime()
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    with _MODEL_CACHE_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]

        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        _MODEL_CACHE[model_name] = model
        logger.info("Loaded sentence transformer model: %s", model_name)
        return model
