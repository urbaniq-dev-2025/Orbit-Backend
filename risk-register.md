## Initial Risk & Assumption Register

| ID | Category | Description | Impact | Likelihood | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Requirements Quality | BA notes lack sufficient detail for AI extraction | High | Medium | Enforce minimum input checklist, clarifying question flow, BA training | BA Lead | Open |
| R2 | Model Accuracy | LLM misinterprets domain-specific terminology leading to incorrect scope | High | Medium | Domain classifier tuning, validation ensemble, SME review checkpoints | AI Lead | Open |
| R3 | Infrastructure | Delay in provisioning secure environment/SSO integration | Medium | Medium | Early infra tickets, sandbox fallback, weekly infra standups | Platform Lead | Open |
| R4 | Adoption | BAs resist process change or perceive tool as overhead | Medium | Medium | Pilot champions, enablement sessions, feedback loop incorporation | Change Manager | Open |
| R5 | Data Privacy | Client-sensitive information stored without proper controls | High | Low | Data retention policy, encrypted storage, PII redaction, audits | Security Officer | Open |
| R6 | Performance | Processing exceeds NFR (5–12 seconds for <15 pages) causing frustration | Medium | Low | Performance testing, optimized chunking, caching | Engineering Lead | Open |
| R7 | Excel Output Quality | Excel export mismatches scope document causing rework | Medium | Medium | Automated diff checks, LLM verification, regression suite | QA Lead | Open |
| R8 | Scope Creep | Requests for client portal or integrations before MVP | Medium | High | Roadmap governance, change control process, phased releases | Product Manager | Open |

### Key Assumptions
- BAs can allocate time for pilot feedback cycles during Weeks 5–8.
- Leadership will nominate an executive sponsor and steering committee in Week 0.
- Existing BA documents can be shared (with redactions) for tuning and testing.
- Corporate policy allows the selected LLM provider for internal documents.
- Required support functions (Security, IT Ops, AI Ops) agree to bi-weekly working sessions.

### Next Steps
- Confirm risk owners and integrate register into steering deck.
- Update status bi-weekly; escalate High/High items immediately.
- Expand register post-architecture review (Phase 1) with technical and operational findings.

