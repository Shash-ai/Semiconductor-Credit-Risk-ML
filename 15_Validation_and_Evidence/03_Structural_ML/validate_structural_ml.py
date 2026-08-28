from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "15_Validation_and_Evidence" / "03_Structural_ML"
CONFIG_FILE = ROOT / "15_Validation_and_Evidence" / "00_Config" / "structural_ml_validation_config.json"

FEATURE_FILE = ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Ecosystem_Clustering_Final.csv"
ASSIGNMENT_FILE = ROOT / "03_Modeling" / "Phase_3B_Cluster_Validation" / "Validated_Cluster_Assignments.csv"
HISTORICAL_METRICS_FILE = ROOT / "03_Modeling" / "Phase_3B_Cluster_Validation" / "Cluster_Validation_All_Metrics.csv"
PCA_LOADINGS_FILE = ROOT / "03_Modeling" / "Phase_3A_PCA_KMeans" / "PCA_Loadings.csv"
PCA_VARIANCE_FILE = ROOT / "03_Modeling" / "Phase_3A_PCA_KMeans" / "PCA_Explained_Variance.csv"
FROZEN_CENTROIDS_FILE = ROOT / "13_Continuous_Ingestion" / "06_Frozen_Model" / "artifacts" / "Frozen_Cluster_Centroids.csv"
FROZEN_MANIFEST_FILE = ROOT / "13_Continuous_Ingestion" / "06_Frozen_Model" / "artifacts" / "Frozen_Model_Manifest.json"

K_SELECTION_OUT = PHASE_DIR / "K_Selection_Robustness.csv"
SEED_STABILITY_OUT = PHASE_DIR / "K6_Seed_Stability.csv"
SUBSAMPLE_OUT = PHASE_DIR / "K6_Subsample_Stability.csv"
PERTURBATION_OUT = PHASE_DIR / "Frozen_Inference_Perturbation_Stability.csv"
PCA_SENSITIVITY_OUT = PHASE_DIR / "PCA_Component_Sensitivity.csv"
LOO_OUT = PHASE_DIR / "Leave_One_Out_Influence.csv"
PROJECT_STABILITY_OUT = PHASE_DIR / "Project_Assignment_Stability.csv"
HISTORICAL_COMPARISON_OUT = PHASE_DIR / "Historical_vs_Recomputed_K_Metrics.csv"
SUMMARY_OUT = PHASE_DIR / "Structural_ML_Validation_Summary.csv"
RUN_LOG = PHASE_DIR / "Phase_15C_Run_Log.jsonl"

ENGINE_VERSION = "SCI_STRUCTURAL_ML_VALIDATION_V1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def mean_pairwise_ari(label_sets: list[np.ndarray]) -> float:
    if len(label_sets) < 2:
        return float("nan")
    vals = [adjusted_rand_score(a, b) for a, b in combinations(label_sets, 2)]
    return float(np.mean(vals)) if vals else float("nan")


def map_labels_to_reference(predicted: np.ndarray, reference: np.ndarray) -> np.ndarray:
    pred_labels = np.unique(predicted)
    ref_labels = np.unique(reference)
    matrix = np.zeros((len(pred_labels), len(ref_labels)), dtype=int)
    for i, p in enumerate(pred_labels):
        for j, r in enumerate(ref_labels):
            matrix[i, j] = int(np.sum((predicted == p) & (reference == r)))
    row_ind, col_ind = linear_sum_assignment(-matrix)
    mapping = {pred_labels[i]: ref_labels[j] for i, j in zip(row_ind, col_ind)}
    return np.array([mapping.get(x, x) for x in predicted])


def strength_label(value: float, thresholds: dict) -> str:
    if value >= float(thresholds["ari_strong"]):
        return "STRONG"
    if value >= float(thresholds["ari_good"]):
        return "GOOD"
    if value >= float(thresholds["ari_moderate"]):
        return "MODERATE"
    return "WEAK"


def nearest_frozen_centroid(scores: np.ndarray, centroids: pd.DataFrame, pc_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    centroid_values = centroids[pc_cols].to_numpy(dtype=float)
    centroid_labels = pd.to_numeric(centroids["validated_cluster"], errors="raise").astype(int).to_numpy()
    distances = np.linalg.norm(scores[:, None, :] - centroid_values[None, :, :], axis=2)
    idx = distances.argmin(axis=1)
    return centroid_labels[idx], distances[np.arange(len(scores)), idx]


def validate_inputs(features: pd.DataFrame, assignments: pd.DataFrame, manifest: dict) -> tuple[list[str], list[str]]:
    raw_features = list(manifest["raw_features"])
    z_features = [f"z_{f}" for f in raw_features]
    required_feature_cols = ["ecosystem_id"] + raw_features + z_features
    missing = [c for c in required_feature_cols if c not in features.columns]
    if missing:
        raise RuntimeError(f"Feature matrix missing required columns: {missing}")
    if "validated_cluster" not in assignments.columns or "ecosystem_id" not in assignments.columns:
        raise RuntimeError("Validated assignments missing ecosystem_id or validated_cluster")
    if set(features["ecosystem_id"].astype(str)) != set(assignments["ecosystem_id"].astype(str)):
        raise RuntimeError("Feature matrix and validated assignments do not contain the same ecosystem IDs")
    if len(features) != int(manifest["reference_universe_rows"]):
        raise RuntimeError(
            f"Reference row count mismatch: feature matrix={len(features)}, manifest={manifest['reference_universe_rows']}"
        )
    return raw_features, z_features


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError(f"Config engine mismatch: {config.get('engine_version')} != {ENGINE_VERSION}")

    manifest = json.loads(FROZEN_MANIFEST_FILE.read_text(encoding="utf-8"))
    features = read_csv(FEATURE_FILE)
    assignments = read_csv(ASSIGNMENT_FILE)
    historical = read_csv(HISTORICAL_METRICS_FILE)
    centroids = read_csv(FROZEN_CENTROIDS_FILE)
    loadings = read_csv(PCA_LOADINGS_FILE, index_col=0)

    raw_features, z_features = validate_inputs(features, assignments, manifest)
    reference_k = int(config["reference_k"])
    thresholds = config["research_interpretation_thresholds"]
    tolerance = float(thresholds["reference_reproduction_tolerance"])
    rng_master = np.random.default_rng(int(config["random_seed"]))

    # Preserve the authoritative feature-matrix order and align reference assignments to it.
    work = features[["ecosystem_id"] + z_features].copy()
    aligned_assignments = work[["ecosystem_id"]].merge(
        assignments[["ecosystem_id", "validated_cluster", "PC1", "PC2"]],
        on="ecosystem_id",
        how="left",
        validate="one_to_one",
    )
    reference_labels = pd.to_numeric(aligned_assignments["validated_cluster"], errors="raise").astype(int).to_numpy()
    Xz = work[z_features].astype(float).to_numpy()

    # ------------------------------------------------------------------
    # Exact frozen PCA / centroid reference reproduction.
    # ------------------------------------------------------------------
    loadings.index = loadings.index.astype(str)
    missing_loadings = [c for c in z_features if c not in loadings.index]
    if missing_loadings:
        raise RuntimeError(f"PCA loadings missing frozen z-features: {missing_loadings}")
    pc_cols = sorted(
        [c for c in loadings.columns if str(c).startswith("PC")],
        key=lambda x: int(str(x).replace("PC", "")),
    )
    retained = int(manifest["retained_pca_components"])
    pc_cols = pc_cols[:retained]
    loading_matrix = loadings.loc[z_features, pc_cols].astype(float).to_numpy()
    frozen_scores = Xz @ loading_matrix

    pc1_error = float(np.max(np.abs(frozen_scores[:, 0] - pd.to_numeric(aligned_assignments["PC1"]).to_numpy())))
    pc2_error = float(np.max(np.abs(frozen_scores[:, 1] - pd.to_numeric(aligned_assignments["PC2"]).to_numpy())))
    pca_reference_pass = bool(max(pc1_error, pc2_error) <= tolerance)

    frozen_pred, frozen_distance = nearest_frozen_centroid(frozen_scores, centroids, pc_cols)
    frozen_centroid_ari = float(adjusted_rand_score(reference_labels, frozen_pred))
    frozen_exact_agreement = float(np.mean(frozen_pred == reference_labels))
    frozen_reference_pass = bool(frozen_exact_agreement >= 0.999999)

    # ------------------------------------------------------------------
    # K-selection robustness across repeated KMeans fits.
    # ------------------------------------------------------------------
    k_rows: list[dict] = []
    k_label_sets: dict[int, list[np.ndarray]] = {}
    for k in [int(x) for x in config["k_candidates"]]:
        run_rows = []
        label_sets: list[np.ndarray] = []
        for run in range(int(config["k_selection_runs_per_k"])):
            seed = int(config["random_seed"]) + (k * 10000) + run
            model = KMeans(
                n_clusters=k,
                random_state=seed,
                n_init=int(config["k_selection_n_init"]),
            )
            labels = model.fit_predict(frozen_scores)
            label_sets.append(labels)
            run_rows.append(
                {
                    "silhouette": silhouette_score(frozen_scores, labels),
                    "calinski_harabasz": calinski_harabasz_score(frozen_scores, labels),
                    "davies_bouldin": davies_bouldin_score(frozen_scores, labels),
                    "smallest_cluster": int(pd.Series(labels).value_counts().min()),
                    "largest_cluster": int(pd.Series(labels).value_counts().max()),
                }
            )
        runs = pd.DataFrame(run_rows)
        k_label_sets[k] = label_sets
        k_rows.append(
            {
                "k": k,
                "runs": len(runs),
                "mean_silhouette": float(runs["silhouette"].mean()),
                "std_silhouette": float(runs["silhouette"].std(ddof=0)),
                "min_silhouette": float(runs["silhouette"].min()),
                "max_silhouette": float(runs["silhouette"].max()),
                "mean_calinski_harabasz": float(runs["calinski_harabasz"].mean()),
                "mean_davies_bouldin": float(runs["davies_bouldin"].mean()),
                "minimum_observed_cluster_size": int(runs["smallest_cluster"].min()),
                "maximum_observed_cluster_size": int(runs["largest_cluster"].max()),
                "mean_pairwise_seed_ari": mean_pairwise_ari(label_sets),
                "reference_k": k == reference_k,
            }
        )
    k_selection = pd.DataFrame(k_rows).sort_values("k").reset_index(drop=True)
    atomic_write(k_selection, K_SELECTION_OUT)
    best_k = int(k_selection.sort_values(["mean_silhouette", "mean_pairwise_seed_ari"], ascending=False).iloc[0]["k"])

    # Historical metrics are retained as historical evidence, not assumed to be exactly reproducible
    # because the original training-code/random-state contract was not preserved.
    hist_cols = [c for c in ["k", "silhouette", "calinski_harabasz", "davies_bouldin", "kmeans_hierarchical_ari", "mean_bootstrap_ari"] if c in historical.columns]
    historical_small = historical[hist_cols].copy()
    historical_small = historical_small.rename(columns={c: f"historical_{c}" for c in hist_cols if c != "k"})
    hist_compare = k_selection.merge(historical_small, on="k", how="left")
    hist_compare["comparison_status"] = "HISTORICAL_EVIDENCE_ONLY_ORIGINAL_TRAINING_RANDOM_STATE_NOT_ASSERTED"
    atomic_write(hist_compare, HISTORICAL_COMPARISON_OUT)

    # ------------------------------------------------------------------
    # K=6 initialization sensitivity: deliberately n_init=1 to expose local optima.
    # ------------------------------------------------------------------
    seed_rows: list[dict] = []
    seed_match_counts = np.zeros(len(reference_labels), dtype=int)
    for run in range(int(config["seed_runs"])):
        seed = int(config["random_seed"]) + run
        model = KMeans(
            n_clusters=reference_k,
            random_state=seed,
            n_init=int(config["seed_test_n_init"]),
        )
        labels = model.fit_predict(frozen_scores)
        mapped = map_labels_to_reference(labels, reference_labels)
        seed_match_counts += (mapped == reference_labels).astype(int)
        seed_rows.append(
            {
                "run": run + 1,
                "random_state": seed,
                "ari_vs_validated": adjusted_rand_score(reference_labels, labels),
                "mapped_assignment_agreement": float(np.mean(mapped == reference_labels)),
                "silhouette": silhouette_score(frozen_scores, labels),
                "inertia": float(model.inertia_),
            }
        )
    seed_df = pd.DataFrame(seed_rows)
    atomic_write(seed_df, SEED_STABILITY_OUT)
    seed_mean_ari = float(seed_df["ari_vs_validated"].mean())
    seed_median_ari = float(seed_df["ari_vs_validated"].median())
    seed_min_ari = float(seed_df["ari_vs_validated"].min())

    # ------------------------------------------------------------------
    # Alternative clustering family: Ward hierarchical clustering.
    # ------------------------------------------------------------------
    hierarchical_labels = AgglomerativeClustering(n_clusters=reference_k, linkage="ward").fit_predict(frozen_scores)
    hierarchical_ari = float(adjusted_rand_score(reference_labels, hierarchical_labels))

    # ------------------------------------------------------------------
    # Subsample stability: fit on 70/80/90% of projects, then predict all projects.
    # ------------------------------------------------------------------
    subsample_rows: list[dict] = []
    subsample_match_counts = {
        float(f): np.zeros(len(reference_labels), dtype=int) for f in config["subsample_fractions"]
    }
    for fraction_raw in config["subsample_fractions"]:
        fraction = float(fraction_raw)
        train_n = max(reference_k + 1, int(round(len(frozen_scores) * fraction)))
        for run in range(int(config["subsample_runs_per_fraction"])):
            seed = int(rng_master.integers(0, 2**31 - 1))
            rng = np.random.default_rng(seed)
            train_idx = np.sort(rng.choice(len(frozen_scores), size=train_n, replace=False))
            model = KMeans(
                n_clusters=reference_k,
                random_state=seed,
                n_init=int(config["subsample_n_init"]),
            )
            model.fit(frozen_scores[train_idx])
            labels = model.predict(frozen_scores)
            mapped = map_labels_to_reference(labels, reference_labels)
            subsample_match_counts[fraction] += (mapped == reference_labels).astype(int)
            subsample_rows.append(
                {
                    "fraction": fraction,
                    "run": run + 1,
                    "train_rows": train_n,
                    "random_state": seed,
                    "ari_vs_validated": adjusted_rand_score(reference_labels, labels),
                    "mapped_assignment_agreement": float(np.mean(mapped == reference_labels)),
                    "train_silhouette": silhouette_score(frozen_scores[train_idx], model.labels_),
                }
            )
    subsample_df = pd.DataFrame(subsample_rows)
    atomic_write(subsample_df, SUBSAMPLE_OUT)

    # ------------------------------------------------------------------
    # Frozen-inference perturbation: only continuous structural features are perturbed.
    # Noise is in standardized-feature units and is not claimed to be a real-world distribution.
    # ------------------------------------------------------------------
    continuous_z_cols = [f"z_{x}" for x in config["continuous_features_for_perturbation"]]
    continuous_idx = [z_features.index(c) for c in continuous_z_cols]
    perturb_rows: list[dict] = []
    perturb_match_counts = {
        float(level): np.zeros(len(reference_labels), dtype=int) for level in config["perturbation_standardized_noise_sd"]
    }
    for level_raw in config["perturbation_standardized_noise_sd"]:
        level = float(level_raw)
        for run in range(int(config["perturbation_runs_per_level"])):
            seed = int(rng_master.integers(0, 2**31 - 1))
            rng = np.random.default_rng(seed)
            perturbed = Xz.copy()
            perturbed[:, continuous_idx] += rng.normal(0.0, level, size=(len(Xz), len(continuous_idx)))
            perturbed_scores = perturbed @ loading_matrix
            labels, distances = nearest_frozen_centroid(perturbed_scores, centroids, pc_cols)
            perturb_match_counts[level] += (labels == reference_labels).astype(int)
            perturb_rows.append(
                {
                    "standardized_noise_sd": level,
                    "run": run + 1,
                    "random_state": seed,
                    "ari_vs_validated": adjusted_rand_score(reference_labels, labels),
                    "exact_assignment_agreement": float(np.mean(labels == reference_labels)),
                    "mean_distance_to_assigned_centroid": float(np.mean(distances)),
                    "max_distance_to_assigned_centroid": float(np.max(distances)),
                }
            )
    perturb_df = pd.DataFrame(perturb_rows)
    atomic_write(perturb_df, PERTURBATION_OUT)

    # ------------------------------------------------------------------
    # PCA dimensionality sensitivity using de-novo PCA on the same standardized feature matrix.
    # This tests dependence on choosing seven retained components; it does not replace the frozen basis.
    # ------------------------------------------------------------------
    pca_rows: list[dict] = []
    for n_components_raw in config["pca_component_sensitivity"]:
        n_components = int(n_components_raw)
        if n_components > min(Xz.shape):
            continue
        pca = PCA(n_components=n_components, svd_solver="full")
        scores = pca.fit_transform(Xz)
        ari_vals = []
        sil_vals = []
        mapped_vals = []
        for run in range(int(config["pca_sensitivity_seed_runs"])):
            seed = int(config["random_seed"]) + (n_components * 1000) + run
            model = KMeans(n_clusters=reference_k, random_state=seed, n_init=10)
            labels = model.fit_predict(scores)
            mapped = map_labels_to_reference(labels, reference_labels)
            ari_vals.append(adjusted_rand_score(reference_labels, labels))
            sil_vals.append(silhouette_score(scores, labels))
            mapped_vals.append(float(np.mean(mapped == reference_labels)))
        pca_rows.append(
            {
                "n_components": n_components,
                "explained_variance": float(np.sum(pca.explained_variance_ratio_)),
                "mean_ari_vs_validated": float(np.mean(ari_vals)),
                "median_ari_vs_validated": float(np.median(ari_vals)),
                "min_ari_vs_validated": float(np.min(ari_vals)),
                "mean_mapped_assignment_agreement": float(np.mean(mapped_vals)),
                "mean_silhouette": float(np.mean(sil_vals)),
                "reference_component_count": n_components == retained,
            }
        )
    pca_df = pd.DataFrame(pca_rows)
    atomic_write(pca_df, PCA_SENSITIVITY_OUT)

    # ------------------------------------------------------------------
    # Leave-one-project-out influence analysis.
    # ------------------------------------------------------------------
    loo_rows: list[dict] = []
    loo_match_counts = np.zeros(len(reference_labels), dtype=int)
    ecosystem_ids = work["ecosystem_id"].astype(str).tolist()
    for omitted_idx, ecosystem_id in enumerate(ecosystem_ids):
        mask = np.ones(len(frozen_scores), dtype=bool)
        mask[omitted_idx] = False
        seed = int(config["random_seed"]) + omitted_idx
        model = KMeans(
            n_clusters=reference_k,
            random_state=seed,
            n_init=int(config["leave_one_out_n_init"]),
        )
        model.fit(frozen_scores[mask])
        labels = model.predict(frozen_scores)
        mapped = map_labels_to_reference(labels, reference_labels)
        loo_match_counts += (mapped == reference_labels).astype(int)
        loo_rows.append(
            {
                "omitted_ecosystem_id": ecosystem_id,
                "ari_vs_validated": adjusted_rand_score(reference_labels, labels),
                "mapped_assignment_agreement": float(np.mean(mapped == reference_labels)),
                "omitted_project_reassigned_to_validated_cluster": bool(mapped[omitted_idx] == reference_labels[omitted_idx]),
            }
        )
    loo_df = pd.DataFrame(loo_rows)
    atomic_write(loo_df, LOO_OUT)

    # ------------------------------------------------------------------
    # Per-project stability register.
    # ------------------------------------------------------------------
    project_stability = pd.DataFrame(
        {
            "ecosystem_id": ecosystem_ids,
            "validated_cluster": reference_labels,
            "seed_assignment_stability": seed_match_counts / int(config["seed_runs"]),
            "leave_one_out_assignment_stability": loo_match_counts / len(ecosystem_ids),
        }
    )
    for fraction in sorted(subsample_match_counts):
        denom = int(config["subsample_runs_per_fraction"])
        project_stability[f"subsample_{int(round(fraction * 100))}_assignment_stability"] = (
            subsample_match_counts[fraction] / denom
        )
    for level in sorted(perturb_match_counts):
        denom = int(config["perturbation_runs_per_level"])
        label = str(level).replace(".", "p")
        project_stability[f"perturb_noise_{label}_assignment_stability"] = perturb_match_counts[level] / denom
    stability_cols = [c for c in project_stability.columns if c.endswith("assignment_stability")]
    project_stability["minimum_observed_assignment_stability"] = project_stability[stability_cols].min(axis=1)
    project_stability["mean_observed_assignment_stability"] = project_stability[stability_cols].mean(axis=1)
    atomic_write(project_stability, PROJECT_STABILITY_OUT)

    # ------------------------------------------------------------------
    # Summary and pre-declared robustness warnings.
    # ------------------------------------------------------------------
    subsample_summary = subsample_df.groupby("fraction")["ari_vs_validated"].agg(["mean", "median", "min"]).reset_index()
    perturb_summary = perturb_df.groupby("standardized_noise_sd").agg(
        mean_ari=("ari_vs_validated", "mean"),
        mean_agreement=("exact_assignment_agreement", "mean"),
        min_agreement=("exact_assignment_agreement", "min"),
    ).reset_index()

    warnings: list[str] = []
    if best_k != reference_k:
        warnings.append(f"REFERENCE_K_NOT_TOP_MEAN_SILHOUETTE:best_k={best_k}")
    if seed_mean_ari < float(thresholds["ari_good"]):
        warnings.append(f"K6_INITIALIZATION_STABILITY_BELOW_GOOD:mean_ari={seed_mean_ari:.6f}")
    if hierarchical_ari < float(thresholds["ari_moderate"]):
        warnings.append(f"HIERARCHICAL_CROSS_METHOD_ARI_BELOW_MODERATE:ari={hierarchical_ari:.6f}")

    row80 = subsample_summary[np.isclose(subsample_summary["fraction"], 0.80)]
    subsample80_mean = float(row80.iloc[0]["mean"]) if not row80.empty else float("nan")
    if np.isfinite(subsample80_mean) and subsample80_mean < float(thresholds["ari_moderate"]):
        warnings.append(f"SUBSAMPLE_80_STABILITY_BELOW_MODERATE:mean_ari={subsample80_mean:.6f}")

    row05 = perturb_summary[np.isclose(perturb_summary["standardized_noise_sd"], 0.05)]
    perturb05_agreement = float(row05.iloc[0]["mean_agreement"]) if not row05.empty else float("nan")
    if np.isfinite(perturb05_agreement) and perturb05_agreement < float(thresholds["assignment_stability_strong"]):
        warnings.append(f"PERTURBATION_005_ASSIGNMENT_STABILITY_BELOW_STRONG:agreement={perturb05_agreement:.6f}")

    loo_mean_ari = float(loo_df["ari_vs_validated"].mean())
    loo_min_ari = float(loo_df["ari_vs_validated"].min())
    if loo_mean_ari < float(thresholds["ari_moderate"]):
        warnings.append(f"LEAVE_ONE_OUT_STABILITY_BELOW_MODERATE:mean_ari={loo_mean_ari:.6f}")

    hard_failures = []
    if not pca_reference_pass:
        hard_failures.append("FROZEN_PCA_REFERENCE_REPRODUCTION_FAILED")
    if not frozen_reference_pass:
        hard_failures.append("FROZEN_NEAREST_CENTROID_REFERENCE_RECOVERY_FAILED")

    status = (
        "FAIL_REFERENCE_REPRODUCTION"
        if hard_failures
        else "PASS_REFERENCE_REPRODUCTION_ROBUSTNESS_REVIEW_COMPLETE"
    )

    ref_k_row = k_selection[k_selection["k"].eq(reference_k)].iloc[0]
    summary = pd.DataFrame(
        [
            {
                "phase": "15C",
                "engine_version": ENGINE_VERSION,
                "status": status,
                "reference_rows": len(frozen_scores),
                "raw_features": len(raw_features),
                "retained_pca_components": retained,
                "reference_k": reference_k,
                "frozen_pc12_max_abs_error": max(pc1_error, pc2_error),
                "frozen_pca_reference_pass": pca_reference_pass,
                "frozen_centroid_ari": frozen_centroid_ari,
                "frozen_exact_assignment_agreement": frozen_exact_agreement,
                "best_k_by_repeated_mean_silhouette": best_k,
                "reference_k_mean_silhouette": float(ref_k_row["mean_silhouette"]),
                "reference_k_mean_pairwise_seed_ari": float(ref_k_row["mean_pairwise_seed_ari"]),
                "k6_single_init_mean_ari_vs_validated": seed_mean_ari,
                "k6_single_init_median_ari_vs_validated": seed_median_ari,
                "k6_single_init_min_ari_vs_validated": seed_min_ari,
                "hierarchical_ward_ari_vs_validated": hierarchical_ari,
                "subsample_80_mean_ari_vs_validated": subsample80_mean,
                "perturbation_005_mean_assignment_agreement": perturb05_agreement,
                "leave_one_out_mean_ari_vs_validated": loo_mean_ari,
                "leave_one_out_min_ari_vs_validated": loo_min_ari,
                "minimum_project_assignment_stability": float(project_stability["minimum_observed_assignment_stability"].min()),
                "seed_stability_interpretation": strength_label(seed_mean_ari, thresholds),
                "hierarchical_agreement_interpretation": strength_label(hierarchical_ari, thresholds),
                "hard_failure_count": len(hard_failures),
                "warning_count": len(warnings),
                "hard_failures": ";".join(hard_failures),
                "warnings": ";".join(warnings),
                "interpretation_guardrail": "STRUCTURAL_CLUSTER_ROBUSTNESS_ONLY_NOT_DEFAULT_PREDICTION_ACCURACY",
                "evaluated_at": utc_now(),
            }
        ]
    )
    atomic_write(summary, SUMMARY_OUT)

    log_payload = summary.iloc[0].to_dict()
    log_payload["guardrails"] = config.get("guardrails", {})
    log_payload["outputs"] = [
        str(p.relative_to(ROOT))
        for p in [
            K_SELECTION_OUT,
            SEED_STABILITY_OUT,
            SUBSAMPLE_OUT,
            PERTURBATION_OUT,
            PCA_SENSITIVITY_OUT,
            LOO_OUT,
            PROJECT_STABILITY_OUT,
            HISTORICAL_COMPARISON_OUT,
            SUMMARY_OUT,
        ]
    ]
    append_jsonl(RUN_LOG, log_payload)

    print("PHASE 15C - STRUCTURAL ML ROBUSTNESS VALIDATION")
    print("=" * 82)
    print(f"Reference rows                     : {len(frozen_scores)}")
    print(f"Frozen structural features        : {len(raw_features)}")
    print(f"Retained PCA components            : {retained}")
    print(f"Reference K                        : {reference_k}")
    print(f"Frozen PCA PC1/PC2 max abs error   : {max(pc1_error, pc2_error):.3e}")
    print(f"Frozen centroid exact agreement    : {frozen_exact_agreement:.6f}")
    print(f"Best K by repeated mean silhouette : {best_k}")
    print(f"K=6 mean silhouette                : {float(ref_k_row['mean_silhouette']):.6f}")
    print(f"K=6 mean seed ARI vs validated     : {seed_mean_ari:.6f}")
    print(f"Ward hierarchical ARI              : {hierarchical_ari:.6f}")
    print(f"80% subsample mean ARI             : {subsample80_mean:.6f}")
    print(f"5% std-noise assignment agreement  : {perturb05_agreement:.6f}")
    print(f"Leave-one-out mean ARI             : {loo_mean_ari:.6f}")
    print(f"Minimum project stability          : {float(project_stability['minimum_observed_assignment_stability'].min()):.6f}")
    print(f"Hard failures                      : {len(hard_failures)}")
    print(f"Research warnings                  : {len(warnings)}")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    print(f"STATUS                             : {status}")
    print(f"Summary                            : {SUMMARY_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: these tests assess structural segmentation robustness. They do not measure default-prediction accuracy and do not create a credit rating, PD, LGD, EAD or ECL.")
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
