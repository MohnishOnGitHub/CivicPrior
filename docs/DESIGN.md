# CivicPrior — Technical Design Document

**Hackathon:** Build with AI — Code for Communities, Second Edition  
**Problem Statement:** AI for Digital Public Infrastructure & Governance  
**Status:** Draft v0.1 — Team Review  
**Working Product Name:** CivicPrior

---

## 1. Design Overview

CivicPrior separates generative-AI tasks from policy-allocation logic.

Gemini handles:

- multilingual understanding
- translation
- structured extraction
- summarization
- grounded explanation

Deterministic services handle:

- evidence scoring
- policy constraints
- project portfolio optimization
- scenario comparison

> AI understands the request; evidence scores quantify need; optimization allocates the budget; AI explains the result.

This makes the system auditable and avoids using an LLM as the authority for public-budget allocation.

---

## 2. High-Level Architecture

```text
Citizen Channels
      ↓
Ingestion API
      ↓
Gemini / Speech-to-Text
      ↓
Structured Request Store
      ↓
Semantic Clustering & Deduplication
      ↓
Evidence Enrichment Layer
  ├─ Demographics
  ├─ Infrastructure indices
  ├─ Geospatial/access indicators
  └─ Existing/public investment plans
      ↓
Candidate Project Generator
      ↓
Priority Scoring Service
      ↓
Portfolio Optimizer
      ↓
Scenario / Counterfactual Service
      ↓
Policy Dashboard + Map
      ↓
Grounded Explanation Service
      ↓
Impact Measurement / Feedback Loop
```

---

## 3. Proposed Technology Stack

| Layer | Proposed Technology | Reason |
|---|---|---|
| Frontend | React / Next.js | Fast dashboard prototyping and scenario UI |
| Authentication | Firebase Auth | Hackathon-friendly auth and role separation |
| Primary app data | Firestore or PostgreSQL | Requests, projects, scenarios, audit records |
| Analytics / public datasets | BigQuery | Large structured datasets and aggregations |
| AI | Gemini API / Vertex AI | Multilingual extraction, summarization, grounded explanations |
| Voice | Google Cloud Speech-to-Text | Citizen voice input |
| Embeddings | Vertex AI text embeddings | Semantic clustering / similarity |
| Geospatial | Google Maps Platform; optional Earth Engine | Hotspots, access metrics, geospatial overlays |
| Optimization | OR-Tools or equivalent | Budget-constrained portfolio optimization |
| Backend | Cloud Run / Functions | Stateless APIs and event-driven jobs |
| Observability | Cloud Logging + simple metrics | Trace extraction, scoring, optimizer runs |

---

## 4. Core Data Model

### CitizenRequest

```text
id
original_text
audio_ref
normalized_text
language
category
subcategory
geo_id
urgency_class
submitted_at
cluster_id
```

### DemandCluster

```text
id
category
geo_id
request_count
unique_requester_count
requests_per_capita
first_seen
last_seen
summary_embedding
```

### GeoProfile

```text
geo_id
population
vulnerability_index
remoteness
service_access_metrics
demographic_aggregates
```

### InfrastructureMetric

```text
geo_id
category
coverage
service_level
deficit_score
source
observed_at
```

### InvestmentPlan

```text
id
geo_id
category
amount
status
start_date
funding_source
```

### CandidateProject

```text
id
geo_id
category
name
estimated_cost
estimated_beneficiaries
evidence_refs
component_scores
composite_score
```

### Scenario

```text
id
budget
weights
fairness_constraints
policy_objective
created_by
created_at
```

### ScenarioResult

```text
scenario_id
selected_project_ids
unselected_project_ids
objective_value
citizens_reached
demand_covered
equity_metrics
```

### ImpactObservation

```text
project_id
metric_name
baseline
predicted_value
observed_value
observed_at
```

---

## 5. Citizen Request Processing Pipeline

1. Receive text or audio input plus optional coarse location.
2. If audio, transcribe using Speech-to-Text.
3. Detect language and preserve original content.
4. Call Gemini using a strict structured-output schema.
5. Validate category, location, and urgency against allowed enums/rules.
6. Generate an embedding for normalized request text.
7. Find nearest compatible demand clusters by geography/category.
8. Attach to an existing cluster if similarity and rule thresholds pass.
9. Otherwise create a new cluster.
10. Update aggregate demand metrics asynchronously.

Suggested extraction schema:

```json
{
  "language": "hi",
  "normalized_english": "Water supply is available only twice a week.",
  "category": "WATER",
  "subcategory": "SUPPLY_RELIABILITY",
  "location_text": "Village X",
  "geo_id": "geo_001",
  "urgency_class": "HIGH",
  "requested_intervention": "WATER_DISTRIBUTION_UPGRADE",
  "confidence": 0.93
}
```

---

## 6. Demand Scoring

Scores are normalized to 0–100.

Default weighting:

```text
Citizen demand          30%
Infrastructure deficit  20%
Population affected     20%
Equity / vulnerability  15%
Urgency                 10%
Investment gap           5%
```

Default composite:

```text
0.30*demand
+ 0.20*deficit
+ 0.20*population
+ 0.15*equity
+ 0.10*urgency
+ 0.05*investment_gap
```

### Component definitions

**Citizen demand**

Blend of unique requests per capita, persistence over time, and cluster size. Use caps/normalization so a single very large cluster does not dominate.

**Infrastructure deficit**

Normalize the observed service gap against a target or regional benchmark.

**Population affected**

Use percentile or log normalization so mega-cities do not automatically dominate rural regions.

**Equity / vulnerability**

Use aggregate geographic-level signals such as remoteness, deprivation, and service-access disadvantage.

**Urgency**

Use deterministic mappings from validated issue types and severity classes.

**Investment gap**

Higher when severe demand has no approved project; lower when equivalent investment is already planned.

---

## 7. Candidate Project Generation

For the hackathon MVP, candidate projects should come from a curated intervention catalog instead of asking Gemini to invent arbitrary public works.

Example mapping:

```text
Demand:
WATER + SUPPLY_RELIABILITY

Possible interventions:
- Distribution network upgrade
- Storage expansion
- Pumping-system improvement
```

Gemini can summarize evidence, describe the project, and explain why it matches the demand. Cost and beneficiary estimates should come from the project catalog or clearly labeled synthetic assumptions.

---

## 8. Portfolio Optimization

Decision variable:

```text
x_i ∈ {0,1}
```

where `x_i = 1` means project `i` is funded.

### Objective

```text
Maximize Σ x_i × ImpactScore_i
```

### Core constraint

```text
Σ x_i × Cost_i ≤ Budget
```

### Optional constraints

- Minimum percentage of spending in underserved geographies.
- Minimum coverage for critical categories such as water or healthcare access.
- Prevent duplicate or mutually exclusive interventions in the same area.
- Geographic-spread constraint.
- Do not select a project that duplicates an already-approved equivalent project.

For v0.1, `ImpactScore` can be the weighted composite score multiplied by a bounded beneficiary factor.

---

## 9. Counterfactual / Scenario Engine

A `Scenario` is an immutable set of parameters.

Changing any parameter creates a new scenario and triggers scoring + optimization.

| Parameter | Example |
|---|---|
| Budget | ₹50Cr, ₹60Cr, ₹100Cr |
| Weights | Increase equity from 15% → 30% |
| Fairness constraint | ≥20% of spend in underserved regions |
| Policy focus | Water security / rural access / climate resilience |
| Critical coverage | Fund at least one high-urgency water project if feasible |

Scenario comparison should calculate:

- projects added
- projects removed
- total beneficiaries
- demand coverage
- equity changes
- remaining unserved need

---

## 10. Trade-Off & Explanation Engine

Explanations run only after the optimizer finishes.

The explanation prompt receives selected projects, rejected projects, component scores, source evidence, active constraints, and scenario differences.

Questions the system should answer:

- Why was this project selected?
- Why was another project rejected?
- Which constraint changed the outcome?
- Who benefits?
- Who remains underserved?
- What changed between Scenario A and Scenario B?
- Which values are observed facts, model estimates, or simulations?

Critical explanation fields should be deterministic where possible; Gemini can produce the human-readable narrative.

---

## 11. Impact Measurement Loop

Each funded project stores baseline indicators at approval time.

After completion, new observations are compared with baseline, predicted outcome, and observed outcome.

| Metric | Baseline | Predicted | Observed |
|---|---:|---:|---:|
| Water complaints / month | 221 | 70 | 47 |
| Average daily water availability | 3.1 hrs | 7.5 hrs | 8.7 hrs |
| Population with adequate access | 41% | 68% | 71% |

The MVP compares predicted and observed changes but should not claim causal proof.

---

## 12. Suggested API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/v1/requests` | Submit citizen request |
| GET | `/v1/demand/clusters` | Query aggregated demand |
| GET | `/v1/geographies/{id}/evidence` | Fetch evidence for a region |
| POST | `/v1/projects/generate` | Generate candidates from validated demand |
| POST | `/v1/scenarios` | Create scenario |
| POST | `/v1/scenarios/{id}/run` | Run scoring + optimizer |
| GET | `/v1/scenarios/{id}/results` | Return selected portfolio and metrics |
| POST | `/v1/scenarios/compare` | Compare scenarios |
| GET | `/v1/projects/{id}/explanation` | Return grounded selection/rejection explanation |
| POST | `/v1/projects/{id}/impact` | Add post-project observations |

---

## 13. Interoperability / Federated BRICS Design

The hackathon MVP should demonstrate the architecture rather than implement full federated learning.

Each country or region:

- keeps raw citizen data locally
- maps local categories to a common taxonomy
- exposes normalized aggregate data
- can use jurisdiction-specific policy weights
- may share model updates or aggregate learnings where permitted

### Shared layer

- Common request taxonomy
- Common API contract
- Versioned schema
- Versioned scoring policy
- Aggregate model/update exchange

### Local layer

- Raw citizen submissions
- Local-language processing
- Jurisdiction-specific datasets
- Local privacy requirements
- Local policy constraints

---

## 14. Security, Privacy & Governance

- Minimize personally identifiable information.
- Pseudonymize requester identifiers.
- Use role-based access.
- Separate raw audio from normalized analytics records where practical.
- Log model version, prompt/schema version, scenario weights, and optimizer constraints.
- Avoid individual-sensitive demographic attributes in ranking.
- Make simulated outcomes visibly different from guaranteed outcomes.
- Keep human policymakers in the decision loop.

---

## 15. Failure Modes & Fallbacks

| Failure | Fallback |
|---|---|
| Gemini extraction confidence is low | Flag for review; do not auto-score |
| Location cannot be resolved | Keep unassigned and request coarse locality/pin |
| Public data is unavailable | Mark component missing or use clearly labeled synthetic demo data |
| No feasible portfolio exists | Return infeasibility reason and identify blocking constraint |
| Explanation conflicts with optimizer output | Use deterministic template for critical fields |
| Clustering fails | Fall back to category + geography grouping |

---

## 16. Implementation Plan

### Phase 0 — Validate the model

- Create 10–20 synthetic candidate projects.
- Implement score formula.
- Test ₹50Cr / ₹100Cr scenarios manually.
- Verify the optimizer makes sensible choices.

### Phase 1 — Core decision engine

- Schemas
- Seed dataset
- Scoring service
- Scenario engine
- OR-Tools optimization

### Phase 2 — AI intake

- Multilingual structured extraction
- Embeddings
- Clustering / deduplication

### Phase 3 — Dashboard

- Demand map
- Project portfolio
- Scenario controls
- Score breakdowns

### Phase 4 — Differentiators

- Scenario comparison
- “Who loses?” trade-off view
- Impact measurement

### Phase 5 — Polish

- Voice flow
- Audit log
- Federated architecture demo
- Error handling
- Demo performance

---

## 17. Test Strategy

- Golden multilingual request dataset for extraction accuracy.
- Cluster tests for duplicates, paraphrases, unrelated requests, and geography differences.
- Deterministic unit tests for every score component.
- Optimizer tests for budget, fairness, duplicate-project, and infeasible scenarios.
- Regression tests for scenario changes.
- Explanation grounding tests.
- End-to-end demo test using a fixed seed dataset.

---

## 18. Open Questions for Team Review

- Which geography should the demo use?
- Which 2–3 infrastructure categories should be supported first?
- Which public datasets can be used directly?
- Which fields must remain synthetic for the demo?
- Should equity be a weighted score, hard constraint, or both?
- How should project costs be sourced?
- Should we use OR-Tools or a simpler optimization approach first?
- How much impact measurement should be live versus seeded?

---

## 19. Technical Definition of Done

> Given a fixed demo dataset and citizen-request stream, the system deterministically produces candidate projects, scores them, selects a feasible portfolio under configurable budget/fairness constraints, explains the trade-offs using grounded evidence, and re-runs correctly when scenario parameters change.

---

## 20. First Engineering Milestone

Before frontend, Gemini, Firebase, or Maps:

> Given 10 synthetic infrastructure projects and a ₹50Cr budget, return the optimal project portfolio with transparent scores and at least one fairness constraint.

If this works convincingly, the core technical idea is validated.
