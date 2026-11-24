# OPTIMIZATION_STRATEGY.md — NyaySaathi

**Project:** NyaySaathi — NLP Legal Intelligence Platform  
**Strategy date:** 2026-11-24  
**Priority order:** Corpus > Evaluation > Retrieval Engine > Performance

## Priority 1: Corpus Engineering (Phase A1)

**Current state:** 201 cases, 10 categories, no provenance tracking  
**Goal:** Expand corpus with legally accessible Indian legal documents where feasible  
**Constraint:** Do not violate access restrictions or licensing conditions; 10K+ is aspirational

### Planned actions:
1. Audit existing dataset structure and metadata completeness
2. Document corpus provenance and licensing
3. Implement deduplication detection
4. Add document classification metadata
5. Expand corpus with legally accessible sources where permitted
6. Build incremental indexing pipeline

### Success criteria:
- Corpus count is reproducible and documented
- Each document has provenance metadata (source, URL, extraction status)
- Duplicate detection is implemented
- Corpus expansion only where legally permissible

## Priority 2: Human-Validated Evaluation (Phase A3)

**Current state:** 201 auto-generated queries with category-based proxy labels  
**Goal:** Human-reviewed evaluation dataset with explicit relevance judgments  
**Constraint:** Cannot invent human labels; must create annotation workflow

### Planned actions:
1. Audit MRR implementation (suspicious 1.000 result)
2. Create annotation workflow and guidelines
3. Build human-validated dataset (50-100 diverse queries)
4. Separate train/dev/test splits to prevent leakage
5. Measure Recall@1/3/5/10, Precision@5, MRR, nDCG@5, Hit Rate

### Success criteria:
- Human-validated labels are clearly distinguished from auto-generated
- No test-set leakage
- MRR implementation is verified correct
- Evaluation is reproducible

## Priority 3: Retrieval Engine Improvements (Phase A2)

**Current state:** TF-IDF, BM25, Dense MiniLM+FAISS, Hybrid RRF  
**Goal:** Improve ranking quality through measured experiments  
**Constraint:** Do not introduce techniques without ablation evidence

### Planned actions:
1. Investigate why Hybrid RRF (0.183) < Dense (0.202) on Recall@5
2. Tune BM25 parameters (k1, b)
3. Evaluate embedding normalization and similarity metric
4. Test cross-encoder reranking on top candidates
5. Test weighted fusion vs RRF
6. Evaluate query expansion and legal terminology normalization

### Success criteria:
- Each technique tested in isolation via ablation
- Best architecture selected based on actual results
- No complexity added without measurable improvement

## Priority 4: Performance Engineering (Phase A5)

**Current state:** Unknown p95 latency, no memory profiling  
**Goal:** Reduce latency while preserving relevance  
**Constraint:** No optimization that damages retrieval quality

### Planned actions:
1. Measure cold-start and warm retrieval latency (p50/p95/p99)
2. Profile embedding generation time
3. Evaluate FAISS index configuration
4. Implement embedding caching
5. Measure QPS and memory usage

## Experiment Tracking

All experiments recorded per Section 8 of the master prompt:
- Experiment ID, hypothesis, baseline, configuration, dataset version, random seed, hardware, metrics, result, regression status

## Acceptance Criteria

- Larger verified corpus where feasible
- Reproducible ingestion
- Human-reviewed evaluation
- Correct metric implementations
- Comparative retrieval experiments
- Measured latency
- Regression tests
- Document provenance
