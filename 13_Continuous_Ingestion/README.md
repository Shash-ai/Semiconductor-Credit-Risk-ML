# Phase 13 — Continuous Data Ingestion & Automated Project Evaluation

## Objective

Build a reproducible, source-backed monitoring pipeline that detects newly announced semiconductor manufacturing approvals, routes them through verification and canonicalization, and later evaluates eligible projects through the frozen research risk framework.

## Safety states

`DISCOVERED -> SOURCE_VERIFIED -> CANONICALIZED -> MODEL_EVALUATED -> DASHBOARD_ACTIVE`

Ambiguous or conflicting records are routed to `MANUAL_REVIEW_REQUIRED`.

No discovered record is automatically treated as verified banking data. Project investment must never be used as bank exposure/EAD. Missing project debt, DSCR, collateral, repayment or recovery values remain unavailable unless supported by evidence.

## Current implementation

### 13A — Source registry

Implemented in `00_Config/source_registry.csv`.

### 13B — Project discovery

Implemented in `01_Discovery/discover_new_projects.py`.

The discovery engine monitors active RSS sources, filters for semiconductor + approval language, fetches matching articles, hashes content for deduplication, stores candidate records, and writes an append-only JSONL run audit.

### 13C — Source verification & structured extraction

Implemented in `04_Verification/verify_candidates.py`.

The verification stage:

- re-fetches the candidate source;
- checks whether the source is an official PIB / MeitY / ISM domain;
- detects approval language;
- extracts candidate company, state, project type and investment values conservatively;
- compares article text with the canonical semiconductor project master;
- flags possible existing projects and multi-project announcements;
- stores field-level evidence snippets;
- routes every candidate to a human review queue;
- never writes directly to the canonical master.

Extracted fields are marked `EXTRACTED_NOT_VERIFIED` until reviewed. A primary-source page being accessible is not by itself treated as proof that every extracted field is correct.

## Current outputs

### Discovery

- `02_Candidates/Project_Discovery_Candidates.csv`
- `03_Audit/Discovery_Run_Log.jsonl` after the first discovery run

### Verification

Created after the first Phase 13C run:

- `04_Verification/Structured_Project_Candidates.csv`
- `04_Verification/Candidate_Field_Evidence.csv`
- `04_Verification/Verification_Queue.csv`
- `04_Verification/Verification_Run_Log.jsonl`

If the candidate register is empty, Phase 13C exits successfully and creates empty schema-compatible output files. It does not fabricate a project for testing.

## Next stages

- 13D — reviewed canonicalization and safe master update
- 13E — frozen-model inference for new canonical projects
- 13F — automated stress / Monte Carlo / banking-layer rebuild
- 13G — dashboard pipeline-status and new-project intake views
- 13H — scheduled GitHub Actions execution
- 13I — model/version/audit tracking
- 13J — end-to-end controlled simulation

The stages remain separated so unverified announcements cannot enter the canonical research dataset or banking decision-support outputs automatically.
