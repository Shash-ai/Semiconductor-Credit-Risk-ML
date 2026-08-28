# Phase 15C — Structural ML Robustness Validation

## Objective

Phase 15C challenges the structural PCA + clustering layer rather than accepting historical artifacts at face value. The phase validates exact frozen-reference reproduction and then measures how sensitive the six-cluster structural segmentation is to initialization, sample composition, small perturbations, PCA dimensionality, and clustering family.

## Tests

1. Exact frozen PCA reconstruction against stored PC1/PC2 values.
2. Exact recovery of validated structural clusters using the frozen nearest-centroid inference rule.
3. Repeated K-selection analysis for K=2..10 using silhouette, Calinski-Harabasz, Davies-Bouldin and seed-to-seed ARI stability.
4. K=6 initialization sensitivity using 100 deliberately single-initialization KMeans fits.
5. Ward hierarchical cross-method comparison at K=6.
6. 70%, 80% and 90% project-subsample stability with prediction back onto the full reference universe.
7. Frozen-inference perturbation testing on the three continuous cohort-relative features only.
8. PCA dimensionality sensitivity from 5 through 12 components.
9. Leave-one-project-out influence testing.
10. Per-project assignment-stability register to identify structurally fragile observations.

## Interpretation

Adjusted Rand Index and assignment-agreement metrics in this phase evaluate **structural segmentation robustness only**. They are not classification accuracy, default-prediction accuracy, credit ratings, or probabilities of default.

Historical Phase 3B metrics are retained as comparison evidence, but Phase 15C does not assert that the original KMeans random-state/training contract is exactly reproducible unless it is explicitly available.

Perturbation noise is an engineering sensitivity test in standardized-feature units. It is not a claimed empirical probability distribution for future semiconductor projects.

## Run

```bash
python -m py_compile \
"15_Validation_and_Evidence/03_Structural_ML/validate_structural_ml.py"

python \
"15_Validation_and_Evidence/03_Structural_ML/validate_structural_ml.py"
```

## Outputs

- `K_Selection_Robustness.csv`
- `K6_Seed_Stability.csv`
- `K6_Subsample_Stability.csv`
- `Frozen_Inference_Perturbation_Stability.csv`
- `PCA_Component_Sensitivity.csv`
- `Leave_One_Out_Influence.csv`
- `Project_Assignment_Stability.csv`
- `Historical_vs_Recomputed_K_Metrics.csv`
- `Structural_ML_Validation_Summary.csv`
- `Phase_15C_Run_Log.jsonl`
