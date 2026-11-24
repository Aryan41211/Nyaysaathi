"""NyaySaathi corpus expansion script.

Generates additional legal-case records from the existing 201-case seed
corpus using template-based paraphrase and entity substitution.

Output: backend/dataset/expanded_cases.json — created alongside legal_cases.json.
Read-only source; does not modify existing legal_cases.json.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = REPO_ROOT / "backend"
DATA_FILE = BACKEND / "dataset" / "legal_cases.json"
OUT_PATH = BACKEND / "dataset" / "expanded_cases.json"
SEED = 42
TARGET_TOTAL = 500  # target corpus size including original 201


def _paraphrase(text: str, rng: random.Random) -> str:
    """Light paraphrase: reorder clauses, swap synonyms."""
    if not text:
        return text
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if len(sentences) > 2 and rng.random() < 0.4:
        rng.shuffle(sentences)
    text = ". ".join(sentences)
    if text and not text.endswith("."):
        text += "."
    rng_map = {
        "neighbour": ["neighbor", "adjoining owner"],
        "land": ["property", "plot"],
        "boundary": ["border", "demarcation line"],
        "encroached": ["encroached on", "illegally occupied"],
        "salary": ["wages", "pay"],
        "employer": ["company", "firm"],
        "court": ["civil court", "district court"],
    }
    for k, v in rng_map.items():
        if k in text.lower() and rng.random() < 0.3:
            text = text.replace(k, rng.choice(v))
    return text


def expand_case(case: Dict, idx: int, rng: random.Random) -> Dict:
    """Create a variant of an existing case."""
    new = dict(case)
    new["id"] = f"expanded:{idx}"
    new["source"] = "synthetic_expansion"
    new["category"] = case.get("category", "Unknown")
    new["subcategory"] = case.get("subcategory", "General Legal Issue")
    new["problem_description"] = _paraphrase(case.get("problem_description", ""), rng)
    new["workflow_steps"] = list(case.get("workflow_steps", []))
    new["required_documents"] = list(case.get("required_documents", []))
    new["authorities"] = list(case.get("authorities", []))
    new["escalation_path"] = list(case.get("escalation_path", []))
    new["online_portals"] = list(case.get("online_portals", []))
    new["helplines"] = list(case.get("helplines", []))
    new["descriptions"] = [_paraphrase(d, rng) for d in case.get("descriptions", [])[:3]]
    new["raw"] = None
    new["searchable_text"] = " ".join(
        filter(
            None,
            [
                new.get("category", ""),
                new.get("subcategory", ""),
                new.get("problem_description", ""),
                " ".join(new.get("descriptions", [])),
                " ".join(new.get("workflow_steps", [])),
            ],
        )
    ).strip()
    return new


def main() -> int:
    rng = random.Random(SEED)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)
    n_existing = len(cases)
    target = min(TARGET_TOTAL, n_existing * 3)  # cap at 3x original
    needed = target - n_existing
    if needed <= 0:
        print(f"Corpus already at {n_existing} cases; no expansion needed.")
        return 0

    expanded = []
    for i in range(needed):
        base = rng.choice(cases)
        expanded.append(expand_case(base, n_existing + i, rng))

    out = list(cases) + expanded
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Original: {n_existing} cases")
    print(f"Added: {len(expanded)} cases")
    print(f"Total: {len(out)} cases written to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
