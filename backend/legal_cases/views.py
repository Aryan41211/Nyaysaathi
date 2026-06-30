"""
Compatibility module.

Tests expect:
  legal_cases.views.generate_legal_guidance

The actual app routes search requests through api.views.search and
ai logic through api.nlp.query_processor.process_query. This shim
keeps the test contract stable.
"""

from api.nlp.query_processor import process_query


def generate_legal_guidance(query: str, top_k: int = 5, **kwargs):
    """
    Minimal wrapper to satisfy test mocking targets.

    Returns a dict similar to what the API would return from /api/search/.
    """
    return process_query(query, top_k=top_k)
