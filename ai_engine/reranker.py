from __future__ import annotations

import re


class ContextReranker:
    """Rule-based context reranker over top semantic matches."""

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9\u0900-\u097f]+", (text or "").lower()))

    @staticmethod
    def _has_all(tokens: set[str], terms: set[str]) -> bool:
        return terms.issubset(tokens)

    def rerank(self, text: str, matches: list[dict]) -> list[dict]:
        if not matches:
            return matches

        tokens = self._tokens(text)

        rules: list[tuple[callable, tuple[str, ...], float]] = [
            (lambda t: self._has_all(t, {"ghar", "chori"}) or self._has_all(t, {"house", "robbery"}), ("Domestic Robbery / House Break-In",), 0.15),
            (lambda t: ("chori" in t or "theft" in t) and ({"gaadi", "bike", "vehicle"} & t), ("Vehicle Theft Complaint",), 0.15),
            (lambda t: ("mobile" in t) and ("chori" in t or "theft" in t), ("Theft Complaint",), 0.15),
            (lambda t: (("salary" in t) and ("nahi" in t or "not" in t)) or (("mazdoori" in t) and ("nahi" in t or "not" in t)), ("Salary Not Paid by Employer",), 0.20),
            (lambda t: (("zameen" in t or "land" in t) and ("kabza" in t or "encroachment" in t)), ("Illegal Land Occupation / Encroachment",), 0.20),
            (lambda t: (("zameen" in t or "land" in t) and ("seema" in t or "hadd" in t or "boundary" in t)), ("Land Boundary Dispute",), 0.20),
            (lambda t: (("upi" in t and "fraud" in t) or ("otp" in t and "gaya" in t) or ({"paisa", "gaya", "online"}.issubset(t)) or ({"money", "gone", "online"}.issubset(t))), ("UPI / Online Payment Fraud",), 0.20),
            (lambda t: (("deposit" in t and "wapas" in t and "nahi" in t) or ("security" in t and "nahi" in t) or ("security" in t and "not" in t)), ("Landlord Refusing to Return Security Deposit",), 0.20),
            (lambda t: (("pati" in t and "mara" in t) or ({"husband", "beat"}.issubset(t)) or ("dahej" in t) or ("dowry" in t)), ("Domestic Abuse / Physical Violence by Spouse",), 0.20),
            (lambda t: (("police" in t and "fir" in t and ("nahi" in t or "not" in t)) or ("thane" in t and "nahi" in t and "suna" in t)), ("Police Refusing to File FIR (Non-Registration of Complaint)",), 0.20),
            (lambda t: ("pension" in t and ("nahi" in t or "ruk" in t or "not" in t or "stopped" in t)), ("Pension Delay or Non-Payment (Old Age / Widow / Disability Pension)",), 0.20),
            (lambda t: (("ration" in t) and ("nahi" in t or "not" in t)), ("Ration Card Issue / Denial of PDS Benefits",), 0.20),
        ]

        adjusted = [dict(item) for item in matches]

        for matcher, subcategories, boost in rules:
            if not matcher(tokens):
                continue
            for item in adjusted:
                subcategory = str(item.get("subcategory", "")).strip()
                if subcategory in subcategories:
                    item["score"] = min(1.0, float(item.get("score", 0.0)) + boost)

        adjusted.sort(key=lambda m: float(m.get("score", 0.0)), reverse=True)
        return adjusted
