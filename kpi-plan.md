## KPI & Measurement Plan – AI Scope Extraction Assistant

### 1. Overview
This plan converts the charter KPIs into measurable metrics with ownership, data sources, and cadence. Metrics are grouped by outcome tier for executive visibility.

### 2. KPI Tree
- **Business Outcomes**
  - **BO1:** Reduce BA scope-pack turnaround time ≥40%.
  - **BO2:** Achieve ≥90% requirement completeness score in peer QA.
  - **BO3:** Increase engagement success (win rate / delivery readiness uplift).
- **Product KPIs**
  - **PK1:** Median time from document upload to AI draft ≤8 minutes.
  - **PK2:** Average iterations per scope before approval ≤2.
  - **PK3:** AI confidence score ≥0.75 for production-ready documents.
  - **PK4:** 80% BA adoption within 3 months of launch.
- **Quality KPIs**
  - **QK1:** Validation coverage ≥95% (persona–feature & feature–page mappings).
  - **QK2:** Excel export accuracy complaints <2% of engagements.
  - **QK3:** Requirement defect escape rate reduced by 30%.

### 3. Metric Definitions
| ID | Metric | Definition | Collection | Owner | Cadence |
| --- | --- | --- | --- | --- | --- |
| BO1 | BA turnaround reduction | % change in average hours from meeting close to scope handoff | Compare baseline (manual) vs. AI-assisted engagements | PMO Analyst | Monthly |
| BO2 | Requirement completeness | Peer QA checklist score capturing missing personas, features, dependencies | QA form tied to each engagement | Lead BA | Per engagement |
| BO3 | Engagement success uplift | Change in win rate or delivery readiness survey score | Sales CRM + Delivery readiness survey | Sales Ops & Delivery Lead | Quarterly |
| PK1 | Time-to-first-scope | Median elapsed time from upload to AI draft availability | System telemetry timestamps | Product Analytics | Weekly |
| PK2 | Iteration count | Avg number of regenerate cycles until BA marks scope ready | Application event logs | Product Manager | Weekly |
| PK3 | Confidence score | Average confidence value emitted by validation engine | Validation service logs | AI Lead | Weekly |
| PK4 | Adoption rate | % of BA-led engagements using AI tool | Usage analytics vs. engagement roster | Change Manager | Monthly |
| QK1 | Validation coverage | % requirements passing completeness checks | Validation engine reports | QA Lead | Weekly |
| QK2 | Export accuracy complaints | Number of Jira/ServiceNow tickets citing Excel issues / total exports | Support queue | Support Manager | Monthly |
| QK3 | Requirement defect escape | # of requirement-related defects post-handoff vs. baseline | Delivery retrospectives | Delivery QA | Quarterly |

### 4. Instrumentation Roadmap
1. **Phase 1–2:** Define telemetry schema, implement core event logging (upload events, generation complete, regeneration).  
2. **Phase 3–4:** Emit validation-level metrics (coverage, confidence), wire to analytics warehouse.  
3. **Phase 5–6:** Integrate Excel export status events, complaint tagging.  
4. **Phase 7+:** Automate KPI dashboards (Looker/PowerBI) with threshold alerts.

### 5. Baseline & Targets
- **Baseline Window:** Collect manual process metrics from last 10 BA engagements before pilot.  
- **Target Review:** Reassess targets after pilot (Weeks 7–9) to confirm feasibility.  
- **Alert Thresholds:**  
  - PK1 >10 min median for two consecutive weeks triggers performance war-room.  
  - PK4 <50% adoption at month 2 triggers training/enablement expansion.  
  - QK2 >2% complaints prompts Excel export QA deep dive.

### 6. Data Governance
- All telemetry stored in secured analytics workspace with role-based access.  
- Client-identifiable data anonymized before analytics ingestion.  
- KPI dashboard updates shared in bi-weekly steering meetings.

### 7. Open Tasks
- Assign named owners for each metric.  
- Finalize baseline data pull from PMO and Sales Ops.  
- Confirm analytics tooling (Looker vs. PowerBI) with IT Ops.

