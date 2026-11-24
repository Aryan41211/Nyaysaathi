"""Summarize NyayaSaathi Phase 4 retrieval results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

RESULTS_PATH = Path(__file__).resolve().parent.parent.parent / "backend" / "evaluation" / "phase4" / "retrieval_results.json"


def main() -> int:
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        r = json.load(f)

    print(f"Label source: {r['label_source']}")
    print(f"N queries: {r['n_eval_queries']}")
    print(f"N cases: {r['n_deduped_cases']}")
    print()

    # Model comparison CSV
    print("Model,LabelSource,Recall@1,Precision@1,Recall@3,Precision@3,Recall@5,Precision@5,Recall@10,Precision@10,MRR,MAP,nDCG@5,nDCG@10,p50_ms,p95_ms,p99_ms")
    for name, exp in r["experiments"].items():
        m = exp["metrics"]
        lat = exp["latency_ms"]
        print(
            f'{name},{r["label_source"]},'
            f'{m.get("recall@1", 0):.4f},{m.get("precision@1", 0):.4f},'
            f'{m.get("recall@3", 0):.4f},{m.get("precision@3", 0):.4f},'
            f'{m.get("recall@5", 0):.4f},{m.get("precision@5", 0):.4f},'
            f'{m.get("recall@10", 0):.4f},{m.get("precision@10", 0):.4f},'
            f'{m.get("mrr", 0):.4f},{m.get("map", 0):.4f},'
            f'{m.get("ndcg@5", 0):.4f},{m.get("ndcg@10", 0):.4f},'
            f'{lat["p50_ms"]},{lat["p95_ms"]},{lat["p99_ms"]}'
        )
    print()

    # Per-query stats
    print("Per-query summary:")
    for name, exp in r["experiments"].items():
        m = exp["metrics"]
        lat = exp["latency_ms"]
        r5 = m.get("recall@5", 0)
        r5_lo = m.get("recall@5_ci_lo", 0)
        r5_hi = m.get("recall@5_ci_hi", 0)
        print(
            f"  {name:<35s} R@5={r5:.4f} "
            f"CI=[{r5_lo:.4f}, {r5_hi:.4f}] "
            f"P@5={m.get('precision@5', 0):.4f} "
            f"MRR={m.get('mrr', 0):.4f} "
            f"nDCG@5={m.get('ndcg@5', 0):.4f} "
            f"MAP={m.get('map', 0):.4f} "
            f"p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())