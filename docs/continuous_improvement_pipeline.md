# NyaySaathi Continuous Improvement Pipeline

## 1) Dataset Design

Primary schema file:
- dataset/training_dataset_schema_multilingual.json

Languages covered:
- hinglish
- hi (Hindi)
- mr (Marathi)

Each record includes:
- query and normalized_query
- intent_label
- expected output contract (decision, workflow_steps, required_documents, where_to_go)
- source metadata (seed, synthetic, production_feedback)

## 2) Synthetic Data Generation

Script:
- backend/scripts/generate_synthetic_training_data.py

What it generates:
- Hinglish spelling variants (`kaise`, `kese`, `kaisey`)
- Slang rewrites (`ignore kar raha` -> `bhaav nahi de raha`)
- Misspellings (`salary` -> `salery`, `sallary`)

Output:
- dataset/synthetic_multilingual_training.json

## 3) Feedback and Training Data Logging

Production collections:
- `training_events`: query + model decision row
- `training_feedback`: user correction and helpfulness row

Stored fields include:
- raw/normalized query
- detected intent and confidence
- answer/fallback decision
- system response and workflow steps
- user correction text and corrected intent/language

Write paths:
- search flow logs training event
- classify flow logs training event
- feedback API stores correction payload

## 4) Retraining Strategy

Script:
- backend/scripts/run_improvement_loop.py

Decision thresholds (env-configurable):
- retrain embeddings when:
  - event volume >= `RETRAIN_MIN_EVENTS` and
  - fallback_rate >= `RETRAIN_FALLBACK_RATE` OR low_confidence_rate >= `RETRAIN_LOW_CONF_RATE`
- update intents when corrected feedback ratio >= `INTENT_UPDATE_ERROR_RATE`
- update synonyms when correction-token frequency >= `SYNONYM_MIN_OCCURRENCES`

Output report:
- backend/data/improvement_reports/latest_improvement_report.json

## 5) Operational Cadence

Daily:
- generate improvement report
- inspect top corrected intents and synonym candidates

Weekly:
- approve synonym updates in query normalization maps
- add high-quality corrected queries to intent exemplars

Bi-weekly or trigger-based:
- regenerate embeddings/index when retrain condition is true
- run regression tests on multilingual intent accuracy before deployment
