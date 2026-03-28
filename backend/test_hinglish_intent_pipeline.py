"""Regression tests for Hinglish-heavy intent understanding and confidence."""

from __future__ import annotations

from django.test import SimpleTestCase

from legal_cases import services


class HinglishIntentPipelineTest(SimpleTestCase):
    def test_required_queries_have_high_confidence_and_correct_intent(self):
        cases = [
            {
                "query": "FIR kaise file kare",
                "intent": "Police FIR Refusal",
                "category_tokens": ["police", "fir", "तक्रार", "पोलीस"],
            },
            {
                "query": "police complaint kese kare",
                "intent": "Police FIR Refusal",
                "category_tokens": ["police", "fir", "complaint"],
            },
            {
                "query": "ghar me jhagda hua kya kare",
                "intent": "Domestic Violence / Family Safety",
                "category_tokens": ["domestic", "family", "violence"],
            },
            {
                "query": "consumer complaint ka process kya hai",
                "intent": "Consumer Complaint",
                "category_tokens": ["consumer", "refund", "product", "service"],
            },
        ]

        for row in cases:
            results, nlp = services.search_cases(row["query"], top_k=3)

            self.assertTrue(results, msg=f"No results returned for query: {row['query']}")
            self.assertEqual(str(nlp.get("matched_intent")), row["intent"])
            self.assertEqual(str(nlp.get("confidence")), "High")
            self.assertFalse(bool(nlp.get("clarification_required")))

            top = results[0]
            merged_text = f"{top.get('category', '')} {top.get('subcategory', '')}".lower()
            self.assertTrue(
                any(token.lower() in merged_text for token in row["category_tokens"]),
                msg=(
                    f"Top workflow mapping mismatch for query={row['query']}. "
                    f"category={top.get('category')} subcategory={top.get('subcategory')}"
                ),
            )

    def test_typos_and_spoken_hinglish_variants_are_handled(self):
        query = "polce complint kese kare"
        results, nlp = services.search_cases(query, top_k=3)

        self.assertTrue(results)
        self.assertEqual(str(nlp.get("matched_intent")), "Police FIR Refusal")
        self.assertIn(str(nlp.get("confidence")), {"High", "Medium"})
        self.assertFalse(bool(nlp.get("clarification_required", False)))
