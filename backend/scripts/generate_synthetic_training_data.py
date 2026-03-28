"""Generate synthetic multilingual query variants for NyaySaathi training data.

Creates spelling, slang, and transliterated Hinglish variants from seed records.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SeedRecord:
    language: str
    query: str
    intent_label: str


HINGLISH_VARIANTS = {
    "kaise": ["kaise", "kese", "kaisey", "kaisy"],
    "nahi": ["nahi", "nhi", "nai", "nahee"],
    "kyu": ["kyu", "kyo", "kyun", "q"],
    "mera": ["mera", "mere", "meri", "mra"],
    "salary": ["salary", "salry", "sallary"],
    "landlord": ["landlord", "land lord", "owner", "makaan malik"],
    "police": ["police", "polis", "thana", "cop"],
}

SLANG_REWRITES = {
    "ignore kar raha": ["bhaav nahi de raha", "ignore maar raha", "response hi nahi"],
    "refund": ["paise wapas", "return paisa", "refund paisa"],
    "complaint": ["shikayat", "report", "likhit complaint"],
}

MISSPELLINGS = {
    "complaint": ["compalint", "compliant"],
    "deposit": ["deposit", "deposite", "depojit"],
    "salary": ["salery", "sallery", "sallary"],
    "fraud": ["froud", "fruad"],
}


def _token_replacements(query: str, replacements: dict[str, list[str]]) -> list[str]:
    base = query.strip()
    variants = {base}
    for key, values in replacements.items():
        if key in base.lower():
            for value in values:
                variants.add(base.lower().replace(key, value))
    return [v.strip() for v in variants if v.strip()]


def _slang_variants(query: str) -> list[str]:
    variants = {query}
    for key, values in SLANG_REWRITES.items():
        if key in query.lower():
            for value in values:
                variants.add(query.lower().replace(key, value))
    return list(variants)


def _misspelling_variants(query: str) -> list[str]:
    variants = {query}
    for token, noisy in MISSPELLINGS.items():
        if token in query.lower():
            for miss in noisy:
                variants.add(query.lower().replace(token, miss))
    return list(variants)


def generate_variations(seed: SeedRecord, per_seed: int = 24) -> list[dict[str, Any]]:
    base_candidates = _token_replacements(seed.query, HINGLISH_VARIANTS)
    slang_candidates: list[str] = []
    miss_candidates: list[str] = []

    for text in base_candidates:
        slang_candidates.extend(_slang_variants(text))
        miss_candidates.extend(_misspelling_variants(text))

    pool = list({seed.query, *base_candidates, *slang_candidates, *miss_candidates})
    random.shuffle(pool)
    selected = pool[: max(1, per_seed)]

    rows = []
    for idx, query in enumerate(selected, start=1):
        rows.append(
            {
                "id": f"synthetic-{seed.intent_label.lower().replace(' ', '-')}-{idx}",
                "language": seed.language,
                "query": query,
                "intent_label": seed.intent_label,
                "expected_output": {
                    "decision": "answer_with_disclaimer",
                    "disclaimer_required": True,
                },
                "metadata": {
                    "source": "synthetic",
                    "generator": "variation_rules_v1",
                },
            }
        )
    return rows


def _load_seed(path: Path) -> list[SeedRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    examples = payload.get("examples") or []
    records: list[SeedRecord] = []
    for row in examples:
        records.append(
            SeedRecord(
                language=str(row.get("language") or "hinglish"),
                query=str(row.get("query") or "").strip(),
                intent_label=str(row.get("intent_label") or "General legal issue"),
            )
        )
    return [r for r in records if r.query]


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    seed_path = root / "dataset" / "training_dataset_schema_multilingual.json"
    output_path = root / "dataset" / "synthetic_multilingual_training.json"

    seeds = _load_seed(seed_path)
    generated: list[dict[str, Any]] = []

    for seed in seeds:
        generated.extend(generate_variations(seed))

    output_payload = {
        "schema_version": "1.0",
        "generated_count": len(generated),
        "records": generated,
    }
    output_path.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(generated)} synthetic records at {output_path}")


if __name__ == "__main__":
    main()
