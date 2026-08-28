# Phase 15 — Validation and Evidence

## Objective

Phase 15 is the final research-strengthening program for the semiconductor credit-risk decision-support framework. It does not add another risk score. It tests whether the existing data, structural ML, stress, Monte Carlo, portfolio, financial-intelligence, and new-project assessment layers are supported by reproducible evidence.

The phase separates **artifact presence** from **methodological validation**. A CSV or plot existing in the repository is evidence that an analysis was produced; it is not, by itself, proof that the method is valid.

## Research position

The system remains a research decision-support framework. It does not claim observed project-level probability of default, LGD, EAD, ECL, or automated lending approval. Project investment is not treated as bank exposure. Parent/group financial statements are not recast as project-company statements.

## Validation workstreams

1. **15A — Evidence inventory and gap register**
   - Inventory existing validation artifacts.
   - Hash evidence files for traceability.
   - Separate present evidence, partial evidence, missing evidence, and open methodological gates.

2. **15B — Data provenance, leakage, and schema validation**
   - Reconcile canonical projects to official-source provenance.
   - Check duplicate entities/projects, missing source metadata, date consistency, and feature leakage.
   - Verify that no post-assessment outcome information leaks into structural features.

3. **15C — Structural ML validation**
   - Re-run PCA/KMeans diagnostics from controlled inputs.
   - Re-test K sensitivity, silhouette, hierarchical agreement, bootstrap stability, and perturbation stability.
   - Validate the frozen nearest-centroid inference adapter against the reference training assignments.

4. **15D — Ablation, benchmark, and sensitivity expansion**
   - Re-run feature-family ablation.
   - Add leave-one-feature-family-out and controlled perturbation tests.
   - Report rank stability and material changes instead of selecting only favorable outcomes.

5. **15E — Stress and Monte Carlo reproducibility**
   - Reproduce deterministic stress exactly.
   - Reconstruct and document the Monte Carlo shock-generation method and random seed policy.
   - Until reconstructed, historical Monte Carlo outputs remain evidence artifacts but not fully reproducible method evidence.

6. **15F — Portfolio optimization validation**
   - Test sensitivity to budgets, project caps, state caps, minimum allocations, and risk/diversification weights.
   - Report solution stability, concentration, and rank robustness.
   - Do not label a budget value as economically optimal unless the budget itself is truly optimized.

7. **15G — External and financial evidence validation**
   - Expand audited borrower/sponsor financial evidence.
   - Expand independent CRA evidence where available.
   - Validate peer universes, scope, period alignment, and ratio provenance.

8. **15H — New-project generalization and OOD validation**
   - Use controlled hold-one-project-out / pseudo-new-project tests where technically valid.
   - Test frozen preprocessing and inference on unseen-like records.
   - Calibrate or clearly retain the OOD radius as a heuristic if formal calibration is not supported by sample size.

9. **15I — Independent review and paper evidence pack**
   - Produce a reviewer checklist, limitations register, reproducibility manifest, and paper-ready validation tables.
   - Independent external validation remains open until a person outside the model-building workflow reviews the method and evidence.

## Validation hierarchy

Evidence strength, from strongest to weakest for this project:

1. Reproducible result from frozen code + frozen input + logged configuration.
2. Primary/official external evidence with exact provenance.
3. Independent method agreement or external reviewer confirmation.
4. Internal sensitivity/ablation evidence.
5. Historical output with incomplete reproduction metadata.
6. Narrative assertion without traceable evidence — not acceptable as validation.

## Hard research guardrails

- No observed project default/NPA target is claimed where none exists.
- Structural clusters are not default-risk classes.
- Stress scores are modelled vulnerability/stress measures, not realized loss probabilities.
- No PD/LGD/EAD/ECL is generated from unavailable data.
- No missing bank loan variables are fabricated.
- No parent financial observation is represented as an exact project-company observation.
- Missing evidence remains explicitly missing.
- A validation artifact cannot self-certify its own methodology solely because the file exists.

Start Phase 15 by running `01_Audit/build_validation_evidence_register.py` after syncing the repository.