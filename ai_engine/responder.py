from __future__ import annotations

import os

from openai import OpenAI


def _has_real_openai_key() -> bool:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return False
    if key.lower() in {"your_key_here", "changeme", "none", "null"}:
        return False
    return True


class FriendlyResponder:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.client = OpenAI() if _has_real_openai_key() else None

    @staticmethod
    def _fallback_message(query: str, category: str, subcategory: str, confidence: float, steps: list[str]) -> str:
        tone = "high" if confidence >= 0.8 else "medium" if confidence >= 0.6 else "low"
        first_step = steps[0] if steps else "collect the key facts and documents"
        if tone == "high":
            return (
                f"I understood your issue as {subcategory} under {category}. "
                f"Start with this: {first_step}. "
                "If you want, I can also draft the exact complaint text for you."
            )
        if tone == "medium":
            return (
                f"Your issue most likely maps to {subcategory} under {category}. "
                f"A good next action is: {first_step}. "
                "Share one more detail if you want a sharper recommendation."
            )
        return (
            "I may need one or two more details to be fully accurate. "
            f"Right now, the closest match is {subcategory} under {category}. "
            f"You can begin with: {first_step}."
        )

    def generate(
        self,
        query: str,
        category: str,
        subcategory: str,
        confidence: float,
        workflow_steps: list[str],
        needs_clarification: bool,
        clarification_question: str,
    ) -> str:
        if needs_clarification and clarification_question:
            return f"I need one quick clarification before guiding you properly: {clarification_question}"

        if self.client is None:
            return self._fallback_message(query, category, subcategory, confidence, workflow_steps)

        prompt = (
            "You are NyaySaathi, a calm legal help assistant. "
            "Write a concise, friendly response in plain English/Hinglish (2-4 short sentences). "
            "Mention identified category and subcategory, then one immediate practical next step. "
            "Do not provide legal guarantees."
        )
        user = (
            f"User query: {query}\n"
            f"Category: {category}\n"
            f"Subcategory: {subcategory}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Top workflow step: {(workflow_steps[0] if workflow_steps else 'Collect facts and documents')}\n"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            return text or self._fallback_message(query, category, subcategory, confidence, workflow_steps)
        except Exception:
            return self._fallback_message(query, category, subcategory, confidence, workflow_steps)
