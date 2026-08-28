from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "15_Validation_and_Evidence" / "04_Benchmark_Ablation"
CONFIG_FILE = ROOT / "15_Validation_and_Evidence" / "00_Config" / "benchmark_ablation_validation_config.json"
BENCHMARK_FILE = ROOT / "03_Modeling" / "Phase_6A_Benchmark_Ablation" / "Benchmark_Model_Rankings.csv"
HIST_ABLATION_FILE = ROOT / "03_Modeling" / "Phase_6A_Benchmark_Ablation" / "Ablation_Rank_Stability.csv"

BASELINE_OUT = PHASE_DIR / "Baseline_Hybrid_Reproduction.csv"
SCENARIO_OUT = PHASE_DIR / "Benchmark_Weight_Scenarios.csv"
ABLATION_OUT = PHASE_DIR / "Expanded_Family_Ablation.csv"
RANDOM_OUT = PHASE_DIR / "Random_Weight_Sensitivity.csv"
PROJECT_STABILITY_OUT = PHASE_DIR / "Project_Rank_Stability.csv"
NOISE_OUT = PHASE_DIR / "Score_Noise_Sensitivity.csv"
SUMMARY_OUT = PHASE_DIR / "Benchmark_Validation_Summary.csv"
RUN_LOG = PHASE_DIR / "Phase_15D_Run_Log.jsonl"

ENGINE_VERSION = "SCI_BENCHMARK_ABLATION_VALIDATION_V1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def normalize_weights(weights: dict[str, float], families: list[str]) -> dict[str, float]:
    vals = {f: float(weights.get(f, 0.0)) for f in families}
    total = sum(vals.values())
    if total <= 0:
        raise ValueError("Weight vector must have positive total weight")
    return {f: vals[f] / total for f in families}


def score_from_weights(df: pd.DataFrame, families: list[str], score_cols: dict[str, str], weights: dict[str, float]) -> pd.Series:
    w = normalize_weights(weights, families)
    out = pd.Series(0.0, index=df.index, dtype=float)
    for family in families:
        out = out + pd.to_numeric(df[score_cols[family]], errors="raise").astype(float) * w[family]
    return out


def descending_rank(scores: pd.Series) -> pd.Series:
    return scores.rank(method="min", ascending=False).astype(float)


def rank_metrics(reference_rank: pd.Series, candidate_rank: pd.Series, top_n: int = 3) -> dict:
    rho = float(spearmanr(reference_rank.astype(float), candidate_rank.astype(float)).statistic)
    ref_top = set(reference_rank.nsmallest(top_n).index)
    cand_top = set(candidate_rank.nsmallest(top_n).index)
    retention = len(ref_top & cand_top) / max(1, len(ref_top))
    abs_change = (candidate_rank.astype(float) - reference_rank.astype(float)).abs()
    return {
        "spearman_vs_baseline": rho,
        "mean_absolute_rank_change": float(abs_change.mean()),
        "maximum_rank_change": float(abs_change.max()),
        "top3_retention": float(retention),
    }


def scenario_row(name: str, weights: dict[str, float], df: pd.DataFrame, families: list[str], score_cols: dict[str, str], baseline_rank: pd.Series) -> tuple[dict, pd.Series]:
    w = normalize_weights(weights, families)
    score = score_from_weights(df, families, score_cols, w)
    rank = descending_rank(score)
    metrics = rank_metrics(baseline_rank, rank)
    row = {"scenario": name, **{f"weight_{f}": w[f] for f in families}, **metrics}
    return row, rank


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError("Phase 15D config version mismatch")

    df = read_csv(BENCHMARK_FILE)
    hist_ablation = read_csv(HIST_ABLATION_FILE)
    families = list(config["family_score_columns"].keys())
    score_cols = config["family_score_columns"]
    required = ["project_id", "company", "full_hybrid_score", "full_hybrid_rank"] + list(score_cols.values())
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Benchmark file missing required columns: {missing}")

    baseline_weights = normalize_weights(config["baseline_weights"], families)
    stored_score = pd.to_numeric(df["full_hybrid_score"], errors="raise").astype(float)
    stored_rank = pd.to_numeric(df["full_hybrid_rank"], errors="raise").astype(float)
    calc_score = score_from_weights(df, families, score_cols, baseline_weights)
    calc_rank = descending_rank(calc_score)
    score_err = (calc_score - stored_score).abs()
    rank_err = (calc_rank - stored_rank).abs()

    baseline = df[["project_id", "company", "full_hybrid_score", "full_hybrid_rank"]].copy()
    baseline["recomputed_full_hybrid_score"] = calc_score
    baseline["score_abs_error"] = score_err
    baseline["recomputed_full_hybrid_rank"] = calc_rank
    baseline["rank_abs_error"] = rank_err
    atomic_write(baseline, BASELINE_OUT)

    max_score_err = float(score_err.max())
    max_rank_err = float(rank_err.max())
    threshold = float(config["review_thresholds"]["baseline_reconstruction_max_abs_error"])
    baseline_pass = bool(max_score_err <= threshold and max_rank_err == 0)

    scenario_rows = []
    scenario_rank_vectors: dict[str, pd.Series] = {}
    base_row, base_rank = scenario_row("CONFIGURED_BASELINE", baseline_weights, df, families, score_cols, stored_rank)
    scenario_rows.append(base_row)
    scenario_rank_vectors["CONFIGURED_BASELINE"] = base_rank

    for name, weights in config.get("named_weight_scenarios", {}).items():
        row, rank = scenario_row(name, weights, df, families, score_cols, stored_rank)
        scenario_rows.append(row)
        scenario_rank_vectors[name] = rank

    for family in families:
        for multiplier in config.get("one_at_a_time_weight_multipliers", []):
            weights = dict(baseline_weights)
            weights[family] *= float(multiplier)
            name = f"OAT_{family}_X{multiplier}"
            row, rank = scenario_row(name, weights, df, families, score_cols, stored_rank)
            scenario_rows.append(row)
            scenario_rank_vectors[name] = rank

    scenario_df = pd.DataFrame(scenario_rows)
    atomic_write(scenario_df, SCENARIO_OUT)

    ablation_rows = []
    ablation_rank_vectors: dict[str, pd.Series] = {}
    historical_map = {}
    if not hist_ablation.empty and "removed_feature_family" in hist_ablation.columns:
        historical_map = hist_ablation.set_index("removed_feature_family").to_dict(orient="index")

    for family in families:
        weights = dict(baseline_weights)
        weights[family] = 0.0
        row, rank = scenario_row(f"REMOVE_{family}", weights, df, families, score_cols, stored_rank)
        hist = historical_map.get(family, {})
        row.update({
            "removed_feature_family": family,
            "historical_spearman_vs_full": hist.get("spearman_vs_full", pd.NA),
            "historical_mean_absolute_rank_change": hist.get("mean_absolute_rank_change", pd.NA),
            "historical_maximum_rank_change": hist.get("maximum_rank_change", pd.NA),
            "comparison_note": "Phase15D recomputes ablation from the stored family-score integration contract; historical Phase6A values may reflect the original ablation implementation and are retained for comparison, not overwritten.",
        })
        ablation_rows.append(row)
        ablation_rank_vectors[family] = rank
    ablation_df = pd.DataFrame(ablation_rows)
    atomic_write(ablation_df, ABLATION_OUT)

    random_cfg = config["random_weight_tests"]
    rng = np.random.default_rng(int(random_cfg["seed"]))
    baseline_vec = np.array([baseline_weights[f] for f in families], dtype=float)
    random_rows = []
    project_rank_samples = {idx: [] for idx in df.index}

    for regime, draws_key, conc_key in [
        ("CENTERED", "centered_draws", "centered_concentration"),
        ("BROAD", "broad_draws", "broad_concentration"),
    ]:
        draws = int(random_cfg[draws_key])
        concentration = float(random_cfg[conc_key])
        alpha = np.clip(baseline_vec * concentration, 1e-6, None)
        for i, vec in enumerate(rng.dirichlet(alpha, size=draws)):
            weights = {f: float(vec[j]) for j, f in enumerate(families)}
            score = score_from_weights(df, families, score_cols, weights)
            rank = descending_rank(score)
            metrics = rank_metrics(stored_rank, rank)
            random_rows.append({
                "regime": regime,
                "draw": i + 1,
                **{f"weight_{f}": weights[f] for f in families},
                **metrics,
            })
            for idx in df.index:
                project_rank_samples[idx].append(float(rank.loc[idx]))

    random_df = pd.DataFrame(random_rows)
    atomic_write(random_df, RANDOM_OUT)

    project_rows = []
    for idx, row in df.iterrows():
        samples = np.array(project_rank_samples[idx], dtype=float)
        base_rank_value = float(stored_rank.loc[idx])
        project_rows.append({
            "project_id": row["project_id"],
            "company": row["company"],
            "baseline_rank": base_rank_value,
            "mean_random_weight_rank": float(samples.mean()),
            "median_random_weight_rank": float(np.median(samples)),
            "p05_rank": float(np.quantile(samples, 0.05)),
            "p95_rank": float(np.quantile(samples, 0.95)),
            "random_weight_rank_range_p05_p95": float(np.quantile(samples, 0.95) - np.quantile(samples, 0.05)),
            "probability_top3_under_random_weights": float(np.mean(samples <= 3)),
            "probability_within_2_ranks_of_baseline": float(np.mean(np.abs(samples - base_rank_value) <= 2)),
        })
    project_df = pd.DataFrame(project_rows)
    atomic_write(project_df, PROJECT_STABILITY_OUT)

    noise_cfg = config["score_noise_tests"]
    noise_rng = np.random.default_rng(int(noise_cfg["seed"]))
    reps = int(noise_cfg["replicates_per_level"])
    family_matrix = np.column_stack([pd.to_numeric(df[score_cols[f]], errors="raise").astype(float).to_numpy() for f in families])
    family_ranges = np.ptp(family_matrix, axis=0)
    baseline_weight_vec = np.array([baseline_weights[f] for f in families], dtype=float)
    noise_rows = []
    for level in noise_cfg["noise_std_fraction_of_score_range"]:
        level = float(level)
        rhos, macs, maxcs, top3s = [], [], [], []
        for _ in range(reps):
            eps = noise_rng.normal(0.0, family_ranges * level, size=family_matrix.shape)
            noisy = np.clip(family_matrix + eps, 0.0, 100.0)
            score = pd.Series(noisy @ baseline_weight_vec, index=df.index)
            rank = descending_rank(score)
            m = rank_metrics(stored_rank, rank)
            rhos.append(m["spearman_vs_baseline"])
            macs.append(m["mean_absolute_rank_change"])
            maxcs.append(m["maximum_rank_change"])
            top3s.append(m["top3_retention"])
        noise_rows.append({
            "noise_std_fraction_of_score_range": level,
            "replicates": reps,
            "mean_spearman": float(np.mean(rhos)),
            "p05_spearman": float(np.quantile(rhos, 0.05)),
            "mean_absolute_rank_change": float(np.mean(macs)),
            "mean_maximum_rank_change": float(np.mean(maxcs)),
            "mean_top3_retention": float(np.mean(top3s)),
        })
    noise_df = pd.DataFrame(noise_rows)
    atomic_write(noise_df, NOISE_OUT)

    warnings = []
    thresholds = config["review_thresholds"]
    random_mean_rho = float(random_df["spearman_vs_baseline"].mean())
    random_mean_top3 = float(random_df["top3_retention"].mean())
    max_project_p90_range = float(project_df["random_weight_rank_range_p05_p95"].max())
    if random_mean_rho < float(thresholds["random_weight_mean_spearman_warning_below"]):
        warnings.append("RANDOM_WEIGHT_RANK_CORRELATION_BELOW_REVIEW_THRESHOLD")
    if random_mean_top3 < float(thresholds["random_weight_mean_top3_retention_warning_below"]):
        warnings.append("RANDOM_WEIGHT_TOP3_RETENTION_BELOW_REVIEW_THRESHOLD")
    if max_project_p90_range > float(thresholds["project_mean_rank_range_warning_above"]):
        warnings.append("PROJECT_RANK_WEIGHT_SENSITIVITY_REQUIRES_DISCUSSION")

    row5 = noise_df[np.isclose(noise_df["noise_std_fraction_of_score_range"], 0.05)]
    noise5_rho = float(row5.iloc[0]["mean_spearman"]) if not row5.empty else np.nan
    if not np.isnan(noise5_rho) and noise5_rho < float(thresholds["noise_5pct_mean_spearman_warning_below"]):
        warnings.append("FIVE_PERCENT_SCORE_NOISE_STABILITY_BELOW_REVIEW_THRESHOLD")

    status = "PASS_BENCHMARK_REPRODUCTION_SENSITIVITY_REVIEW_COMPLETE" if baseline_pass else "FAIL_BASELINE_BENCHMARK_REPRODUCTION"
    summary = pd.DataFrame([
        {"metric": "reference_projects", "value": len(df), "status": "INFO"},
        {"metric": "feature_families", "value": len(families), "status": "INFO"},
        {"metric": "baseline_reconstruction_max_abs_error", "value": max_score_err, "status": "PASS" if max_score_err <= threshold else "FAIL"},
        {"metric": "baseline_rank_max_abs_error", "value": max_rank_err, "status": "PASS" if max_rank_err == 0 else "FAIL"},
        {"metric": "random_weight_draws", "value": len(random_df), "status": "INFO"},
        {"metric": "random_weight_mean_spearman", "value": random_mean_rho, "status": "REVIEW"},
        {"metric": "random_weight_mean_top3_retention", "value": random_mean_top3, "status": "REVIEW"},
        {"metric": "maximum_project_p05_p95_rank_range", "value": max_project_p90_range, "status": "REVIEW"},
        {"metric": "five_percent_noise_mean_spearman", "value": noise5_rho, "status": "REVIEW"},
        {"metric": "research_warning_count", "value": len(warnings), "status": "INFO"},
        {"metric": "overall_status", "value": status, "status": status},
    ])
    atomic_write(summary, SUMMARY_OUT)

    run = {
        "phase": "15D",
        "run_at": utc_now(),
        "status": status,
        "engine_version": ENGINE_VERSION,
        "reference_projects": int(len(df)),
        "feature_families": families,
        "baseline_weights": baseline_weights,
        "baseline_reconstruction_max_abs_error": max_score_err,
        "baseline_rank_max_abs_error": max_rank_err,
        "random_weight_draws": int(len(random_df)),
        "random_weight_mean_spearman": random_mean_rho,
        "random_weight_mean_top3_retention": random_mean_top3,
        "maximum_project_p05_p95_rank_range": max_project_p90_range,
        "five_percent_noise_mean_spearman": noise5_rho,
        "research_warnings": warnings,
        "guardrails": config.get("guardrails", {}),
        "outputs": [
            str(BASELINE_OUT.relative_to(ROOT)), str(SCENARIO_OUT.relative_to(ROOT)),
            str(ABLATION_OUT.relative_to(ROOT)), str(RANDOM_OUT.relative_to(ROOT)),
            str(PROJECT_STABILITY_OUT.relative_to(ROOT)), str(NOISE_OUT.relative_to(ROOT)),
            str(SUMMARY_OUT.relative_to(ROOT)),
        ],
    }
    append_jsonl(RUN_LOG, run)

    print("PHASE 15D - BENCHMARK, ABLATION & WEIGHT SENSITIVITY VALIDATION")
    print("=" * 86)
    print(f"Reference projects                  : {len(df)}")
    print(f"Feature families                    : {len(families)}")
    print(f"Baseline score max abs error        : {max_score_err:.12g}")
    print(f"Baseline rank max abs error         : {max_rank_err:.12g}")
    print(f"Random weight draws                 : {len(random_df)}")
    print(f"Random-weight mean Spearman         : {random_mean_rho:.4f}")
    print(f"Random-weight mean top-3 retention  : {random_mean_top3:.4f}")
    print(f"Max project p05-p95 rank range      : {max_project_p90_range:.2f}")
    print(f"5% score-noise mean Spearman        : {noise5_rho:.4f}")
    print(f"Research warnings                   : {len(warnings)}")
    for warning in warnings:
        print(f"  - {warning}")
    print(f"STATUS                              : {status}")
    print(f"Summary                             : {SUMMARY_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: this phase tests score-integration and ranking robustness. It is not default-prediction validation, causal feature importance, or a bank credit rating.")
    return 0 if baseline_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
