from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "15_Validation_and_Evidence" / "00_Config" / "stress_monte_carlo_validation_config.json"
OUT_DIR = ROOT / "15_Validation_and_Evidence" / "05_Stress_Monte_Carlo"

STRESS_FILE = ROOT / "03_Modeling" / "Phase_3E_Robust_Stress_Test" / "Robust_Stress_Test_Full.csv"
MC_DIR = ROOT / "03_Modeling" / "Phase_6B_Monte_Carlo_Stress"
MC_SHOCK_FILE = MC_DIR / "Monte_Carlo_Shock_Distributions.csv"
MC_SYSTEM_FILE = MC_DIR / "Monte_Carlo_System_Summary.csv"
MC_PROJECT_FILE = MC_DIR / "Monte_Carlo_Project_Risk_Summary.csv"
MC_RAW_FILE = MC_DIR / "Monte_Carlo_Project_Scores.csv"

DET_REPRO_OUT = OUT_DIR / "Deterministic_Stress_Reproduction.csv"
DET_SENS_OUT = OUT_DIR / "Deterministic_Stress_Severity_Sensitivity.csv"
MC_STRUCT_OUT = OUT_DIR / "Monte_Carlo_Archived_Evidence_Validation.csv"
MC_RAW_VERIFY_OUT = OUT_DIR / "Monte_Carlo_Raw_Summary_Verification.csv"
MC_GAPS_OUT = OUT_DIR / "Monte_Carlo_Method_Metadata_Gap_Register.csv"
MC_HITS_OUT = OUT_DIR / "Monte_Carlo_Method_Source_Hits.csv"
SUMMARY_OUT = OUT_DIR / "Stress_MC_Validation_Summary.csv"
RUN_LOG = OUT_DIR / "Phase_15E_Run_Log.jsonl"

ENGINE_VERSION = "SCI_STRESS_MC_VALIDATION_V1"


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
    return " ".join(str(value).split()).strip()


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


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def rank_desc(values: pd.Series) -> pd.Series:
    return numeric(values).rank(method="min", ascending=False).astype("Int64")


def spearman(a: pd.Series, b: pd.Series) -> float:
    x = numeric(a)
    y = numeric(b)
    mask = x.notna() & y.notna()
    if int(mask.sum()) < 2:
        return float("nan")
    return float(x[mask].rank(method="average").corr(y[mask].rank(method="average")))


def top_n_retention(reference_rank: pd.Series, candidate_rank: pd.Series, n: int = 3) -> float:
    ref = set(reference_rank.index[numeric(reference_rank).le(n)])
    cand = set(candidate_rank.index[numeric(candidate_rank).le(n)])
    if not ref:
        return float("nan")
    return len(ref & cand) / len(ref)


def deterministic_score(df: pd.DataFrame, weights: dict[str, float], stressed: set[str], severity: float) -> pd.Series:
    total = pd.Series(0.0, index=df.index, dtype=float)
    for col, weight in weights.items():
        risk = numeric(df[col])
        if col in stressed:
            risk = risk + severity * (1.0 - risk)
        total = total + float(weight) * risk
    return 100.0 * total


def validate_deterministic(config: dict, stress: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    det = config["deterministic_stress"]
    weights = {k: float(v) for k, v in det["weights"].items()}
    stressed = set(det["stressed_risk_channels"])
    levels = {k: float(v) for k, v in det["severity_levels"].items()}
    score_tol = float(det["score_tolerance"])

    required = {"project_id", *weights.keys()}
    for level in levels:
        required.add(f"{level}_score")
        required.add(f"{level}_rank")
    missing = sorted(required - set(stress.columns))
    if missing:
        raise RuntimeError(f"Deterministic stress file missing columns: {missing}")

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-12:
        raise RuntimeError(f"Deterministic weights must sum to 1.0; found {weight_sum}")

    risk_frame = stress[list(weights)].apply(pd.to_numeric, errors="coerce")
    risk_missing = int(risk_frame.isna().sum().sum())
    risk_out_of_bounds = int(((risk_frame < 0) | (risk_frame > 1)).sum().sum())

    repro = stress[[c for c in ["project_id", "company", "project_type", "state"] if c in stress.columns]].copy()
    score_errors: list[float] = []
    rank_errors: list[int] = []
    calculated_scores: dict[str, pd.Series] = {}
    calculated_ranks: dict[str, pd.Series] = {}

    for level, severity in levels.items():
        calc_score = deterministic_score(stress, weights, stressed, severity)
        calc_rank = rank_desc(calc_score)
        stored_score = numeric(stress[f"{level}_score"])
        stored_rank = numeric(stress[f"{level}_rank"])
        error = (calc_score - stored_score).abs()
        rank_error = (numeric(calc_rank) - stored_rank).abs()

        calculated_scores[level] = calc_score
        calculated_ranks[level] = calc_rank
        repro[f"stored_{level}_score"] = stored_score
        repro[f"calculated_{level}_score"] = calc_score
        repro[f"{level}_score_abs_error"] = error
        repro[f"stored_{level}_rank"] = stored_rank
        repro[f"calculated_{level}_rank"] = calc_rank
        repro[f"{level}_rank_abs_error"] = rank_error
        score_errors.extend(error.dropna().tolist())
        rank_errors.extend(rank_error.dropna().astype(int).tolist())

    ordered = [name for name in ["baseline", "mild", "moderate", "severe"] if name in calculated_scores]
    monotonic_failures = 0
    for earlier, later in zip(ordered, ordered[1:]):
        monotonic_failures += int((calculated_scores[later] + score_tol < calculated_scores[earlier]).sum())

    score_matrix = pd.DataFrame(calculated_scores)
    score_bounds_failures = int(((score_matrix < -score_tol) | (score_matrix > 100.0 + score_tol)).sum().sum())

    max_score_error = max(score_errors) if score_errors else float("nan")
    max_rank_error = max(rank_errors) if rank_errors else 0
    exact_score_pass = bool(np.isfinite(max_score_error) and max_score_error <= score_tol)
    exact_rank_pass = bool(max_rank_error == int(det.get("rank_tolerance", 0)))

    severe_ref = calculated_ranks.get("severe", rank_desc(calculated_scores[ordered[-1]]))
    baseline_ref = calculated_ranks.get("baseline", rank_desc(calculated_scores[ordered[0]]))
    sensitivity_rows = []
    for severity in [float(x) for x in det["severity_sensitivity_grid"]]:
        scores = deterministic_score(stress, weights, stressed, severity)
        ranks = rank_desc(scores)
        sensitivity_rows.append({
            "severity": severity,
            "mean_score": float(scores.mean()),
            "median_score": float(scores.median()),
            "maximum_score": float(scores.max()),
            "minimum_score": float(scores.min()),
            "spearman_vs_baseline_rank": spearman(baseline_ref, ranks),
            "spearman_vs_severe_rank": spearman(severe_ref, ranks),
            "top3_retention_vs_severe": top_n_retention(severe_ref, ranks, 3),
            "maximum_absolute_rank_change_vs_baseline": int((numeric(ranks) - numeric(baseline_ref)).abs().max()),
        })
    sensitivity = pd.DataFrame(sensitivity_rows)

    summary = {
        "deterministic_reference_rows": int(len(stress)),
        "deterministic_weight_sum": float(weight_sum),
        "risk_missing_cells": risk_missing,
        "risk_out_of_bounds_cells": risk_out_of_bounds,
        "deterministic_max_score_abs_error": float(max_score_error),
        "deterministic_max_rank_abs_error": int(max_rank_error),
        "deterministic_monotonicity_failures": int(monotonic_failures),
        "deterministic_score_bounds_failures": int(score_bounds_failures),
        "deterministic_exact_reproduction_pass": bool(
            exact_score_pass
            and exact_rank_pass
            and risk_missing == 0
            and risk_out_of_bounds == 0
            and monotonic_failures == 0
            and score_bounds_failures == 0
        ),
    }
    return repro, sensitivity, summary


def add_mc_check(rows: list[dict], check_id: str, scope: str, status: str, observed, requirement: str, detail: str) -> None:
    rows.append({
        "check_id": check_id,
        "scope": scope,
        "status": status,
        "observed": observed,
        "requirement": requirement,
        "detail": detail,
    })


def validate_mc_archived_evidence(shocks: pd.DataFrame, system: pd.DataFrame, project: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    hard_failures = 0

    shock_required = {"shock_channel", "mean_severity", "median_severity", "p90_severity", "p95_severity"}
    missing = sorted(shock_required - set(shocks.columns))
    if missing:
        add_mc_check(rows, "MC_SHOCK_COLUMNS", "shock_summary", "FAIL", ";".join(missing), "all required columns", "Archived shock summary schema is incomplete.")
        hard_failures += 1
    else:
        vals = shocks[["mean_severity", "median_severity", "p90_severity", "p95_severity"]].apply(pd.to_numeric, errors="coerce")
        missing_numeric = int(vals.isna().sum().sum())
        bounds_fail = int(((vals < 0) | (vals > 1)).sum().sum())
        order_fail = int(((vals["median_severity"] > vals["p90_severity"]) | (vals["p90_severity"] > vals["p95_severity"])).sum())
        for cid, observed, ok, requirement, detail in [
            ("MC_SHOCK_NUMERIC", missing_numeric, missing_numeric == 0, "0 missing numeric cells", "Shock summary severities must be numeric."),
            ("MC_SHOCK_BOUNDS", bounds_fail, bounds_fail == 0, "all severities in [0,1]", "Archived shock summary must remain within the severity scale."),
            ("MC_SHOCK_QUANTILE_ORDER", order_fail, order_fail == 0, "median <= p90 <= p95", "Shock quantiles must be internally ordered."),
        ]:
            status = "PASS" if ok else "FAIL"
            add_mc_check(rows, cid, "shock_summary", status, observed, requirement, detail)
            if not ok:
                hard_failures += 1

    system_required = {
        "simulations", "mean_portfolio_vulnerability", "median_portfolio_vulnerability",
        "p90_portfolio_vulnerability", "p95_portfolio_vulnerability", "p99_portfolio_vulnerability",
        "maximum_portfolio_vulnerability", "systemic_weight",
    }
    missing = sorted(system_required - set(system.columns))
    if missing or len(system) != 1:
        add_mc_check(rows, "MC_SYSTEM_SCHEMA", "system_summary", "FAIL", f"rows={len(system)};missing={missing}", "one complete summary row", "System summary schema/row count must be complete.")
        hard_failures += 1
    else:
        s = system.iloc[0]
        simulations = pd.to_numeric(pd.Series([s["simulations"]]), errors="coerce").iloc[0]
        systemic_weight = pd.to_numeric(pd.Series([s["systemic_weight"]]), errors="coerce").iloc[0]
        q = [
            float(s["p90_portfolio_vulnerability"]),
            float(s["p95_portfolio_vulnerability"]),
            float(s["p99_portfolio_vulnerability"]),
            float(s["maximum_portfolio_vulnerability"]),
        ]
        checks = [
            ("MC_SIMULATION_COUNT", simulations, pd.notna(simulations) and simulations > 0, "> 0", "Archived simulation count must be positive."),
            ("MC_SYSTEMIC_WEIGHT", systemic_weight, pd.notna(systemic_weight) and 0 <= systemic_weight <= 1, "in [0,1]", "Archived systemic weight must be a valid mixing weight."),
            ("MC_SYSTEM_QUANTILE_ORDER", q, q[0] <= q[1] <= q[2] <= q[3], "p90 <= p95 <= p99 <= max", "Portfolio tail quantiles must be internally ordered."),
        ]
        for cid, observed, ok, requirement, detail in checks:
            status = "PASS" if ok else "FAIL"
            add_mc_check(rows, cid, "system_summary", status, observed, requirement, detail)
            if not ok:
                hard_failures += 1

    project_required = {
        "project_id", "mean_simulated_score", "median_simulated_score", "p75_score", "p90_score",
        "p95_score", "p99_score", "maximum_score", "score_std", "probability_top_1",
        "probability_top_3", "probability_top_5",
    }
    missing = sorted(project_required - set(project.columns))
    if missing:
        add_mc_check(rows, "MC_PROJECT_COLUMNS", "project_summary", "FAIL", ";".join(missing), "all required columns", "Project Monte Carlo summary schema is incomplete.")
        hard_failures += 1
    else:
        qcols = ["median_simulated_score", "p75_score", "p90_score", "p95_score", "p99_score", "maximum_score"]
        q = project[qcols].apply(pd.to_numeric, errors="coerce")
        order_fail = int((q.diff(axis=1).iloc[:, 1:] < 0).any(axis=1).sum())
        std = numeric(project["score_std"])
        std_fail = int((std < 0).sum() + std.isna().sum())
        probs = project[["probability_top_1", "probability_top_3", "probability_top_5"]].apply(pd.to_numeric, errors="coerce")
        prob_bounds_fail = int(((probs < 0) | (probs > 1) | probs.isna()).sum().sum())
        prob_order_fail = int(((probs["probability_top_1"] > probs["probability_top_3"]) | (probs["probability_top_3"] > probs["probability_top_5"])).sum())
        for cid, observed, ok, requirement, detail in [
            ("MC_PROJECT_QUANTILE_ORDER", order_fail, order_fail == 0, "median <= p75 <= p90 <= p95 <= p99 <= max", "Project-level simulated score quantiles must be internally ordered."),
            ("MC_PROJECT_STD", std_fail, std_fail == 0, "non-negative finite standard deviations", "Project score dispersion must be valid."),
            ("MC_PROJECT_PROBABILITY_BOUNDS", prob_bounds_fail, prob_bounds_fail == 0, "probabilities in [0,1]", "Top-k probabilities must be valid probabilities."),
            ("MC_PROJECT_PROBABILITY_ORDER", prob_order_fail, prob_order_fail == 0, "P(top1) <= P(top3) <= P(top5)", "Nested top-k probabilities must be monotone."),
        ]:
            status = "PASS" if ok else "FAIL"
            add_mc_check(rows, cid, "project_summary", status, observed, requirement, detail)
            if not ok:
                hard_failures += 1

    return pd.DataFrame(rows), {
        "mc_archived_evidence_hard_failures": int(hard_failures),
        "mc_archived_evidence_internal_consistency_pass": bool(hard_failures == 0),
        "mc_project_summary_rows": int(len(project)),
        "mc_shock_channels": int(len(shocks)),
    }


def detect_column(columns: list[str], preferred: list[str], contains_tokens: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for candidate in preferred:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    for c in columns:
        text = c.lower()
        if all(token in text for token in contains_tokens):
            return c
    return None


def verify_raw_mc_scores(raw_path: Path, project_summary: pd.DataFrame, system_summary: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    columns = [
        "project_id", "raw_rows", "archived_simulations", "score_column", "mean_abs_error",
        "median_abs_error", "p75_abs_error", "p90_abs_error", "p95_abs_error", "p99_abs_error",
        "max_abs_error", "std_ddof0_abs_error", "std_ddof1_abs_error", "best_std_convention",
        "raw_summary_status",
    ]
    if not raw_path.exists():
        return pd.DataFrame(columns=columns), {
            "mc_raw_score_file_present": False,
            "mc_raw_score_summary_verification_status": "RAW_SCORE_FILE_MISSING",
        }

    try:
        raw = pd.read_csv(raw_path)
    except Exception as exc:
        return pd.DataFrame(columns=columns), {
            "mc_raw_score_file_present": True,
            "mc_raw_score_summary_verification_status": f"RAW_SCORE_READ_FAILED:{type(exc).__name__}",
        }

    project_col = detect_column(list(raw.columns), ["project_id"], ["project", "id"])
    score_col = detect_column(
        list(raw.columns),
        ["simulated_score", "simulation_score", "score", "vulnerability_score"],
        ["score"],
    )
    if project_col is None or score_col is None:
        return pd.DataFrame(columns=columns), {
            "mc_raw_score_file_present": True,
            "mc_raw_score_rows": int(len(raw)),
            "mc_raw_score_columns": list(raw.columns),
            "mc_raw_score_summary_verification_status": "RAW_SCORE_SCHEMA_REVIEW_REQUIRED",
        }

    system_sims = None
    if len(system_summary) == 1 and "simulations" in system_summary.columns:
        system_sims = int(pd.to_numeric(system_summary.iloc[0]["simulations"], errors="coerce"))

    archived = project_summary.set_index("project_id")
    rows = []
    tolerance = 1e-8
    for pid, group in raw.groupby(project_col):
        pid = str(pid)
        if pid not in archived.index:
            continue
        scores = pd.to_numeric(group[score_col], errors="coerce").dropna().to_numpy(dtype=float)
        if len(scores) == 0:
            continue
        a = archived.loc[pid]
        calc = {
            "mean_abs_error": abs(float(np.mean(scores)) - float(a["mean_simulated_score"])),
            "median_abs_error": abs(float(np.quantile(scores, 0.50)) - float(a["median_simulated_score"])),
            "p75_abs_error": abs(float(np.quantile(scores, 0.75)) - float(a["p75_score"])),
            "p90_abs_error": abs(float(np.quantile(scores, 0.90)) - float(a["p90_score"])),
            "p95_abs_error": abs(float(np.quantile(scores, 0.95)) - float(a["p95_score"])),
            "p99_abs_error": abs(float(np.quantile(scores, 0.99)) - float(a["p99_score"])),
            "max_abs_error": abs(float(np.max(scores)) - float(a["maximum_score"])),
            "std_ddof0_abs_error": abs(float(np.std(scores, ddof=0)) - float(a["score_std"])),
            "std_ddof1_abs_error": abs(float(np.std(scores, ddof=1)) - float(a["score_std"])) if len(scores) > 1 else float("nan"),
        }
        best_std = "ddof0" if calc["std_ddof0_abs_error"] <= calc["std_ddof1_abs_error"] else "ddof1"
        summary_errs = [
            calc["mean_abs_error"], calc["median_abs_error"], calc["p75_abs_error"], calc["p90_abs_error"],
            calc["p95_abs_error"], calc["p99_abs_error"], calc["max_abs_error"],
            min(calc["std_ddof0_abs_error"], calc["std_ddof1_abs_error"]),
        ]
        rows.append({
            "project_id": pid,
            "raw_rows": int(len(scores)),
            "archived_simulations": system_sims,
            "score_column": score_col,
            **calc,
            "best_std_convention": best_std,
            "raw_summary_status": "PASS_RAW_SUMMARY_RECONSTRUCTION" if max(summary_errs) <= tolerance else "REVIEW_RAW_SUMMARY_DIFFERENCE",
        })

    out = pd.DataFrame(rows, columns=columns)
    if out.empty:
        status = "NO_MATCHING_PROJECTS_IN_RAW_SCORE_FILE"
    elif out["raw_summary_status"].eq("PASS_RAW_SUMMARY_RECONSTRUCTION").all():
        status = "PASS_RAW_PROJECT_SUMMARIES_RECONSTRUCTED"
    else:
        status = "RAW_PROJECT_SUMMARY_DIFFERENCES_REQUIRE_REVIEW"
    return out, {
        "mc_raw_score_file_present": True,
        "mc_raw_score_rows": int(len(raw)),
        "mc_raw_score_columns": list(raw.columns),
        "mc_raw_score_summary_verification_status": status,
    }


def source_scan(config: dict) -> pd.DataFrame:
    mc = config["monte_carlo"]
    extensions = {str(x).lower() for x in mc["source_scan_extensions"]}
    max_bytes = int(mc["source_scan_max_bytes"])
    keywords = [str(x) for x in mc["source_scan_keywords"]]
    rows = []

    for root_name in mc["source_scan_roots"]:
        scan_root = ROOT / root_name
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lower = text.lower()
            for keyword in keywords:
                needle = keyword.lower()
                start = 0
                hit_count = 0
                while True:
                    idx = lower.find(needle, start)
                    if idx < 0:
                        break
                    left = max(0, idx - 140)
                    right = min(len(text), idx + len(keyword) + 220)
                    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
                    rows.append({
                        "file": str(path.relative_to(ROOT)),
                        "keyword": keyword,
                        "snippet": snippet,
                    })
                    hit_count += 1
                    if hit_count >= 8:
                        break
                    start = idx + len(needle)
    if not rows:
        return pd.DataFrame(columns=["file", "keyword", "snippet"])
    return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)


def build_method_gap_register(config: dict, hits: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "random_seed_or_seed_policy": ["seed", "random_state", "default_rng"],
        "shock_distribution_family_and_exact_parameters": ["np.random.beta", "random.beta", "beta("],
        "systemic_idiosyncratic_mixing_equation": ["systemic_weight", "systemic"],
        "cross_channel_dependence_or_correlation_rule": ["correlation", "corr", "covariance", "cholesky"],
        "project_specific_idiosyncratic_shock_generation": ["idiosyncratic", "project shock", "project_shock"],
        "exact_monte_carlo_score_transformation": ["monte_carlo", "simulated_score", "simulation_score"],
        "portfolio_aggregation_formula": ["portfolio", "weighted average", "weighted_average"],
    }
    rows = []
    hit_text = ""
    if not hits.empty:
        hit_text = " ".join((hits["keyword"].astype(str) + " " + hits["snippet"].astype(str)).str.lower())
    for field in config["monte_carlo"]["required_method_metadata"]:
        tokens = mapping.get(field, [field.replace("_", " ")])
        candidate = [token for token in tokens if token.lower() in hit_text]
        rows.append({
            "required_method_metadata": field,
            "automated_candidate_source_signal": "YES" if candidate else "NO",
            "matched_signal_terms": ";".join(candidate),
            "verification_status": "CANDIDATE_SOURCE_REVIEW_REQUIRED" if candidate else "METHOD_METADATA_NOT_RECOVERED",
            "gate_effect": "MONTE_CARLO_METHOD_REPRODUCTION_REMAINS_OPEN",
            "note": "A text hit is not proof of the original sampling implementation. Exact code/parameters must be reviewed and reproduced before this gate can close.",
        })
    return pd.DataFrame(rows)


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError(f"Config engine mismatch: {config.get('engine_version')} != {ENGINE_VERSION}")

    stress = read_csv(STRESS_FILE)
    shocks = read_csv(MC_SHOCK_FILE)
    system = read_csv(MC_SYSTEM_FILE)
    projects = read_csv(MC_PROJECT_FILE)

    det_repro, det_sens, det_summary = validate_deterministic(config, stress)
    mc_checks, mc_summary = validate_mc_archived_evidence(shocks, system, projects)
    raw_verify, raw_summary = verify_raw_mc_scores(MC_RAW_FILE, projects, system)
    hits = source_scan(config)
    gaps = build_method_gap_register(config, hits)

    atomic_write(det_repro, DET_REPRO_OUT)
    atomic_write(det_sens, DET_SENS_OUT)
    atomic_write(mc_checks, MC_STRUCT_OUT)
    atomic_write(raw_verify, MC_RAW_VERIFY_OUT)
    atomic_write(gaps, MC_GAPS_OUT)
    atomic_write(hits, MC_HITS_OUT)

    method_gate_open = bool((gaps["gate_effect"] == "MONTE_CARLO_METHOD_REPRODUCTION_REMAINS_OPEN").any())
    deterministic_pass = bool(det_summary["deterministic_exact_reproduction_pass"])
    archived_mc_pass = bool(mc_summary["mc_archived_evidence_internal_consistency_pass"])

    research_warnings = []
    if method_gate_open:
        research_warnings.append("MONTE_CARLO_METHOD_REPRODUCTION_GATE_REMAINS_OPEN")
    if raw_summary.get("mc_raw_score_summary_verification_status") not in {
        "PASS_RAW_PROJECT_SUMMARIES_RECONSTRUCTED",
    }:
        research_warnings.append("MONTE_CARLO_RAW_SCORE_SUMMARY_RECONSTRUCTION_REVIEW_REQUIRED")

    if deterministic_pass and archived_mc_pass and method_gate_open:
        status = "PASS_DETERMINISTIC_STRESS_REPRODUCED_MC_METHOD_GATE_OPEN"
    elif deterministic_pass and archived_mc_pass and not method_gate_open:
        status = "PASS_STRESS_AND_MC_EVIDENCE_REVIEW_METHOD_GATE_REQUIRES_MANUAL_CLOSE"
    else:
        status = "FAIL_STRESS_OR_ARCHIVED_MC_EVIDENCE_VALIDATION"

    summary = {
        "phase": "15E",
        "run_at": utc_now(),
        "status": status,
        "engine_version": ENGINE_VERSION,
        **det_summary,
        **mc_summary,
        **raw_summary,
        "method_source_hits": int(len(hits)),
        "required_mc_method_metadata_items": int(len(gaps)),
        "mc_method_gate_open": method_gate_open,
        "research_warnings": research_warnings,
        "guardrails": config.get("guardrails", {}),
    }
    summary_df = pd.DataFrame([{
        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
        for k, v in summary.items()
    }])
    atomic_write(summary_df, SUMMARY_OUT)
    append_jsonl(RUN_LOG, summary)

    system_row = system.iloc[0] if len(system) else pd.Series(dtype=object)
    print("PHASE 15E - DETERMINISTIC STRESS & MONTE CARLO FORENSIC VALIDATION")
    print("=" * 88)
    print(f"Deterministic reference projects       : {det_summary['deterministic_reference_rows']}")
    print(f"Deterministic max score abs error      : {det_summary['deterministic_max_score_abs_error']:.12g}")
    print(f"Deterministic max rank abs error       : {det_summary['deterministic_max_rank_abs_error']}")
    print(f"Stress monotonicity failures           : {det_summary['deterministic_monotonicity_failures']}")
    print(f"Deterministic exact reproduction       : {'PASS' if deterministic_pass else 'FAIL'}")
    print(f"Archived MC simulations                : {clean(system_row.get('simulations'))}")
    print(f"Archived MC systemic weight            : {clean(system_row.get('systemic_weight'))}")
    print(f"Archived MC evidence hard failures     : {mc_summary['mc_archived_evidence_hard_failures']}")
    print(f"Raw MC score verification              : {raw_summary.get('mc_raw_score_summary_verification_status')}")
    print(f"Candidate MC method source hits        : {len(hits)}")
    print(f"MC method metadata items still gated   : {len(gaps)}")
    print(f"Research warnings                      : {len(research_warnings)}")
    for warning in research_warnings:
        print(f"  - {warning}")
    print()
    print(f"STATUS                                  : {status}")
    print(f"Summary                                 : {SUMMARY_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: exact deterministic-stress reproduction does not make the stress index a default probability. Archived Monte Carlo draws can be internally validated, but the Monte Carlo method is not called reproducible until the original sampling parameters and equations are recovered and independently rerun.")
    return 0 if not status.startswith("FAIL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
