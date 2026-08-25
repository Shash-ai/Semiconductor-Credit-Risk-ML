# Phase 13 — Continuous Data Ingestion & Automated Project Evaluation

## Objective

Build a reproducible, source-backed monitoring pipeline that detects newly announced semiconductor manufacturing approvals, routes them through verification and canonicalization, and evaluates eligible projects through frozen research-risk methods without converting missing public information into invented banking data.

## Safety states

`DISCOVERED -> SOURCE_VERIFIED -> CANONICALIZED -> MODEL_EVALUATED -> STRESS_EVALUATED -> DASHBOARD_ACTIVE`

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

The verification stage re-fetches the source, checks official-source provenance, extracts candidate fields conservatively, compares the announcement with the canonical master, stores field-level evidence, and routes every candidate through human review. Extracted fields remain `EXTRACTED_NOT_VERIFIED` until reviewed.

### 13D — Controlled canonicalization

Implemented in `05_Canonicalization/canonicalize_reviewed_candidates.py`.

Canonicalization is human-gated. A reviewer must explicitly approve a new project and confirm the required canonical fields. Duplicate/conflict checks run before staging. The default execution is stage-only; applying rows requires both `--apply` and the explicit confirmation token `APPLY_REVIEWED_CANONICAL_ROWS`.

### 13E — Frozen structural-model inference

Implemented through `06_Frozen_Model/freeze_and_infer.py`.

The current frozen structural model is `SCI_STRUCTURAL_CLUSTER_FROZEN_2026_V2`. Phase 13E uses the authoritative historical Phase-3 feature matrix, stored standardized features, seven-component PCA loadings, and validated cluster assignments to reproduce the original 36-project model before any new-project inference is allowed.

The validated local run reproduced the historical model to floating-point precision and recovered the validated clusters with full agreement. New projects are transformed with frozen historical scaler/PCA parameters and assigned to the nearest validated seven-dimensional structural centroid. Cluster membership is a structural segment, not a credit-risk class or rating. Out-of-reference projects are flagged for review rather than converted into invented default-risk estimates.

### 13F — Controlled automated stress and banking-evidence evaluation

Implemented in `07_Automated_Evaluation/evaluate_new_projects.py`.

Phase 13F reads only projects that have already passed Phase 13E structural inference. Before scoring a new project, it reproduces the historical Phase-3E deterministic stress method from `Robust_Stress_Test_Full.csv`.

The deterministic contract is:

- project-size risk weight: 25%;
- geographic-concentration risk weight: 15%;
- credit-growth risk weight: 15%;
- credit-volatility risk weight: 15%;
- NPA-growth risk weight: 15%;
- NPA-pressure risk weight: 15%;
- mild macro severity: 10%;
- moderate macro severity: 25%;
- severe macro severity: 50%;
- a stressed macro-risk component is `baseline_risk + severity * (1 - baseline_risk)`;
- structural project-size and geographic-concentration risk are not shocked.

Project-size and geographic risk for a new project are normalized against the frozen original manufacturing reference bounds and clipped with an explicit out-of-reference signal when required. Macro risk is used only when an exact historical/verified approval-year risk vector is available. A project with an approval year for which no verified macro vector exists is returned as `MACRO_CONTEXT_REVIEW_REQUIRED` and receives no deterministic stress score until the macro context is updated and verified.

#### Monte Carlo reproducibility gate

The repository contains the historical Phase-6B Monte Carlo outputs, including the 10,000-simulation summary, systemic/idiosyncratic weights, and Beta shock-distribution parameters. However, the exact historical simulation/scoring implementation is not currently preserved as a reproducible source file in the tracked repository.

Phase 13F therefore deliberately returns `MC_METHOD_REPRODUCTION_REQUIRED` for a new project instead of inventing or silently replacing the Phase-6B method. A new versioned Monte Carlo implementation may be activated only after the historical method is recovered/reproduced or after a separately documented methodology change is approved.

#### Banking evidence gate

For borrower financials, project finance, security/recovery, execution risk, EWS, and integrated banking-risk outputs, Phase 13F checks only for an exact `project_id` match in the relevant banking output files. It does not transfer values from analogous borrowers/projects and does not infer DSCR, collateral, debt, bank exposure, repayment history, or recovery values from project investment.

If no exact project-specific banking evidence exists, the project is labelled `INSUFFICIENT_VERIFIED_BANKING_EVIDENCE` and is held for human/evidence review.

### 13G — Dashboard live-pipeline integration

Implemented in `app/banking_dashboard_v3_2.py` and exposed through the V3 preview entry point `app/community_main_v3_preview.py`.

A new `Data Operations -> Continuous Pipeline` workspace shows:

- pipeline state and active source count;
- the current canonical project count;
- discovered, verification, staging, structural-inference and evaluation counts;
- Phase 13E frozen-model validation state;
- Phase 13F deterministic-stress reproduction state;
- the explicit Monte Carlo reproducibility gate;
- latest available runtime audit status for Phases 13B–13F;
- discovery candidates and source URLs;
- verification/canonicalization queues and conflicts;
- new-project structural/stress/banking evaluation registers;
- the official/reference source registry.

The Phase 13G page uses native Streamlit tables and metrics for the pipeline records so missing files or empty candidate states do not render raw HTML. Missing runtime artifacts are displayed as not yet published rather than being treated as zero-risk or successful execution.

### 13H — Scheduled GitHub Actions orchestration

Implemented in `.github/workflows/phase13_continuous_ingestion.yml`.

The workflow is configured for manual dispatch and a daily scheduled run at `02:30 UTC` (`08:00 IST`, subject to normal GitHub Actions scheduling delay). It executes Phases 13B through 13F in order after compiling the scripts and installing the tracked Python requirements.

The scheduled canonicalization step is always stage-only. It never passes `--apply` or the canonical-apply confirmation token, and the publish step defensively excludes the canonical manufacturing master from the staged Git commit. Human review and an explicit manual apply remain required before any new project can enter the canonical research dataset.

The workflow publishes only Phase 13 candidate, audit, review, frozen-model and automated-evaluation runtime outputs so the dashboard can reflect scheduled activity. It uses a serialized concurrency group and rebases its generated-output commit onto the latest `main` before pushing; conflicts fail rather than force-overwriting human work.

The workflow code is implemented, but the first GitHub Actions execution must still be run and inspected before Phase 13H can be marked operationally validated.

## Current outputs

### Discovery

- `02_Candidates/Project_Discovery_Candidates.csv`
- `03_Audit/Discovery_Run_Log.jsonl`

### Verification

- `04_Verification/Structured_Project_Candidates.csv`
- `04_Verification/Candidate_Field_Evidence.csv`
- `04_Verification/Verification_Queue.csv`
- `04_Verification/Verification_Run_Log.jsonl`

### Canonicalization

- `05_Canonicalization/Canonicalization_Review.csv`
- `05_Canonicalization/Canonical_Staging.csv`
- `05_Canonicalization/Canonicalization_Conflicts.csv`
- `05_Canonicalization/Canonicalization_Run_Log.jsonl`
- `05_Canonicalization/backups/` only when an approved staged row is explicitly applied

### Frozen model / inference

- `06_Frozen_Model/artifacts/Frozen_Model_Manifest.json`
- `06_Frozen_Model/artifacts/Frozen_Scaler_Parameters.csv`
- `06_Frozen_Model/artifacts/Frozen_PCA_Components.csv`
- `06_Frozen_Model/artifacts/Frozen_Cluster_Centroids.csv`
- `06_Frozen_Model/artifacts/Frozen_Reference_PCA_Scores.csv`
- `06_Frozen_Model/artifacts/Frozen_Model_Validation.json`
- `06_Frozen_Model/Frozen_Model_New_Project_Inference.csv`
- `06_Frozen_Model/Frozen_Model_Run_Log.jsonl`

### Automated evaluation

Created after a Phase 13F run:

- `07_Automated_Evaluation/New_Project_Deterministic_Stress.csv`
- `07_Automated_Evaluation/New_Project_Monte_Carlo_Status.csv`
- `07_Automated_Evaluation/New_Project_Banking_Evidence_Status.csv`
- `07_Automated_Evaluation/New_Project_Evaluation_Register.csv`
- `07_Automated_Evaluation/Phase_13F_Method_Validation.json`
- `07_Automated_Evaluation/Automated_Evaluation_Run_Log.jsonl`

### Dashboard integration

- `app/banking_dashboard_v3_2.py`
- `app/community_main_v3_preview.py`

### Scheduled orchestration

- `.github/workflows/phase13_continuous_ingestion.yml`

If there are no new canonical manufacturing projects, Phases 13E and 13F still validate their historical method contracts and write empty schema-compatible new-project output files. No synthetic project is created simply to make the pipeline appear active.

## Next stages

- 13I — model/version/audit tracking
- 13J — end-to-end controlled simulation

The stages remain separated so unverified announcements cannot enter the canonical research dataset or banking decision-support outputs automatically.
