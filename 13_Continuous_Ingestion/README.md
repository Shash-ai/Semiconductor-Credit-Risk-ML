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

### 13D — Controlled canonicalization

Implemented in `05_Canonicalization/canonicalize_reviewed_candidates.py`.

The canonicalization stage is deliberately human-gated:

1. structured candidates are copied into `Canonicalization_Review.csv` as `PENDING` review rows;
2. extracted values are shown separately from reviewer-confirmed fields;
3. a reviewer must explicitly set `review_decision=APPROVE_NEW_PROJECT` and fill the confirmed canonical fields;
4. required fields, approval date, state verification, data-quality flag, project type and project group are validated;
5. possible duplicate projects are blocked using company similarity, state, standardized type and investment proximity checks;
6. approved non-conflicting rows are assigned the next available `SEM-xxxx` identifier and written to `Canonical_Staging.csv`;
7. the default run is stage-only and does not change the canonical master;
8. applying staged rows requires both `--apply` and the explicit confirmation token `APPLY_REVIEWED_CANONICAL_ROWS`;
9. before an apply operation the previous canonical master is backed up locally.

This prevents an internet discovery or imperfect extractor from silently becoming an official research observation.

### 13E — Frozen structural-model inference

Implemented in `06_Frozen_Model/freeze_and_infer.py`.

The Phase 13E stage does not retrain the historical model when a new project appears. It first attempts to reproduce the validated 36-project structural model from the existing reference artifacts:

- the 36-row semiconductor ecosystem master;
- the stored seven-component PCA loadings;
- the stored validated cluster assignments;
- the original 12-feature structural feature contract.

Before creating frozen artifacts, the script checks that reconstructed PC1/PC2 scores reproduce the stored model scores within a strict tolerance and that nearest frozen seven-dimensional cluster centroids recover the validated reference cluster assignments. If either check fails, Phase 13E fails safe and performs no new-project inference.

When the reproduction checks pass, the frozen artifacts contain the reference scaler parameters, PCA components, validated cluster centroids, reference PCA scores, hashes of the reference inputs and a versioned model manifest. A newly canonicalized manufacturing project is then transformed with the frozen scaler/PCA parameters and assigned to the nearest validated structural cluster centroid.

The output is explicitly a structural segment, not a credit-risk grade. Distance outside the reference cluster's 95th-percentile radius is surfaced as `STRUCTURAL_EXTRAPOLATION_REVIEW_REQUIRED` instead of being converted into an invented default-risk measure.

Phase 13E does not produce PD, LGD, EAD, ECL, an official bank rating, or an automated approve/reject decision.

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

### Canonicalization

- `05_Canonicalization/Canonicalization_Review.csv`
- `05_Canonicalization/Canonical_Staging.csv`
- `05_Canonicalization/Canonicalization_Conflicts.csv`
- `05_Canonicalization/Canonicalization_Run_Log.jsonl` after the first Phase 13D run
- `05_Canonicalization/backups/` only when an approved staged row is explicitly applied

The canonical master remains unchanged during a normal Phase 13D run.

### Frozen model / inference

Created when Phase 13E passes its reference-reproduction checks:

- `06_Frozen_Model/artifacts/Frozen_Model_Manifest.json`
- `06_Frozen_Model/artifacts/Frozen_Scaler_Parameters.csv`
- `06_Frozen_Model/artifacts/Frozen_PCA_Components.csv`
- `06_Frozen_Model/artifacts/Frozen_Cluster_Centroids.csv`
- `06_Frozen_Model/artifacts/Frozen_Reference_PCA_Scores.csv`
- `06_Frozen_Model/artifacts/Frozen_Model_Validation.json`
- `06_Frozen_Model/Frozen_Model_New_Project_Inference.csv`
- `06_Frozen_Model/Frozen_Model_Run_Log.jsonl`

If no new canonical manufacturing project exists, Phase 13E can still validate/freeze the reference model and will write an empty schema-compatible inference file.

## Next stages

- 13F — automated stress / Monte Carlo / banking-layer evaluation for eligible new projects
- 13G — dashboard pipeline-status and new-project intake views
- 13H — scheduled GitHub Actions execution
- 13I — model/version/audit tracking
- 13J — end-to-end controlled simulation

The stages remain separated so unverified announcements cannot enter the canonical research dataset or banking decision-support outputs automatically.
