from __future__ import annotations

import re
from difflib import SequenceMatcher

from ai_engine.embedder import CANONICAL_CATEGORY_MAP


class IntentRouter:
    """Minimal high-accuracy reranker for MVP intent routing.

    Uses candidate semantic scores + lexical evidence against dataset fields.
    """

    def __init__(self, dataset: list[dict]) -> None:
        self.dataset = dataset
        self.by_subcategory = {
            str(item.get("subcategory", "")).strip().lower(): item for item in dataset
        }
        self.category_signals = {
            "cyber_fraud_and_digital_scams": {"upi", "otp", "cyber", "fraud", "scam", "qr", "vishing", "whatsapp", "online"},
            "labour_and_wage_issues": {"salary", "wage", "wages", "employer", "labour", "overtime", "pf", "gratuity", "termination"},
            "land_and_property_disputes": {"land", "property", "encroachment", "boundary", "mutation", "registry", "possession", "ancestral"},
            "tenant_landlord_disputes": {"landlord", "tenant", "rent", "deposit", "eviction", "utilities"},
            "domestic_violence_and_family_disputes": {"dowry", "domestic", "husband", "wife", "custody", "marriage", "maintenance"},
            "police_complaints_and_local_crime": {"fir", "police", "theft", "robbery", "assault", "murder", "threat", "extortion", "kidnapping"},
            "government_scheme_and_public_service_issues": {"ration", "pension", "certificate", "scholarship", "mnrega", "aadhaar", "passport", "bribery"},
            "consumer_complaints": {"defective", "warranty", "claim", "overcharging", "medicine", "consumer", "product", "delivered"},
            "senior_citizen_protection_issues": {"senior", "elderly", "parents", "bujurg", "old age"},
            "environmental_and_public_nuisance_complaints": {"pollution", "nuisance", "noise", "garbage", "environment"},
        }

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9\u0900-\u097f]+", (text or "").lower()))

    def _entry_text(self, entry: dict) -> str:
        descriptions = entry.get("descriptions") or []
        if isinstance(descriptions, str):
            descriptions = [descriptions]
        return " ".join(
            [
                str(entry.get("category", "")),
                str(entry.get("subcategory", "")),
                str(entry.get("problem_description", "")),
                " ".join(str(d) for d in descriptions),
            ]
        ).strip()

    def category_id(self, category_label: str) -> str:
        return CANONICAL_CATEGORY_MAP.get(str(category_label).strip().lower(), "unknown")

    @staticmethod
    def _rule_boost(q_tokens: set[str], category_id: str) -> float:
        crime_tokens = {"theft", "robbery", "fir", "police", "assault", "murder", "kidnapping", "extortion", "threat"}
        labour_tokens = {"salary", "wages", "employer", "pf", "gratuity", "overtime"}
        property_tokens = {"land", "property", "encroachment", "mutation", "registry", "possession", "ancestral", "boundary"}
        tenant_tokens = {"landlord", "tenant", "rent", "deposit", "eviction", "utilities"}
        cyber_tokens = {"upi", "otp", "cyber", "fraud", "scam", "qr", "vishing", "whatsapp"}

        if category_id == "police_complaints_and_local_crime" and (q_tokens & crime_tokens):
            return 0.22
        if category_id == "labour_and_wage_issues" and (q_tokens & labour_tokens):
            return 0.16
        if category_id == "land_and_property_disputes" and (q_tokens & property_tokens):
            return 0.16
        if category_id == "tenant_landlord_disputes" and (q_tokens & tenant_tokens):
            return 0.16
        if category_id == "cyber_fraud_and_digital_scams" and (q_tokens & cyber_tokens):
            return 0.20
        return 0.0

    def rerank(self, query: str, embedding_matches: list[dict]) -> tuple[dict | None, float, dict | None]:
        q = (query or "").strip()
        q_tokens = self._tokens(q)
        if not embedding_matches:
            return None, 0.0, None

        scored: list[tuple[float, dict, dict]] = []
        for match in embedding_matches:
            sub = str(match.get("subcategory", "")).strip().lower()
            entry = self.by_subcategory.get(sub)
            if not entry:
                continue

            base_score = float(match.get("score", 0.0))
            entry_text = self._entry_text(entry)
            e_tokens = self._tokens(entry_text)

            token_overlap = len(q_tokens & e_tokens) / max(1, len(q_tokens | e_tokens))
            seq = SequenceMatcher(None, q.lower(), entry_text.lower()).ratio()
            category_id = self.category_id(str(entry.get("category", "")))
            category_keywords = self.category_signals.get(category_id, set())
            category_hits = len(q_tokens & category_keywords)
            category_boost = min(0.20, 0.05 * category_hits)
            rule_boost = self._rule_boost(q_tokens, category_id)
            blended = min(1.0, (0.52 * base_score) + (0.18 * token_overlap) + (0.12 * seq) + category_boost + rule_boost)
            scored.append((blended, entry, match))

        if not scored:
            return None, 0.0, None

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_entry, best_match = scored[0]
        secondary = scored[1][1] if len(scored) > 1 else None
        return best_entry, float(best_score), secondary
