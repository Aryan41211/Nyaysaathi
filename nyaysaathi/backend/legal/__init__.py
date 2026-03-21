"""AI orchestration package for legal understanding."""

from .ai_engine import get_ai_monitoring_snapshot, get_example_test_inputs, understand_user_problem
from .confidence_engine import ConfidenceEngine
from .embedding_engine import EmbeddingStore, generate_dataset_embeddings, get_embedding_store, get_user_embedding, load_model
from .fallback_engine import FallbackEngine
from .intent_engine import IntentEngine
from .monitoring import AIMonitor
from .preprocessing import clean_text, normalize_text, remove_stopwords
from .similarity_engine import find_best_match

__all__ = [
	"AIMonitor",
	"ConfidenceEngine",
	"EmbeddingStore",
	"clean_text",
	"normalize_text",
	"remove_stopwords",
	"find_best_match",
	"FallbackEngine",
	"generate_dataset_embeddings",
	"get_embedding_store",
	"get_user_embedding",
	"IntentEngine",
	"load_model",
	"get_ai_monitoring_snapshot",
	"get_example_test_inputs",
	"understand_user_problem",
]
