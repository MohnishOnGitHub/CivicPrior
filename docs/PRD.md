# CivicPrior — Product Requirements Document

**Hackathon:** Build with AI — Code for Communities, Second Edition  
**Problem Statement:** AI for Digital Public Infrastructure & Governance  
**Status:** Draft v0.1 — Team Review  
**Working Product Name:** CivicPrior  
**Core Differentiator:** Closed-loop policy intelligence: demand → allocation → trade-offs → measured impact

---

## 1. Executive Summary

CivicPrior is a multilingual public-infrastructure decision-support platform that converts fragmented citizen development requests into transparent, evidence-backed investment recommendations.

Rather than stopping at complaint collection or dashboarding, the product closes the loop between:

**citizen demand → public data → budget allocation → policy trade-offs → post-project impact measurement**

> Generative AI should understand citizen demand, but public money should be allocated through auditable data, constraints, and optimization — not an opaque LLM score.

---

## 2. Problem

Citizen infrastructure requests arrive through disconnected channels and languages, while policymakers must make funding decisions using incomplete, inconsistent, and often non-comparable evidence.

This creates three core failures:

1. Citizen demand is difficult to consolidate.
2. Infrastructure investments are difficult to prioritize transparently.
3. Completed projects are rarely evaluated against the original citizen need.

---

## 3. Product Vision

Create a Digital Public Good that gives policymakers a living view of citizen demand and infrastructure gaps, lets them simulate budget and equity trade-offs, and tracks whether funded projects actually improved outcomes.

---

## 4. Goals

- Aggregate multilingual citizen development requests from text, voice, and messaging-style inputs.
- Convert unstructured requests into structured, deduplicated demand signals linked to geography and infrastructure categories.
- Combine citizen demand with demographic, infrastructure, geospatial, and public-investment data.
- Generate auditable priority scores using documented factors rather than free-form LLM judgment.
- Optimize a portfolio of infrastructure projects under budget and fairness constraints.
- Let policymakers run counterfactual scenarios by changing budget, policy weights, or equity constraints.
- Explain who benefits, who remains underserved, and why each project was selected or rejected.
- Measure post-investment impact and compare predicted outcomes with actual outcomes.
- Support an interoperable/federated deployment model suitable for multiple regions or BRICS nations.

---

## 5. Non-Goals for Hackathon MVP

- Replacing elected officials or public administrators in final funding decisions.
- Building a production-scale national citizen identity system.
- Guaranteeing causal impact from observational data.
- Automating procurement, tendering, or fund disbursement.
- Building every messaging-channel integration.
- Training a foundation model from scratch.
- Supporting every infrastructure category in the first version.

---

## 6. Target Users

| User | Primary Need | MVP Experience |
|---|---|---|
| Citizen | Submit local development needs in a familiar language/channel | Text or voice request with automatic translation and categorization |
| District / municipal analyst | Understand concentrated demand and infrastructure gaps | Demand clusters, map, evidence drill-down |
| Policymaker / budget owner | Decide what to fund under limited budget | Scenario simulator and optimized project portfolio |
| Program evaluator | Know whether funded projects worked | Before/after impact view and predicted-vs-actual comparison |

---

## 7. Core User Journey

1. A citizen submits a development request by text or voice in a local language.
2. AI translates, extracts location/category/issue/urgency, and maps the request to a structured schema.
3. Semantically similar requests are clustered and duplicates/noise are reduced.
4. The system joins demand clusters with population, vulnerability, infrastructure-gap, geography, and planned-investment data.
5. Candidate infrastructure projects receive transparent need/impact scores.
6. A constrained optimizer selects the best project portfolio for the available budget.
7. The policymaker changes budget, equity weighting, or strategic priorities and compares scenarios.
8. The system explains selection trade-offs, including who benefits and who remains underserved.
9. After a project is completed, new feedback and service indicators are compared against the baseline to estimate observed impact.

---

## 8. MVP Feature Requirements

| Priority | Feature | Requirement |
|---|---|---|
| P0 | Multilingual citizen intake | Accept text and at least one voice input flow; produce English-normalized structured output while preserving original language |
| P0 | Request understanding | Extract category, subcategory, location, issue description, urgency class, and infrastructure need |
| P0 | Demand clustering | Group semantically similar requests by location/category and prevent obvious duplicate inflation |
| P0 | Evidence layer | Join demand with at least 3 public-data dimensions: population/demographics, infrastructure deficit, and existing/planned investment |
| P0 | Priority model | Compute 0–100 component scores and a transparent composite score |
| P0 | Budget optimizer | Select a project portfolio under a configurable budget and at least one fairness constraint |
| P0 | Counterfactual simulator | Re-run allocation when the user changes budget or policy/equity weights |
| P0 | Trade-off explanation | Show why selected projects beat alternatives and identify underserved groups left behind |
| P1 | Geospatial dashboard | Visualize demand hotspots and proposed projects on a map |
| P1 | Impact tracking | Show baseline vs post-project indicators and predicted vs observed impact for sample completed projects |
| P1 | Audit log | Record scenario parameters, selected projects, score components, and timestamp |
| P2 | Federated model exchange demo | Demonstrate a schema/API for sharing model updates or aggregate learnings without sharing raw citizen data |

---

## 9. Priority / Impact Model

Initial hackathon weights are configurable defaults, not claims of scientific optimality.

| Factor | Default Weight | Example Evidence |
|---|---:|---|
| Citizen demand | 30% | Unique requests per capita, persistence over time, cluster size |
| Infrastructure deficit | 20% | Coverage/access gap for water, roads, healthcare, etc. |
| Population affected | 20% | Estimated residents materially benefiting |
| Equity / vulnerability | 15% | Remoteness, deprivation, service-access disadvantage |
| Urgency | 10% | Rules mapped from issue class and severity |
| Policy / investment gap | 5% | Existing approved plans, duplicate planned investments, funding gap |

Default composite score:

`0.30*demand + 0.20*deficit + 0.20*population + 0.15*equity + 0.10*urgency + 0.05*investment_gap`

The composite score estimates project value, while the optimizer chooses the best combination of projects under budget and policy constraints.

The LLM may extract and explain evidence, but it must not directly decide the final funding allocation.

---

## 10. Counterfactual Policy Simulator

The policymaker can:

- Change total budget, e.g. ₹100Cr → ₹60Cr.
- Increase or decrease equity weighting.
- Prioritize a policy objective such as rural access, water security, or climate resilience.
- Add a minimum-spend constraint for underserved areas.
- Compare Scenario A vs B vs C on total citizens reached, demand addressed, equity coverage, and remaining unserved need.
- See which projects entered or left the portfolio and why.

---

## 11. Explainability & Responsible AI

- Every project recommendation must expose component scores, source evidence, budget cost, and active constraints.
- AI-generated explanations must be grounded in optimizer output and evidence.
- The UI must distinguish observed facts, model estimates, and simulated outcomes.
- Policymakers remain final decision-makers; the platform is decision support, not autonomous governance.
- Use aggregate demographic indicators for equity analysis.
- Avoid individual-level sensitive profiling.
- Keep changes to scenario weights and assumptions auditable.

---

## 12. Success Metrics for Hackathon Demo

| Metric | Target |
|---|---|
| Structured request extraction | ≥90% correct on a curated multilingual demo set |
| Duplicate/cluster quality | Similar requests visibly grouped; obvious duplicates do not inflate demand |
| Scenario responsiveness | Budget/weight change recomputes portfolio within a few seconds |
| Explainability | 100% of selected projects show score breakdown + selection rationale |
| Trade-off visibility | Every scenario identifies unserved/losing demand where applicable |
| Impact loop | At least 2 sample completed projects show baseline, observed outcome, and predicted-vs-actual comparison |
| Demo integrity | Core flow works end-to-end with minimal hard-coded decision logic |

---

## 13. Demo Narrative

1. Submit multilingual citizen requests from several neighborhoods.
2. Show AI normalization and demand clustering.
3. Open the policy map and identify a high-demand / low-infrastructure hotspot.
4. Set a ₹100Cr budget and generate an optimized project portfolio.
5. Reduce the budget to ₹60Cr and show which projects drop.
6. Increase equity preference and show an underserved-region project entering the portfolio.
7. Open a rejected project and show the explicit trade-off explanation.
8. Open the impact tab for a completed project and compare predicted vs observed improvement.

---

## 14. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Scope becomes too large | Protect the P0 closed-loop flow before voice, federation, or polish |
| Priority score feels arbitrary | Expose weights, use public-data evidence, allow sensitivity analysis |
| LLM hallucination | Use structured outputs, validation, grounded retrieval, deterministic scoring |
| Poor or sparse public data | Use a curated demo geography and label synthetic fields clearly |
| Optimizer produces unintuitive choices | Test with small manual scenarios before UI development |
| Project becomes just another dashboard | Make the interactive policy simulator the center of the demo |

---

## 15. MVP Definition of Done

> A judge can submit citizen demand, see it become structured evidence, generate a constrained infrastructure portfolio, change budget/equity assumptions, understand the trade-offs, and inspect an example of measured post-investment impact — all in one working flow.

---

## 16. Open Product Decisions

- Demo geography.
- First 2–3 infrastructure categories.
- Public datasets to use.
- How project cost estimates are sourced.
- Whether equity is a weight, a hard constraint, or both.
- How much of impact tracking uses live versus seeded demo data.
