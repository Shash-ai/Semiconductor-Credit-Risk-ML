# Phase 15B — Data Provenance & Leakage Audit

## Purpose

Phase 15B validates the evidence chain that feeds the frozen structural semiconductor model. It does not test credit-default prediction accuracy because the research dataset does not contain observed project-level default/NPA outcomes.

## What is tested

1. Canonical manufacturing and DLI schemas, unique identifiers and row composition.
2. Canonical project IDs against the combined ecosystem master.
3. Manufacturing project investment and DLI project outlay against the ecosystem financial-measure field.
4. Source-document, authority and data-quality provenance coverage.
5. Approval-date/year consistency where exact dates are available.
6. Exact reconstruction of the 12 frozen raw structural features from the ecosystem master.
7. Exact reconstruction of stored z-scores using the historical ddof=0 scaler convention.
8. SHA-256 verification of the five authoritative frozen reference artifacts recorded in the frozen-model manifest.
9. Direct target/outcome leakage, direct identifier leakage and downstream-output circularity.
10. Explicit recording of cohort-relative and point-in-time limitations rather than silently treating them as validation passes.

## Interpretation

A successful run may legitimately end with `PASS_WITH_DECLARED_SCOPE_LIMITATIONS`. This is not a failed model. The warnings are deliberate research controls:

- the structural model is a cross-sectional ecosystem snapshot, not a historical as-of-each-approval-date predictive backtest;
- `financial_rank_within_scope`, `state_financial_share_within_scope` and `company_project_count` are cohort-relative features and therefore require pseudo-new-project/leave-one-out testing in Phase 15H;
- exact DLI approval timing remains missing where the official evidence does not provide it;
- no project-level default/NPA target exists, so accuracy, ROC-AUC, PD calibration or default-prediction claims are prohibited.

## Outputs

- `Data_Provenance_Audit.csv`
- `Data_Lineage_Register.csv`
- `Source_Provenance_Coverage.csv`
- `Feature_Reconstruction_Audit.csv`
- `Frozen_Artifact_Hash_Verification.csv`
- `Leakage_Risk_Register.csv`
- `Phase_15B_Run_Log.jsonl`

## Guardrails

Project investment/outlay is not treated as bank exposure or EAD. Structural clusters are not credit ratings or default classes. Missing evidence is not imputed. A frozen-artifact hash mismatch or canonical-to-ecosystem value mismatch is a hard validation failure and must be investigated before later validation phases proceed.
