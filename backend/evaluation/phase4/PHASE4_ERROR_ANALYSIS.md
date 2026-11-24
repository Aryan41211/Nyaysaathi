# PHASE 4 — NyayaSaathi Error Analysis

**Project:** NyayaSaathi — Legal Information Retrieval System  
**Phase:** 4 — Benchmark Breakthrough  
**Date:** 2026-11-25  
**Git SHA:** e67c41b

---

## 1. Hard-Negative Analysis

Hard negatives are documents that are semantically similar but legally irrelevant — cases that retrieval systems incorrectly rank highly.

### 1.1 Hard-Negative Categories

| Hard-Negative Type | Example Query | Incorrectly Retrieved Case | Why It's a Hard Negative |
|-------------------|---------------|---------------------------|--------------------------|
| Same category, different subcategory | "Land boundary dispute" | "Land acquisition by government" | Both about land, but different legal procedures |
| Same category, different subcategory | "Salary non-payment" | "Wrongful termination" | Both employment-related, but different remedies |
| Semantic overlap, different domain | "Cyber fraud UPI" | "Consumer complaint - defective product" | Both involve financial loss, different laws |
| Similar procedure, different context | "Police FIR refusal" | "Consumer - platform refusing refund" | Both involve complaining to authority, different forums |

### 1.2 Why Hard Negatives Occur

1. **Embedding models capture semantic similarity, not legal relevance** — Two cases about "land" are close in embedding space even if one is about boundaries and the other about acquisition
2. **Category-proxy labels mask the problem** — With same-subcategory labels, hard negatives within the same category are not penalized
3. **Small corpus limits discrimination** — With only ~23 cases per category, there are few truly irrelevant cases to push down

### 1.3 Impact on Metrics

| Metric | Impact of Hard Negatives |
|--------|-------------------------|
| Recall@5 | Inflated — many same-subcategory cases satisfy the label |
| Precision@5 | Deflated — hard negatives occupy top slots |
| nDCG@5 | Partially mitigated — graded relevance would penalize hard negatives |
| MRR | Inflated — first relevant case is usually same-subcategory |

---

## 2. Error Patterns by Model

### 2.1 BM25

**Failure mode:** Keyword-only matching misses semantic equivalents.
- Query: "employer not paying salary" → may miss case with "wages withheld" (different keywords)
- Query: "land encroachment by neighbour" → may miss case with "boundary violation" (different keywords)

**Strength:** Fast (0.70ms p50), no model loading required.

### 2.2 Dense Models (MiniLM, MPNet, E5, BGE)

**Failure mode:** Semantic similarity ≠ legal relevance.
- Query: "divorce under Hindu Marriage Act" → may retrieve "domestic violence case" (related but different law)
- Query: "consumer complaint defective product" → may retrieve "service deficiency telecom" (both consumer, different remedy)

**Strength:** Better semantic matching than BM25, but slower (5-10ms p50).

### 2.3 Query Normalization

**Finding:** No statistically significant impact on auto-generated labels.
- Hinglish terms (e.g., "talaq" → "divorce") help when users use code-mixed language
- But on English-only auto-generated queries, normalization is a no-op
- Would likely help on real user queries in Hindi/Marathi/Hinglish

---

## 3. What Would Change with Human-Validated Labels

With genuine human relevance judgments:

| Metric | Expected Change | Reason |
|--------|----------------|--------|
| Recall@5 | Significant decrease | Hard negatives no longer count as "relevant" |
| Precision@5 | Significant decrease | More non-relevant cases in top 5 |
| nDCG@5 | More discriminative | Graded relevance distinguishes partial from full relevance |
| MRR | Decrease | First truly relevant case may be ranked lower |

The gap between BM25 and dense models would likely widen on human-validated data, as dense models better capture semantic legal relevance.

---

## 4. Reproduction

```bash
cd C:\projects\NyaySaathi\scripts\phase4
python retrieval_evaluation.py
```

Results saved to `backend/evaluation/phase4/retrieval_results.json`.

Error analysis is qualitative — based on manual inspection of retrieved results across models.
