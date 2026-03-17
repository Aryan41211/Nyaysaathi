from __future__ import annotations

from models.schemas import ClassificationResult


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class FusionScorer:
    def __init__(self, embed_weight: float = 0.35, llm_weight: float = 0.65) -> None:
        self.embed_weight = embed_weight
        self.llm_weight = llm_weight

    def fuse(self, llm_result: ClassificationResult, embedding_matches: list[dict], llm_available: bool = True) -> dict:
        top_embed = embedding_matches[0] if embedding_matches else None
        embed_category = (top_embed or {}).get("category_id", "unknown")
        embed_score = float((top_embed or {}).get("score", 0.0))
        llm_score = float(llm_result.confidence)

        if not llm_available:
            final_confidence = _clamp(embed_score)
            needs_clarification = final_confidence < 0.55
            return {
                "embed_score": embed_score,
                "llm_score": 0.0,
                "final_confidence": final_confidence,
                "needs_clarification": needs_clarification,
                "clarification_question": "Please share key details like timeline, amount, parties involved, and location." if needs_clarification else "",
                "top_embed": top_embed,
            }

        final_confidence = self.embed_weight * embed_score + self.llm_weight * llm_score

        agree = embed_category == llm_result.category and embed_category != "unknown"
        strong_disagree = (
            embed_category != "unknown"
            and llm_result.category != "unknown"
            and embed_category != llm_result.category
        )

        if agree:
            final_confidence += 0.10
        elif strong_disagree:
            final_confidence -= 0.15

        final_confidence = _clamp(final_confidence)
        needs_clarification = llm_result.needs_clarification or final_confidence < 0.55

        clarification_question = llm_result.clarification_question
        if needs_clarification and not clarification_question:
            clarification_question = "Please share key details like timeline, amount, parties involved, and location."

        return {
            "embed_score": embed_score,
            "llm_score": llm_score,
            "final_confidence": final_confidence,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "top_embed": top_embed,
        }