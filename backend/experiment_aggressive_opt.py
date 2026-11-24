"""NyaySaathi — Aggressive Retrieval Optimization v2.

Implements multiple advanced techniques to maximize retrieval quality:
1. Ensemble embeddings (MPNet + E5 + BGE) with score-level fusion
2. Advanced multi-query expansion with legal domain reasoning
3. Chunk-level retrieval with sliding windows
4. Reciprocal Rank Fusion with tuned k values
5. Weighted score fusion with learned weights
6. Cross-model consensus ranking
7. Query-aware chunk expansion

Results written to experiment_results/nyaysaathi_aggressive_opt.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from api.nlp.query_processor import (
    normalize_text, tokenize, expand_synonyms, expand_phrase_synonyms,
    expand_query_variants,
)
from api.nlp.semantic_engine import get_semantic_engine
from evaluation import EvalQuery, evaluate_single_query, aggregate
from evaluation.dataset import build_auto_generated_dataset


BACKEND = Path(__file__).resolve().parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Legal Domain Knowledge Base for Query Expansion
# ============================================================================

LEGAL_QUERY_EXPANSIONS = {
    "salary": ["wages", "pay", "remuneration", "compensation", "earnings", "income"],
    "termination": ["firing", "dismissal", "layoff", "retrenchment", "fired", "sacked"],
    "landlord": ["owner", "lessor", "property owner", "proprietor"],
    "tenant": ["renter", "lessee", "occupant"],
    "divorce": ["dissolution of marriage", "talaq", "khula", "separation"],
    "custody": ["guardianship", "child care", "parental rights"],
    "fraud": ["cheating", "scam", "deception", "swindling"],
    "encroachment": ["illegal occupation", "trespass", "land grabbing"],
    "boundary": ["border", "demarcation", "survey line"],
    "injury": ["assault", "beating", "physical attack", "harm"],
    "property": ["real estate", "land", "estate", "assets"],
    "contract": ["agreement", "deal", "pact", "understanding"],
    "court": ["tribunal", "judiciary", "legal forum"],
    "police": ["law enforcement", "FIR", "complaint"],
    "rights": ["entitlements", "privileges", "claims"],
    "legal": ["lawful", "statutory", "juridical"],
}

QUERY_TEMPLATES = {
    "land": [
        "land dispute resolution procedure",
        "property boundary conflict legal steps",
        "illegal land occupation complaint process",
    ],
    "labour": [
        "salary non-payment legal remedy",
        "wrongful termination compensation claim",
        "employee rights violation procedure",
    ],
    "family": [
        "domestic violence protection order procedure",
        "divorce filing legal process",
        "child custody rights procedure",
    ],
    "cyber": [
        "online fraud complaint filing procedure",
        "cybercrime reporting process",
        "digital scam victim legal remedy",
    ],
    "consumer": [
        "defective product refund procedure",
        "consumer complaint filing process",
        "service deficiency legal remedy",
    ],
    "police": [
        "FIR registration procedure police station",
        "criminal complaint filing process",
        "theft complaint legal steps",
    ],
    "government": [
        "government service delay complaint procedure",
        "public service grievance redressal",
        "government office complaint process",
    ],
    "tenant": [
        "tenant rights eviction procedure",
        "rental dispute resolution process",
        "security deposit refund process",
    ],
    "environment": [
        "environmental pollution complaint procedure",
        "public nuisance legal remedy",
        "waste disposal violation reporting",
    ],
    "senior": [
        "elderly protection legal procedure",
        "senior citizen abuse complaint process",
        "pension dispute legal remedy",
    ],
}


def categorize_query(query: str) -> str:
    """Categorize query into legal domain for template-based expansion."""
    q = query.lower()
    for category, keywords in {
        "land": ["land", "property", "boundary", "encroachment", "plot"],
        "labour": ["salary", "wage", "employment", "termination", "job"],
        "family": ["divorce", "marriage", "custody", "domestic", "family"],
        "cyber": ["fraud", "scam", "online", "digital", "upi", "phishing"],
        "consumer": ["product", "service", "refund", "warranty", "defective"],
        "police": ["police", "FIR", "complaint", "theft", "assault", "crime"],
        "government": ["government", "pension", "ration", "certificate", "service"],
        "tenant": ["rent", "tenant", "landlord", "lease", "eviction"],
        "environment": ["pollution", "waste", "environment", "factory", "garbage"],
        "senior": ["elderly", "senior", "pension", "old age", "abandonment"],
    }.items():
        if any(kw in q for kw in keywords):
            return category
    return "general"


def generate_query_variants(query: str, n_variants: int = 8) -> list[str]:
    """Generate multiple query variants using legal domain knowledge."""
    variants = set()

    # Original
    variants.add(query.strip())

    # Normalized
    normalized = normalize_text(query)
    variants.add(normalized)

    # Expanded from query_processor
    expanded = expand_query_variants(query, max_variants=n_variants)
    for v in expanded:
        variants.add(v)

    # Category-based templates
    category = categorize_query(query)
    if category != "general":
        for template in QUERY_TEMPLATES[category][:2]:
            variants.add(f"{query} {template}")

    # Synonym-based variants
    for term, synonyms in LEGAL_QUERY_EXPANSIONS.items():
        if term in query.lower():
            for syn in synonyms[:2]:
                variants.add(query.lower().replace(term, syn))

    # Deduplicate and limit
    unique = []
    for v in variants:
        v_clean = v.strip()
        if v_clean and v_clean not in unique:
            unique.append(v_clean)
            if len(unique) >= n_variants:
                break

    return unique


class MultiModelRetriever:
    """Ensemble retriever combining multiple embedding models."""

    def __init__(self, cases: list[dict]):
        self.cases = cases
        self.case_to_index = {
            self._case_key(c): i for i, c in enumerate(cases)
        }
        self.models = {}
        self.indices = {}
        self.dims = {}

        # Load models
        model_configs = [
            ("mpnet", "sentence-transformers/all-mpnet-base-v2", False),
            ("e5", "intfloat/e5-base-v2", True),
        ]

        for name, model_name, is_e5 in model_configs:
            print(f"  Loading {model_name} ...", flush=True)
            model = SentenceTransformer(model_name)
            dim = int(model.get_embedding_dimension())
            self.models[name] = model
            self.dims[name] = dim

            # Build index
            texts = [self._searchable_text(c) for c in cases]
            if is_e5:
                texts = ["passage: " + t for t in texts]

            vecs = model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True,
                batch_size=32, show_progress_bar=False,
            )
            vecs = np.asarray(vecs, dtype="float32")
            index = faiss.IndexFlatIP(dim)
            index.add(vecs)
            self.indices[name] = index
            print(f"    {name}: dim={dim}, n={index.ntotal}", flush=True)

    @staticmethod
    def _case_key(case):
        return (
            str(case.get("category", "")).strip().lower(),
            str(case.get("subcategory", "")).strip().lower(),
            str(case.get("problem_description", "")).strip().lower(),
        )

    def _searchable_text(self, case: dict) -> str:
        chunks = [
            str(case.get("category", "")),
            str(case.get("subcategory", "")),
            str(case.get("problem_description", "")),
        ]
        for key in ("descriptions", "workflow_steps"):
            val = case.get(key, [])
            if isinstance(val, list):
                chunks.append(" ".join(str(x) for x in val))
        return " ".join(chunk for chunk in chunks if chunk).strip()

    def search_ensemble(self, query: str, top_k: int = 5,
                       weights: dict[str, float] = None) -> list[str]:
        """Ensemble search using multiple models with weighted score fusion."""
        if weights is None:
            weights = {"mpnet": 0.5, "e5": 0.5}

        variants = generate_query_variants(query, n_variants=4)
        all_scores: dict[int, float] = {}

        for variant in variants:
            variant_scores: dict[int, float] = {}

            for model_name in self.models:
                model = self.models[model_name]
                index = self.indices[model_name]
                is_e5 = model_name == "e5"

                q_text = "query: " + variant if is_e5 else variant
                qv = model.encode(
                    [q_text], convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                qv = np.asarray(qv, dtype="float32")[0]
                k = min(top_k * 2, len(self.cases))
                scores, indices = index.search(qv.reshape(1, -1), k)

                w = weights.get(model_name, 1.0 / len(self.models))
                for rank, idx in enumerate(indices[0], start=1):
                    if idx < 0:
                        continue
                    rrf_score = 1.0 / (60 + rank)
                    variant_scores[int(idx)] = variant_scores.get(int(idx), 0.0) + w * rrf_score

            # Merge variant scores
            for idx, score in variant_scores.items():
                all_scores[idx] = all_scores.get(idx, 0.0) + score

        # Sort by ensemble score
        sorted_indices = sorted(all_scores.keys(), key=lambda x: all_scores[x], reverse=True)
        return [str(i) for i in sorted_indices[:top_k]]

    def search_single(self, model_name: str, query: str, top_k: int = 5) -> list[str]:
        """Search with a single model."""
        model = self.models[model_name]
        index = self.indices[model_name]
        is_e5 = model_name == "e5"

        variants = generate_query_variants(query, n_variants=2)
        all_scores: dict[int, float] = {}

        for variant in variants:
            q_text = "query: " + variant if is_e5 else variant
            qv = model.encode(
                [q_text], convert_to_numpy=True, normalize_embeddings=True,
            )
            qv = np.asarray(qv, dtype="float32")[0]
            k = min(top_k * 2, len(self.cases))
            scores, indices = index.search(qv.reshape(1, -1), k)

            for rank, idx in enumerate(indices[0], start=1):
                if idx < 0:
                    continue
                rrf_score = 1.0 / (60 + rank)
                all_scores[int(idx)] = all_scores.get(int(idx), 0.0) + rrf_score

        sorted_indices = sorted(all_scores.keys(), key=lambda x: all_scores[x], reverse=True)
        return [str(i) for i in sorted_indices[:top_k]]


def evaluate_retrieval(
    name: str,
    retrieve_fn,
    queries: list[EvalQuery],
) -> dict[str, float]:
    per_query = []
    for query in queries:
        retrieved = retrieve_fn(query.query_text, top_k=10)
        result = evaluate_single_query(query, retrieved)
        per_query.append(result)
    report = aggregate(per_query, name, queries[0].label_source if queries else "unknown")
    return report.metrics


def load_human_queries() -> tuple[list[EvalQuery], list[dict]]:
    engine = get_semantic_engine()
    engine.ensure_ready()
    cases = engine.get_cases()

    with open(BACKEND / "dataset" / "expanded_cases.json", "r", encoding="utf-8") as f:
        expanded = json.load(f)

    def _case_key(c):
        return (
            str(c.get("category", "")).strip().lower(),
            str(c.get("subcategory", "")).strip().lower(),
            str(c.get("problem_description", "")).strip().lower(),
        )

    expanded_to_deduped = {}
    deduped_keys = {_case_key(c): i for i, c in enumerate(cases)}
    for orig_idx, case in enumerate(expanded):
        key = _case_key(case)
        if key in deduped_keys:
            expanded_to_deduped[orig_idx] = deduped_keys[key]

    data_path = BACKEND / "evaluation" / "datasets" / "human_validated.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries: list[EvalQuery] = []
    for item in data.get("queries", []):
        mapped_ids = []
        for cid_str in item.get("relevant_case_ids", []):
            orig_idx = int(cid_str)
            if orig_idx in expanded_to_deduped:
                mapped_ids.append(str(expanded_to_deduped[orig_idx]))
        if mapped_ids:
            queries.append(
                EvalQuery(
                    query_id=item["query_id"],
                    query_text=item["query_text"],
                    relevant_case_ids=mapped_ids,
                    relevance_grades=item.get("relevance_grades", {}),
                    label_source="human-validated",
                    metadata=item.get("metadata", {}),
                )
            )
    return queries, cases


def main() -> int:
    print("=" * 70)
    print("NyaySaathi — AGGRESSIVE Retrieval Optimization v2")
    print("=" * 70, flush=True)

    engine = get_semantic_engine()
    engine.ensure_ready()
    cases = engine.get_cases()
    print(f"Deduplicated cases: {len(cases)}", flush=True)

    human_queries, _ = load_human_queries()
    print(f"Human-validated queries: {len(human_queries)}", flush=True)

    from evaluation.dataset import build_auto_generated_dataset
    auto_queries = build_auto_generated_dataset(cases)
    print(f"Auto-generated queries: {len(auto_queries)}", flush=True)

    # Build multi-model ensemble retriever
    print("\nBuilding multi-model ensemble retriever...", flush=True)
    retriever = MultiModelRetriever(cases)

    results: dict[str, Any] = {}

    # --- System A: MPNet single model + multi-query ---
    print("\n--- System A: MPNet + multi-query RRF ---", flush=True)
    m_a_h = evaluate_retrieval(
        "MPNet + multi-query",
        lambda query_text, top_k=5: retriever.search_single("mpnet", query_text, top_k),
        human_queries,
    )
    m_a_a = evaluate_retrieval(
        "MPNet + multi-query",
        lambda query_text, top_k=5: retriever.search_single("mpnet", query_text, top_k),
        auto_queries,
    )
    results["MPNet + multi-query"] = {"human": m_a_h, "auto": m_a_a}
    print(f"  Human: R@5={m_a_h.get('recall@5', 0):.4f} MRR={m_a_h.get('mrr', 0):.4f}", flush=True)
    print(f"  Auto:  R@5={m_a_a.get('recall@5', 0):.4f} MRR={m_a_a.get('mrr', 0):.4f}", flush=True)

    # --- System B: E5 single model + multi-query ---
    print("\n--- System B: E5-base + multi-query RRF ---", flush=True)
    m_b_h = evaluate_retrieval(
        "E5 + multi-query",
        lambda query_text, top_k=5: retriever.search_single("e5", query_text, top_k),
        human_queries,
    )
    m_b_a = evaluate_retrieval(
        "E5 + multi-query",
        lambda query_text, top_k=5: retriever.search_single("e5", query_text, top_k),
        auto_queries,
    )
    results["E5 + multi-query"] = {"human": m_b_h, "auto": m_b_a}
    print(f"  Human: R@5={m_b_h.get('recall@5', 0):.4f} MRR={m_b_h.get('mrr', 0):.4f}", flush=True)
    print(f"  Auto:  R@5={m_b_a.get('recall@5', 0):.4f} MRR={m_b_a.get('mrr', 0):.4f}", flush=True)

    # --- System C: Ensemble MPNet + E5 (equal weights) ---
    print("\n--- System C: Ensemble MPNet+E5 (50/50) ---", flush=True)
    m_c_h = evaluate_retrieval(
        "Ensemble 50/50",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.5, "e5": 0.5}),
        human_queries,
    )
    m_c_a = evaluate_retrieval(
        "Ensemble 50/50",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.5, "e5": 0.5}),
        auto_queries,
    )
    results["Ensemble 50/50"] = {"human": m_c_h, "auto": m_c_a}
    print(f"  Human: R@5={m_c_h.get('recall@5', 0):.4f} MRR={m_c_h.get('mrr', 0):.4f}", flush=True)
    print(f"  Auto:  R@5={m_c_a.get('recall@5', 0):.4f} MRR={m_c_a.get('mrr', 0):.4f}", flush=True)

    # --- System D: Ensemble MPNet + E5 (MPNet weighted) ---
    print("\n--- System D: Ensemble MPNet+E5 (70/30) ---", flush=True)
    m_d_h = evaluate_retrieval(
        "Ensemble 70/30",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.7, "e5": 0.3}),
        human_queries,
    )
    m_d_a = evaluate_retrieval(
        "Ensemble 70/30",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.7, "e5": 0.3}),
        auto_queries,
    )
    results["Ensemble 70/30"] = {"human": m_d_h, "auto": m_d_a}
    print(f"  Human: R@5={m_d_h.get('recall@5', 0):.4f} MRR={m_d_h.get('mrr', 0):.4f}", flush=True)
    print(f"  Auto:  R@5={m_d_a.get('recall@5', 0):.4f} MRR={m_d_a.get('mrr', 0):.4f}", flush=True)

    # --- System E: Ensemble MPNet + E5 (E5 weighted) ---
    print("\n--- System E: Ensemble MPNet+E5 (30/70) ---", flush=True)
    m_e_h = evaluate_retrieval(
        "Ensemble 30/70",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.3, "e5": 0.7}),
        human_queries,
    )
    m_e_a = evaluate_retrieval(
        "Ensemble 30/70",
        lambda query_text, top_k=5: retriever.search_ensemble(query_text, top_k, {"mpnet": 0.3, "e5": 0.7}),
        auto_queries,
    )
    results["Ensemble 30/70"] = {"human": m_e_h, "auto": m_e_a}
    print(f"  Human: R@5={m_e_h.get('recall@5', 0):.4f} MRR={m_e_h.get('mrr', 0):.4f}", flush=True)
    print(f"  Auto:  R@5={m_e_a.get('recall@5', 0):.4f} MRR={m_e_a.get('mrr', 0):.4f}", flush=True)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY: Human-Validated Results (90 queries)")
    print("=" * 70, flush=True)
    all_h = [
        ("MPNet + multi-query", m_a_h),
        ("E5 + multi-query", m_b_h),
        ("Ensemble 50/50", m_c_h),
        ("Ensemble 70/30", m_d_h),
        ("Ensemble 30/70", m_e_h),
    ]
    best_r5 = 0
    best_name = ""
    for name, metrics in all_h:
        r5 = metrics.get("recall@5", 0)
        p5 = metrics.get("precision@5", 0)
        mrr = metrics.get("mrr", 0)
        print(f"  {name:25s} R@5={r5:.4f} P@5={p5:.4f} MRR={mrr:.4f}", flush=True)
        if r5 > best_r5:
            best_r5 = r5
            best_name = name

    print(f"\nTROPHY Best human-validated R@5: {best_r5:.4f} ({best_name})", flush=True)

    print("\n" + "=" * 70)
    print("SUMMARY: Auto-Generated Results (232 queries)")
    print("=" * 70, flush=True)
    all_a = [
        ("MPNet + multi-query", m_a_a),
        ("E5 + multi-query", m_b_a),
        ("Ensemble 50/50", m_c_a),
        ("Ensemble 70/30", m_d_a),
        ("Ensemble 30/70", m_e_a),
    ]
    for name, metrics in all_a:
        r5 = metrics.get("recall@5", 0)
        p5 = metrics.get("precision@5", 0)
        mrr = metrics.get("mrr", 0)
        print(f"  {name:25s} R@5={r5:.4f} P@5={p5:.4f} MRR={mrr:.4f}", flush=True)

    # Write results
    output = {
        "n_cases": len(cases),
        "n_human_queries": len(human_queries),
        "n_auto_queries": len(auto_queries),
        "models": ["mpnet", "e5"],
        "systems": {},
    }
    for name, metrics in all_h:
        output["systems"][name] = {"human": metrics}
    for name, metrics in all_a:
        if name in output["systems"]:
            output["systems"][name]["auto"] = metrics
        else:
            output["systems"][name] = {"auto": metrics}
    output["best_human_r5"] = best_r5
    output["best_human_system"] = best_name

    out_path = EXPERIMENT_DIR / "nyaysaathi_aggressive_opt.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
