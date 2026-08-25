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

The discovery engine currently monitors active RSS sources, filters for semiconductor + approval language, fetches matching articles, hashes content for deduplication, stores candidate records, and writes an append-only JSONL run audit.

## Current outputs

- `02_Candidates/Project_Discovery_Candidates.csv`
- `03_Audit/Discovery_Run_Log.jsonl` after the first run

## Not implemented yet

- source verification and structured field extraction
- entity/project duplicate reconciliation
- automatic canonical master update
- frozen-model inference for new projects
- automated stress / Monte Carlo / banking-layer rebuild
- dashboard pipeline-status page
- scheduled GitHub Actions execution

These are intentionally separated so unverified announcements cannot enter the canonical research dataset automatically.
