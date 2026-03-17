from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from models.schemas import ClassificationResult
from prompts.classify import CLASSIFY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _has_real_openai_key() -> bool:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return False
    if key.lower() in {"your_key_here", "changeme", "none", "null"}:
        return False
    return True


class LLMClassifier:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.client = OpenAI() if _has_real_openai_key() else None
        self.last_llm_available = self.client is not None

    @staticmethod
    def _fallback_from_embedding(user_input: str, embedding_match: dict | None) -> ClassificationResult:
        if embedding_match:
            return ClassificationResult(
                category=str(embedding_match.get("category_id") or "consumer_complaints"),
                subcategory=str(embedding_match.get("subcategory") or "General Complaint"),
                intent_summary=f"Classified via semantic fallback for: {user_input[:120]}",
                confidence=float(max(0.55, min(1.0, embedding_match.get("score", 0.65)))),
                needs_clarification=False,
                clarification_question="",
                extracted_facts={"mode": "embedding_fallback"},
            )

        return ClassificationResult(
            category="consumer_complaints",
            subcategory="General Grievance",
            intent_summary=f"Fallback classification for: {user_input[:120]}",
            confidence=0.55,
            needs_clarification=False,
            clarification_question="",
            extracted_facts={"mode": "default_fallback"},
        )

    def classify(self, user_input: str, embedding_match: dict | None = None) -> ClassificationResult:
        if self.client is None:
            self.last_llm_available = False
            return self._fallback_from_embedding(user_input, embedding_match)

        try:
            self.last_llm_available = True
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return ClassificationResult.model_validate(data)
        except Exception as exc:
            self.last_llm_available = False
            logger.info("LLM unavailable, using embedding fallback")
            return self._fallback_from_embedding(user_input, embedding_match)