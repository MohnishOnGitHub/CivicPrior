# CivicPrior

**AI understands citizen demand; evidence quantifies need; optimization allocates the budget; AI explains the result.**

CivicPrior is a decision-support prototype for public infrastructure allocation. It turns multilingual citizen complaints into structured demand, joins that demand to evidence, scores need and expected impact, and selects a budget-constrained portfolio under optional equity rules.

This repository is a hackathon demonstration. All locations, requests, and outcome numbers are **synthetic**.

---

## Hackathon challenge

**Build with AI — Code for Communities, Second Edition**  
**Problem statement:** AI for Digital Public Infrastructure & Governance

CivicPrior is submitted as an interoperable Digital Public Good architecture: a shared schema and allocation interface, with country adapters that keep raw citizen data local.

---

## Problem statement

Citizen infrastructure requests arrive in different languages and channels. Policymakers still have to choose a small set of projects under a fixed budget. Typical civic tools stop at classification and a dashboard. They do not say which mix of projects to fund, what equity constraint costs in aggregate impact, or whether a completed project beat its prediction.

---

## CivicPrior solution

CivicPrior closes that loop:

1. Understand the complaint (Gemini, server-side).
2. Cluster demand and join public-style evidence.
3. Score **need** and **expected impact** with a documented formula.
4. Optimize a portfolio under budget and optional underserved-impact floors.
5. Compare policy scenarios and inspect predicted vs observed outcomes.

The language model does **not** allocate money.

---

## What differentiates CivicPrior

**Typical civic complaint platform**

`complaint → AI classification → dashboard`

**CivicPrior**

`complaint → evidence → need → expected impact → constrained portfolio → policy trade-offs → measured outcome`

| Typical platform | CivicPrior |
|---|---|
| Classifies a ticket | Structures demand, then scores need from evidence |
| Lists complaints | Selects a feasible portfolio under ₹ budget |
| Rarely shows equity cost | Compares maximum-impact vs underserved-impact floors |
| Stops at submission | Tracks baseline / predicted / observed indicators |

---

## Core architecture

```
Citizen text
    → Gemini structured intake (server-only API key)
    → Demand clusters (geo + category + intervention)
    → Evidence join (deficit, equity, investment gap)
    → need_score + expected_impact
    → Optimizer (knapsack on expected impact)
    → Frozen JSON export
    → Policymaker dashboard (simulator, map, impact, DPG view)
```

Python owns scoring and allocation. The Next.js app displays exported results and runs Gemini only for intake.

---

## Decision model

Formulas live in `src/scoring.py` and `src/optimizer.py`. They are frozen for this MVP.

**Need score** (no `population_affected`):

`0.30·citizen_demand + 0.25·infrastructure_deficit + 0.20·equity + 0.15·urgency + 0.10·investment_gap`

**Expected impact**

`beneficiaries × (need_score / 100) × (expected_improvement_pct / 100)`

**Budget optimization**

Brute-force knapsack. Maximize sum of `expected_impact` subject to `cost_cr ≤ budget`.

**Equity scenarios**

Optional `min_underserved_impact_share` (25% / 30% / 40%). Underserved projects are those at or above the 75th percentile of derived equity. If a constraint is infeasible, CivicPrior reports why; it does not silently relax the rule.

---

## Citizen intelligence pipeline

- Schema: `frontend/lib/intakeSchema.ts` and `src/requests/schema.py`
- Categories: `water`, `healthcare`, `roads`
- Languages in the demo: English, Hindi, Telugu
- Route: `POST /api/intake/extract`
- Gemini (`gemini-3.6-flash`) runs only on the server
- `frontend/lib/mockExtract.ts` is the fallback when the key is missing or the model fails
- Complaints are **not** persisted

---

## Evidence enrichment

`src/evidence/enrichment.py` joins citizen clusters to synthetic geo profiles, infrastructure metrics, and investment plans. Derived project inputs are written to `data/derived-project-inputs.json`. Seed project scores in `data/seed-projects.json` are not retuned from dashboard results.

---

## Policy simulator

The dashboard reads `frontend/public/data/dashboard-v01.json`. Changing budget or equity mode selects a **precomputed** scenario. The browser does not rerun the optimizer.

Primary demo envelope: **₹60 Cr**.

- Maximum impact vs 30% underserved-impact share
- Comparison view shows who entered, who left, and percent aggregate impact sacrificed
- Numbers always come from the export, not from hardcoded React constants

---

## Geospatial view

A schematic synthetic district (not official administrative coordinates). Markers show demand, deficit, equity, expected impact, and selected / rejected status for the current scenario. Google Maps is not enabled (it would need a new API key and billing).

---

## Impact tracking

Sample completed projects **P001** (Ward 17 water) and **P003** (Rural PHC Expansion) show baseline, predicted, and observed indicators. All values are synthetic. The comparison does not prove causality.

---

## BRICS / DPG interoperability

Dashboard section: **BRICS / Digital Public Good**.

- **Shared layer:** citizen-request schema, infrastructure taxonomy, API contract, versioned scoring / optimization interfaces, aggregate / model exchange format
- **Jurisdiction layer:** local submissions, languages, datasets, policy weights, privacy rules
- **Privacy rule:** raw citizen data stays local; the shared layer may exchange schemas, aggregates, and optionally model updates
- **Illustrative adapters only:** India, Brazil, South Africa — no live government systems

---

## Google / AI technologies used

| Use | Technology |
|---|---|
| Citizen intake extraction | Gemini API (`gemini-3.6-flash`), server-side only |
| Structured JSON | Gemini `responseSchema` + CivicPrior validation |
| Maps / Earth Engine / Firebase | **Not used** |

Allocation is deterministic Python. Gemini is not in the scoring or optimizer path.

---

## Synthetic-data disclaimer

Every request, geography, coordinate, project, scenario, and impact observation in this repo is **synthetic demonstration data**. It is not official government statistics and must not be treated as a real district.

---

## How to run the Python pipeline

From the repository root:

```bash
python3 src/requests/clustering.py
python3 src/evidence/enrichment.py
python3 src/pipeline/compare_decision_models.py
python3 src/pipeline/export_dashboard.py
```

`export_dashboard.py` writes `data/dashboard-v01.json` and copies it to `frontend/public/data/dashboard-v01.json`.

Do not edit portfolio results by hand in React.

---

## How to run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

Production check:

```bash
cd frontend
npm run build
```

---

## GEMINI_API_KEY setup

1. Copy `frontend/.env.example` to `frontend/.env.local`
2. Set:

```
GEMINI_API_KEY=your_key_here
```

3. Restart `npm run dev`

If the key is missing or Gemini fails, intake uses the mock extractor and returns `extraction_mode: "mock_fallback"`.

---

## Security note: never commit `.env.local`

- `GEMINI_API_KEY` is read only as `process.env.GEMINI_API_KEY` in server code
- The browser calls `/api/intake/extract` and never sees the key
- Root `.gitignore` and `frontend/.gitignore` ignore `.env`, `.env.local`, and `.env*.local`
- Do not commit `.env.local` or any file that contains the key

---

## Current limitations

- No persistence of submitted complaints
- No authentication, database, or Firebase
- No voice intake in this build
- No live government data adapters
- Geospatial view is a synthetic schematic, not official GIS
- Impact samples are two synthetic completed projects
- Optimizer is brute-force knapsack on a 12-project catalog
- Equity “underserved” uses the derived 75th-percentile rule, not a live census

---

## Future work

- Additional country adapters behind the same schema
- Optional model / aggregate exchange without moving raw records
- Voice intake
- Broader infrastructure categories
- Official GIS / Earth Engine only with explicit data-sharing rules
- Audit log of scenario parameters
- More completed-project outcome samples
