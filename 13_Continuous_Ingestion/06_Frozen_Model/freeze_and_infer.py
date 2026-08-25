from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "06_Frozen_Model"
ARTIFACT_DIR = OUT_DIR / "artifacts"

BASELINE_ECOSYSTEM_FILE = (
    ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Ecosystem_Master.csv"
)
CANONICAL_FILE = (
    ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"
)
PCA_LOADINGS_FILE = ROOT / "03_Modeling" / "Phase_3A_PCA_KMeans" / "PCA_Loadings.csv"
PCA_VARIANCE_FILE = ROOT / "03_Modeling" / "Phase_3A_PCA_KMeans" / "PCA_Explained_Variance.csv"
VALIDATED_ASSIGNMENTS_FILE = (
    ROOT / "03_Modeling" / "Phase_3B_Cluster_Validation" / "Validated_Cluster_Assignments.csv"
)

MANIFEST_FILE = ARTIFACT_DIR / "Frozen_Model_Manifest.json"
SCALER_FILE = ARTIFACT_DIR / "Frozen_Scaler_Parameters.csv"
PCA_FILE = ARTIFACT_DIR / "Frozen_PCA_Components.csv"
CENTROID_FILE = ARTIFACT_DIR / "Frozen_Cluster_Centroids.csv"
REFERENCE_SCORE_FILE = ARTIFACT_DIR / "Frozen_Reference_PCA_Scores.csv"
VALIDATION_FILE = ARTIFACT_DIR / "Frozen_Model_Validation.json"
INFERENCE_FILE = OUT_DIR / "Frozen_Model_New_Project_Inference.csv"
AUDIT_FILE = OUT_DIR / "Frozen_Model_Run_Log.jsonl"

MODEL_VERSION = "SCI_STRUCTURAL_CLUSTER_FROZEN_2026_V1"
MODEL_SCOPE = "STRUCTURAL_PROJECT_SEGMENTATION_ONLY"

RAW_FEATURES = [
    "financial_rank_within_scope",
    "state_financial_share_within_scope",
    "company_project_count",
    "is_manufacturing",
    "is_fab",
    "is_osat",
    "is_ai_related",
    "is_telecom_related",
    "is_automotive_related",
    "is_iot_related",
    "is_medical_related",
    "has_technology_partner",
]

EXPECTED_BASELINE_POSITIVE_COUNTS = {
    "is_manufacturing": 12,
    "is_fab": 3,
    "is_osat": 6,
    "is_ai_related": 5,
    "is_telecom_related": 6,
    "is_automotive_related": 3,
    "is_iot_related": 4,
    "is_medical_related": 2,
    "has_technology_partner": 6,
}

RANK_RECIPES = [
    ("rank_desc", False, False),
    ("rank_asc", True, False),
    ("pct_desc", False, True),
    ("pct_asc", True, True),
]

INFERENCE_COLUMNS = [
    "project_id",
    "company",
    "state",
    "project_type",
    "project_type_standardized",
    "investment_crore",
    "predicted_validated_cluster",
    "distance_to_cluster_centroid",
    "reference_cluster_p95_radius",
    "distance_to_p95_ratio",
    "structural_extrapolation_signal",
    "PC1",
    "PC2",
    "PC3",
    "PC4",
    "PC5",
    "PC6",
    "PC7",
    "model_version",
    "model_scope",
    "model_evaluation_status",
    "credit_interpretation",
    "inference_universe_rows",
    "evaluated_at",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(value)).strip()


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def write_json_atomic(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def append_audit(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_blob(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ["project_name", "technology", "application", "project_type"] if c in df.columns]
    if not cols:
        return pd.Series("", index=df.index, dtype=str)
    out = pd.Series("", index=df.index, dtype=str)
    for col in cols:
        out = out + " " + df[col].fillna("").astype(str)
    return out.str.lower().str.replace(r"\s+", " ", regex=True)


def contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.str.contains(pattern, regex=True, case=False, na=False)


def build_raw_features(ecosystem: pd.DataFrame, rank_name: str, ascending: bool, pct: bool) -> pd.DataFrame:
    df = ecosystem.copy()
    required = [
        "ecosystem_id",
        "project_scope",
        "company",
        "state",
        "financial_measure_crore",
        "project_type_standardized",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Baseline ecosystem is missing required columns: {missing}")

    financial = pd.to_numeric(df["financial_measure_crore"], errors="coerce")
    if financial.isna().any():
        bad = df.loc[financial.isna(), "ecosystem_id"].astype(str).tolist()
        raise ValueError(f"financial_measure_crore missing for ecosystem rows: {bad}")

    df["financial_rank_within_scope"] = financial.groupby(df["project_scope"]).rank(
        method="average", ascending=ascending, pct=pct
    )

    state_total = financial.groupby([df["project_scope"], df["state"]]).transform("sum")
    scope_total = financial.groupby(df["project_scope"]).transform("sum")
    df["state_financial_share_within_scope"] = state_total / scope_total

    df["company_project_count"] = df.groupby("company")["ecosystem_id"].transform("count").astype(float)
    df["is_manufacturing"] = df["project_scope"].astype(str).eq("Manufacturing").astype(float)
    df["is_fab"] = df["project_type_standardized"].astype(str).eq("FAB").astype(float)
    df["is_osat"] = df["project_type_standardized"].astype(str).eq("OSAT").astype(float)

    blob = text_blob(df)
    df["is_ai_related"] = contains(
        blob,
        r"artificial intelligence|ai accelerator|edge[- ]?ai|\bai\b|machine learning|\bml acceleration\b",
    ).astype(float)
    df["is_telecom_related"] = contains(
        blob,
        r"telecommunications|telecom|\b5g\b|\b4g\b|\blte\b|nb[- ]?iot|broadband|gpon|fttx|satcom|satellite communication|rf/radar|\brf\b|\bradar\b",
    ).astype(float)
    df["is_automotive_related"] = contains(
        blob,
        r"automotive|automobile|\btire\b|motor control",
    ).astype(float)
    df["is_iot_related"] = contains(blob, r"\biot\b|nb[- ]?iot").astype(float)
    df["is_medical_related"] = contains(blob, r"medical|cardiac|health").astype(float)

    tech_partner = df.get("technology_partner", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
    df["has_technology_partner"] = tech_partner.ne("").astype(float)

    out = df[["ecosystem_id"] + RAW_FEATURES].copy()
    for feature in RAW_FEATURES:
        out[feature] = pd.to_numeric(out[feature], errors="coerce")
    if out[RAW_FEATURES].isna().any().any():
        missing_fields = out[RAW_FEATURES].columns[out[RAW_FEATURES].isna().any()].tolist()
        raise ValueError(f"Feature engineering created missing values: {missing_fields}")
    out.attrs["rank_recipe"] = rank_name
    return out


def baseline_binary_count_check(raw: pd.DataFrame) -> dict:
    observed = {feature: int(raw[feature].sum()) for feature in EXPECTED_BASELINE_POSITIVE_COUNTS}
    mismatches = {
        feature: {"expected": expected, "observed": observed[feature]}
        for feature, expected in EXPECTED_BASELINE_POSITIVE_COUNTS.items()
        if observed[feature] != expected
    }
    return {"observed": observed, "mismatches": mismatches, "pass": not mismatches}


def standardize_reference(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    x = raw[RAW_FEATURES].astype(float)
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    if (scales <= 0).any():
        bad = scales[scales <= 0].index.tolist()
        raise ValueError(f"Zero-variance reference features: {bad}")
    z = (x - means) / scales
    z.columns = RAW_FEATURES
    return z, means, scales


def load_pca_components() -> tuple[pd.DataFrame, list[str]]:
    loadings = read_csv(PCA_LOADINGS_FILE, index_col=0)
    loadings.index = [str(i).replace("z_", "", 1) if str(i).startswith("z_") else str(i) for i in loadings.index]
    component_cols = [c for c in loadings.columns if re.fullmatch(r"PC\d+", str(c))]
    component_cols = sorted(component_cols, key=lambda c: int(str(c)[2:]))
    if set(loadings.index) != set(RAW_FEATURES):
        raise ValueError(
            "PCA loading features do not match the frozen feature contract. "
            f"loadings={list(loadings.index)} expected={RAW_FEATURES}"
        )
    if len(component_cols) != 7:
        raise ValueError(f"Expected 7 retained PCA components, found {len(component_cols)}")
    return loadings.loc[RAW_FEATURES, component_cols].astype(float), component_cols


def project_scores(z: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    values = z[RAW_FEATURES].to_numpy(dtype=float) @ components.to_numpy(dtype=float)
    return pd.DataFrame(values, columns=components.columns, index=z.index)


def validate_recipe(
    ecosystem: pd.DataFrame,
    assignments: pd.DataFrame,
    components: pd.DataFrame,
    rank_name: str,
    ascending: bool,
    pct: bool,
) -> dict:
    raw = build_raw_features(ecosystem, rank_name, ascending, pct)
    binary_check = baseline_binary_count_check(raw)
    z, means, scales = standardize_reference(raw)
    scores = project_scores(z, components)
    scores.insert(0, "ecosystem_id", raw["ecosystem_id"].values)

    observed = assignments[["ecosystem_id", "PC1", "PC2", "validated_cluster"]].copy()
    merged = scores.merge(observed, on="ecosystem_id", how="inner", suffixes=("_calc", "_stored"))
    if len(merged) != len(ecosystem):
        raise ValueError(
            f"Reference score validation joined {len(merged)} rows, expected {len(ecosystem)}"
        )

    diffs = []
    for pc in ["PC1", "PC2"]:
        diff = merged[f"{pc}_calc"] - pd.to_numeric(merged[f"{pc}_stored"], errors="coerce")
        diffs.extend(diff.abs().tolist())

    mae = float(np.mean(diffs)) if diffs else float("inf")
    max_abs = float(np.max(diffs)) if diffs else float("inf")
    return {
        "rank_recipe": rank_name,
        "ascending": ascending,
        "pct": pct,
        "binary_check": binary_check,
        "pc12_mae": mae,
        "pc12_max_abs": max_abs,
        "raw": raw,
        "z": z,
        "means": means,
        "scales": scales,
        "scores": scores,
    }


def nearest_cluster(scores: np.ndarray, centroids: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    centroid_values = centroids[[c for c in centroids.columns if re.fullmatch(r"PC\d+", c)]].to_numpy(dtype=float)
    labels = centroids["validated_cluster"].to_numpy()
    distances = np.linalg.norm(scores[:, None, :] - centroid_values[None, :, :], axis=2)
    idx = distances.argmin(axis=1)
    return labels[idx], distances[np.arange(len(scores)), idx]


def build_centroids(reference_scores: pd.DataFrame, assignments: pd.DataFrame, component_cols: list[str]) -> tuple[pd.DataFrame, float]:
    merged = reference_scores.merge(
        assignments[["ecosystem_id", "validated_cluster"]], on="ecosystem_id", how="inner"
    )
    merged["validated_cluster"] = pd.to_numeric(merged["validated_cluster"], errors="raise").astype(int)

    centroids = merged.groupby("validated_cluster", as_index=False)[component_cols].mean()
    predicted, distance = nearest_cluster(merged[component_cols].to_numpy(dtype=float), centroids)
    agreement = float(np.mean(predicted.astype(int) == merged["validated_cluster"].to_numpy(dtype=int)))

    merged["distance_to_own_centroid"] = distance
    radii = (
        merged.groupby("validated_cluster")["distance_to_own_centroid"]
        .quantile(0.95)
        .rename("reference_cluster_p95_radius")
        .reset_index()
    )
    counts = merged.groupby("validated_cluster").size().rename("reference_cluster_size").reset_index()
    centroids = centroids.merge(radii, on="validated_cluster", how="left").merge(counts, on="validated_cluster", how="left")
    return centroids, agreement


def reference_hashes() -> dict:
    return {
        "baseline_ecosystem_sha256": sha256_file(BASELINE_ECOSYSTEM_FILE),
        "pca_loadings_sha256": sha256_file(PCA_LOADINGS_FILE),
        "validated_assignments_sha256": sha256_file(VALIDATED_ASSIGNMENTS_FILE),
        "pca_variance_sha256": sha256_file(PCA_VARIANCE_FILE),
    }


def cumulative_variance_component_7() -> float | None:
    try:
        variance = read_csv(PCA_VARIANCE_FILE)
        row = variance[pd.to_numeric(variance["component"], errors="coerce").eq(7)]
        if not row.empty:
            return float(row.iloc[0]["cumulative_variance"])
    except Exception:
        return None
    return None


def freeze_reference_model(rebuild: bool = False) -> dict:
    ecosystem = read_csv(BASELINE_ECOSYSTEM_FILE)
    assignments = read_csv(VALIDATED_ASSIGNMENTS_FILE)
    components, component_cols = load_pca_components()

    if len(ecosystem) != 36:
        raise RuntimeError(
            f"Frozen reference universe expected 36 baseline ecosystem rows, found {len(ecosystem)}. "
            "Reference drift review is required before freezing."
        )

    recipes = []
    for rank_name, ascending, pct in RANK_RECIPES:
        result = validate_recipe(ecosystem, assignments, components, rank_name, ascending, pct)
        recipes.append(result)

    best = min(recipes, key=lambda x: (x["pc12_max_abs"], x["pc12_mae"]))
    reconstruction_pass = bool(best["binary_check"]["pass"] and best["pc12_max_abs"] <= 1e-6)

    validation_summary = {
        "model_version": MODEL_VERSION,
        "validated_at": utc_now(),
        "reference_rows": int(len(ecosystem)),
        "retained_components": len(component_cols),
        "selected_rank_recipe": best["rank_recipe"],
        "pc12_mae": best["pc12_mae"],
        "pc12_max_abs": best["pc12_max_abs"],
        "binary_feature_check": best["binary_check"],
        "recipe_diagnostics": [
            {
                "rank_recipe": r["rank_recipe"],
                "pc12_mae": r["pc12_mae"],
                "pc12_max_abs": r["pc12_max_abs"],
                "binary_feature_check_pass": r["binary_check"]["pass"],
            }
            for r in recipes
        ],
        "pca_reconstruction_pass": reconstruction_pass,
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    if not reconstruction_pass:
        validation_summary["status"] = "FAIL_REFERENCE_RECONSTRUCTION"
        write_json_atomic(validation_summary, VALIDATION_FILE)
        raise RuntimeError(
            "Phase 13E refused to freeze the model because the reconstructed baseline does not reproduce "
            "the stored PCA scores exactly enough. Review Frozen_Model_Validation.json; no inference was performed."
        )

    centroids, cluster_agreement = build_centroids(best["scores"], assignments, component_cols)
    validation_summary["nearest_centroid_training_agreement"] = cluster_agreement
    validation_summary["cluster_recovery_pass"] = bool(cluster_agreement >= 0.999999)

    if cluster_agreement < 0.999999:
        validation_summary["status"] = "FAIL_CLUSTER_RECOVERY"
        write_json_atomic(validation_summary, VALIDATION_FILE)
        raise RuntimeError(
            "Phase 13E reproduced the PCA projection but could not recover the validated clusters from frozen "
            "7D centroids with full agreement. No inference was performed."
        )

    hashes = reference_hashes()
    if MANIFEST_FILE.exists() and not rebuild:
        existing = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        if existing.get("reference_hashes") != hashes:
            raise RuntimeError(
                "Frozen reference inputs changed after the model manifest was created. "
                "Do not overwrite automatically; perform a model-version review first."
            )

    scaler = pd.DataFrame({
        "feature": RAW_FEATURES,
        "mean": [float(best["means"][f]) for f in RAW_FEATURES],
        "scale_ddof0": [float(best["scales"][f]) for f in RAW_FEATURES],
    })

    pca_export = components.copy()
    pca_export.insert(0, "feature", pca_export.index)
    reference_scores = best["scores"].copy()
    reference_scores = reference_scores.merge(
        assignments[["ecosystem_id", "validated_cluster"]], on="ecosystem_id", how="left"
    )

    manifest = {
        "model_version": MODEL_VERSION,
        "model_scope": MODEL_SCOPE,
        "frozen_at": existing.get("frozen_at") if MANIFEST_FILE.exists() and not rebuild else utc_now(),
        "reference_universe_rows": int(len(ecosystem)),
        "reference_manufacturing_rows": int(ecosystem["project_scope"].astype(str).eq("Manufacturing").sum()),
        "validated_cluster_count": int(assignments["validated_cluster"].nunique()),
        "retained_pca_components": len(component_cols),
        "cumulative_variance_through_pc7": cumulative_variance_component_7(),
        "selected_rank_recipe": best["rank_recipe"],
        "raw_features": RAW_FEATURES,
        "reference_hashes": hashes,
        "inference_rule": "Frozen ddof=0 scaler + stored PCA loadings + nearest validated 7D cluster centroid",
        "cohort_relative_feature_rule": (
            "For a newly canonicalized project, rank/state-share/company-count features are calculated on the "
            "current ecosystem universe, while scaler/PCA/cluster parameters remain frozen to the 36-row reference model."
        ),
        "governance": [
            "Structural cluster assignment only; not a risk class, bank rating, PD, LGD, EAD or ECL.",
            "No automatic credit approval or rejection.",
            "Out-of-distribution distance triggers review rather than an invented risk score.",
        ],
    }

    write_csv_atomic(scaler, SCALER_FILE)
    write_csv_atomic(pca_export.reset_index(drop=True), PCA_FILE)
    write_csv_atomic(centroids, CENTROID_FILE)
    write_csv_atomic(reference_scores, REFERENCE_SCORE_FILE)
    validation_summary["status"] = "PASS_FROZEN_REFERENCE_REPRODUCED"
    write_json_atomic(validation_summary, VALIDATION_FILE)
    write_json_atomic(manifest, MANIFEST_FILE)

    return {
        "manifest": manifest,
        "raw_reference": best["raw"],
        "means": best["means"],
        "scales": best["scales"],
        "components": components,
        "component_cols": component_cols,
        "centroids": centroids,
        "validation": validation_summary,
        "baseline_ecosystem": ecosystem,
    }


def canonical_new_projects(canonical: pd.DataFrame, baseline_ecosystem: pd.DataFrame) -> pd.DataFrame:
    baseline_ids = set(
        baseline_ecosystem.loc[
            baseline_ecosystem["project_scope"].astype(str).eq("Manufacturing"), "source_project_id"
        ].astype(str)
    )
    return canonical[~canonical["project_id"].astype(str).isin(baseline_ids)].copy()


def canonical_to_ecosystem_rows(new_projects: pd.DataFrame, ecosystem_columns: list[str]) -> pd.DataFrame:
    rows = []
    for _, r in new_projects.iterrows():
        investment = pd.to_numeric(pd.Series([r.get("investment_crore")]), errors="coerce").iloc[0]
        if pd.isna(investment) or investment <= 0:
            raise ValueError(f"New canonical project {r.get('project_id')} has invalid investment_crore")

        rec = {c: pd.NA for c in ecosystem_columns}
        project_id = clean(r.get("project_id"))
        rec.update({
            "ecosystem_id": f"LIVE-{project_id}",
            "source_project_id": project_id,
            "project_scope": "Manufacturing",
            "company": clean(r.get("company")),
            "project_name": "",
            "project_type": clean(r.get("project_type")),
            "project_type_standardized": clean(r.get("project_type_standardized")),
            "project_group": clean(r.get("project_group")),
            "scheme": "India Semiconductor Mission",
            "state": clean(r.get("state")),
            "approval_date": clean(r.get("approval_date")),
            "approval_year": r.get("approval_year"),
            "investment_crore": investment,
            "project_outlay_crore": pd.NA,
            "financial_measure_type": "Manufacturing Project Investment",
            "financial_measure_crore": investment,
            "capacity_value": r.get("capacity_value"),
            "capacity_unit": clean(r.get("capacity_unit")),
            "capacity_category": clean(r.get("capacity_category")),
            "technology": clean(r.get("technology")),
            "technology_partner": clean(r.get("technology_partner")),
            "application": "",
            "chip_node": "",
            "source_document": clean(r.get("source_document")),
            "source_url": "",
            "source_authority": clean(r.get("source")),
            "data_quality_flag": clean(r.get("data_quality_flag")),
        })
        rows.append(rec)

    return pd.DataFrame(rows, columns=ecosystem_columns)


def infer_new_projects(frozen: dict) -> pd.DataFrame:
    canonical = read_csv(CANONICAL_FILE)
    baseline = frozen["baseline_ecosystem"].copy()
    new_projects = canonical_new_projects(canonical, baseline)

    if new_projects.empty:
        out = pd.DataFrame(columns=INFERENCE_COLUMNS)
        write_csv_atomic(out, INFERENCE_FILE)
        return out

    new_ecosystem = canonical_to_ecosystem_rows(new_projects, list(baseline.columns))
    universe = pd.concat([baseline, new_ecosystem], ignore_index=True)

    recipe_lookup = {name: (ascending, pct) for name, ascending, pct in RANK_RECIPES}
    recipe = frozen["manifest"]["selected_rank_recipe"]
    if recipe not in recipe_lookup:
        raise RuntimeError(f"Unknown frozen rank recipe: {recipe}")
    ascending, pct = recipe_lookup[recipe]

    raw_all = build_raw_features(universe, recipe, ascending, pct)
    new_ids = set(new_ecosystem["ecosystem_id"].astype(str))
    new_raw = raw_all[raw_all["ecosystem_id"].astype(str).isin(new_ids)].copy()
    new_raw = new_raw.set_index("ecosystem_id")

    means = frozen["means"]
    scales = frozen["scales"]
    z = (new_raw[RAW_FEATURES] - means[RAW_FEATURES]) / scales[RAW_FEATURES]
    scores = project_scores(z, frozen["components"])

    centroids = frozen["centroids"].copy()
    predicted, distance = nearest_cluster(scores[frozen["component_cols"]].to_numpy(dtype=float), centroids)
    radius_map = centroids.set_index("validated_cluster")["reference_cluster_p95_radius"].to_dict()

    project_by_ecosystem = new_ecosystem.set_index("ecosystem_id")
    rows = []
    for i, ecosystem_id in enumerate(scores.index):
        src = project_by_ecosystem.loc[ecosystem_id]
        cluster = int(predicted[i])
        d = float(distance[i])
        radius = float(radius_map.get(cluster, np.nan))
        ratio = d / radius if np.isfinite(radius) and radius > 0 else np.nan
        extrapolation = (
            "STRUCTURAL_EXTRAPOLATION_REVIEW_REQUIRED"
            if np.isfinite(radius) and d > radius
            else "WITHIN_REFERENCE_CLUSTER_RADIUS"
        )

        row = {
            "project_id": clean(src.get("source_project_id")),
            "company": clean(src.get("company")),
            "state": clean(src.get("state")),
            "project_type": clean(src.get("project_type")),
            "project_type_standardized": clean(src.get("project_type_standardized")),
            "investment_crore": float(src.get("financial_measure_crore")),
            "predicted_validated_cluster": cluster,
            "distance_to_cluster_centroid": d,
            "reference_cluster_p95_radius": radius,
            "distance_to_p95_ratio": ratio,
            "structural_extrapolation_signal": extrapolation,
            **{pc: float(scores.loc[ecosystem_id, pc]) for pc in frozen["component_cols"]},
            "model_version": MODEL_VERSION,
            "model_scope": MODEL_SCOPE,
            "model_evaluation_status": "STRUCTURAL_MODEL_EVALUATED",
            "credit_interpretation": "NOT_A_CREDIT_RATING_OR_DEFAULT_PROBABILITY",
            "inference_universe_rows": int(len(universe)),
            "evaluated_at": utc_now(),
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    for c in INFERENCE_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[INFERENCE_COLUMNS]
    write_csv_atomic(out, INFERENCE_FILE)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze/reproduce the validated structural model and infer newly canonicalized manufacturing projects."
    )
    parser.add_argument(
        "--rebuild-freeze",
        action="store_true",
        help="Rebuild frozen artifacts only after the reference-reproduction checks pass.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = utc_now()
    try:
        frozen = freeze_reference_model(rebuild=args.rebuild_freeze)
        inference = infer_new_projects(frozen)

        summary = {
            "run_at": utc_now(),
            "phase": "13E",
            "status": "SUCCESS",
            "model_version": MODEL_VERSION,
            "reference_rows": frozen["manifest"]["reference_universe_rows"],
            "retained_components": frozen["manifest"]["retained_pca_components"],
            "selected_rank_recipe": frozen["manifest"]["selected_rank_recipe"],
            "pc12_max_abs_reconstruction_error": frozen["validation"]["pc12_max_abs"],
            "nearest_centroid_training_agreement": frozen["validation"]["nearest_centroid_training_agreement"],
            "new_canonical_projects_evaluated": int(len(inference)),
            "inference_output": str(INFERENCE_FILE.relative_to(ROOT)),
        }
        append_audit(summary)

        print("PHASE 13E - FROZEN STRUCTURAL MODEL INFERENCE")
        print("=" * 64)
        print(f"Model version                 : {MODEL_VERSION}")
        print(f"Reference rows                : {summary['reference_rows']}")
        print(f"Retained PCA components       : {summary['retained_components']}")
        print(f"Selected rank recipe          : {summary['selected_rank_recipe']}")
        print(f"PC1/PC2 max reconstruction err: {summary['pc12_max_abs_reconstruction_error']:.12g}")
        print(f"Cluster recovery agreement    : {summary['nearest_centroid_training_agreement']:.6f}")
        print(f"New canonical projects        : {len(inference)}")
        print(f"Inference output              : {INFERENCE_FILE.relative_to(ROOT)}")
        if inference.empty:
            print("No newly canonicalized manufacturing projects require inference yet.")
        else:
            print("\nNEW PROJECT STRUCTURAL INFERENCE")
            for _, row in inference.iterrows():
                print(
                    f"- {row['project_id']} | {row['company']} | cluster={row['predicted_validated_cluster']} "
                    f"| distance={row['distance_to_cluster_centroid']:.4f} "
                    f"| {row['structural_extrapolation_signal']}"
                )
        print("\nInterpretation: structural segment only; not a bank rating, PD, LGD, EAD or ECL.")
        return 0

    except Exception as exc:
        payload = {
            "run_at": utc_now(),
            "phase": "13E",
            "status": "FAILED_SAFE",
            "started_at": started,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        append_audit(payload)
        print("PHASE 13E - FAILED SAFE", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
