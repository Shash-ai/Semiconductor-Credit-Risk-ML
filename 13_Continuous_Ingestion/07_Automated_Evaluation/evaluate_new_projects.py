from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "07_Automated_Evaluation"

INFERENCE_FILE = ROOT / "13_Continuous_Ingestion" / "06_Frozen_Model" / "Frozen_Model_New_Project_Inference.csv"
CANONICAL_FILE = ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"
STRESS_REFERENCE_FILE = ROOT / "03_Modeling" / "Phase_3E_Robust_Stress_Test" / "Robust_Stress_Test_Full.csv"
MC_SHOCK_REFERENCE_FILE = ROOT / "03_Modeling" / "Phase_6B_Monte_Carlo_Stress" / "Monte_Carlo_Shock_Distributions.csv"
MC_SYSTEM_REFERENCE_FILE = ROOT / "03_Modeling" / "Phase_6B_Monte_Carlo_Stress" / "Monte_Carlo_System_Summary.csv"

DETERMINISTIC_OUT = OUT_DIR / "New_Project_Deterministic_Stress.csv"
MC_OUT = OUT_DIR / "New_Project_Monte_Carlo_Status.csv"
BANKING_OUT = OUT_DIR / "New_Project_Banking_Evidence_Status.csv"
REGISTER_OUT = OUT_DIR / "New_Project_Evaluation_Register.csv"
VALIDATION_OUT = OUT_DIR / "Phase_13F_Method_Validation.json"
AUDIT_OUT = OUT_DIR / "Automated_Evaluation_Run_Log.jsonl"

STRESS_METHOD_VERSION = "SCI_DETERMINISTIC_STRESS_2026_V1"
MC_METHOD_STATUS = "MC_METHOD_REPRODUCTION_REQUIRED"

WEIGHTS = {
    "risk_project_size": 0.25,
    "risk_geographic_concentration": 0.15,
    "risk_credit_growth": 0.15,
    "risk_credit_volatility": 0.15,
    "risk_npa_growth": 0.15,
    "risk_npa_pressure": 0.15,
}

SCENARIOS = {
    "baseline": 0.00,
    "mild": 0.10,
    "moderate": 0.25,
    "severe": 0.50,
}

MACRO_RISK_COLUMNS = [
    "risk_credit_growth",
    "risk_credit_volatility",
    "risk_npa_growth",
    "risk_npa_pressure",
]

DETERMINISTIC_COLUMNS = [
    "project_id",
    "company",
    "state",
    "project_type",
    "approval_year",
    "investment_crore",
    "current_state_investment_share",
    "risk_project_size",
    "risk_geographic_concentration",
    "risk_credit_growth",
    "risk_credit_volatility",
    "risk_npa_growth",
    "risk_npa_pressure",
    "baseline_score",
    "mild_score",
    "moderate_score",
    "severe_score",
    "absolute_severe_increase",
    "relative_severe_increase_pct",
    "project_size_reference_range_signal",
    "geographic_reference_range_signal",
    "macro_context_status",
    "deterministic_evaluation_status",
    "stress_method_version",
    "evaluated_at",
]

MC_COLUMNS = [
    "project_id",
    "company",
    "monte_carlo_status",
    "historical_reference_simulations",
    "historical_systemic_weight",
    "historical_project_idiosyncratic_weight",
    "known_shock_distribution_contract",
    "reason",
    "evaluated_at",
]

BANKING_COLUMNS = [
    "project_id",
    "company",
    "borrower_financial_evidence_status",
    "project_finance_evidence_status",
    "security_recovery_evidence_status",
    "execution_evidence_status",
    "ews_monitoring_evidence_status",
    "integrated_banking_output_status",
    "verified_banking_layers_present",
    "banking_evidence_status",
    "banking_decision_treatment",
    "evaluated_at",
]

REGISTER_COLUMNS = [
    "project_id",
    "company",
    "state",
    "project_type",
    "investment_crore",
    "predicted_validated_cluster",
    "structural_extrapolation_signal",
    "structural_model_status",
    "deterministic_stress_status",
    "baseline_score",
    "severe_score",
    "monte_carlo_status",
    "banking_evidence_status",
    "overall_automated_evaluation_status",
    "next_required_action",
    "evaluated_at",
]

BANKING_FILES = {
    "borrower_financial": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Borrower_Financial_Risk_Summary.csv",
    "project_finance": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Project_Finance_Underwriting_Summary.csv",
    "security_recovery": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Collateral_Security_Recovery_Project_Summary.csv",
    "execution": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Project_Execution_Risk_Summary.csv",
    "ews": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Longitudinal_EWS_Project_Summary.csv",
    "integrated": ROOT / "04_Banking_Alignment" / "04_Outputs" / "Integrated_Banking_Risk_Full.csv",
}


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
    return " ".join(str(value).split())


def read_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def write_csv_atomic(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    df = df[columns]
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
    with AUDIT_OUT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def minmax(value: float, low: float, high: float) -> tuple[float, str]:
    if not np.isfinite(value) or not np.isfinite(low) or not np.isfinite(high) or high <= low:
        raise ValueError("Invalid min-max normalization inputs")
    raw = (value - low) / (high - low)
    if raw < 0:
        signal = "BELOW_REFERENCE_RANGE_CLIPPED"
    elif raw > 1:
        signal = "ABOVE_REFERENCE_RANGE_CLIPPED"
    else:
        signal = "WITHIN_REFERENCE_RANGE"
    return clip01(raw), signal


def stress_score(risks: dict[str, float], severity: float) -> float:
    stressed = dict(risks)
    for column in MACRO_RISK_COLUMNS:
        base = float(stressed[column])
        stressed[column] = base + severity * (1.0 - base)
    score = 100.0 * sum(WEIGHTS[column] * float(stressed[column]) for column in WEIGHTS)
    return float(score)


def validate_deterministic_method(reference: pd.DataFrame) -> dict:
    required = set(WEIGHTS) | {
        "project_id",
        "investment_crore",
        "state_financial_share_within_scope",
        "approval_year",
        "baseline_score",
        "mild_score",
        "moderate_score",
        "severe_score",
    }
    missing = sorted(required - set(reference.columns))
    if missing:
        raise RuntimeError(f"Phase 3E reference is missing required columns: {missing}")

    score_errors: dict[str, float] = {}
    max_score_error = 0.0
    for scenario, severity in SCENARIOS.items():
        stored_col = f"{scenario}_score"
        calculated = []
        for _, row in reference.iterrows():
            risks = {column: float(row[column]) for column in WEIGHTS}
            calculated.append(stress_score(risks, severity))
        stored = pd.to_numeric(reference[stored_col], errors="raise").to_numpy(dtype=float)
        err = float(np.max(np.abs(np.asarray(calculated) - stored)))
        score_errors[scenario] = err
        max_score_error = max(max_score_error, err)

    inv = pd.to_numeric(reference["investment_crore"], errors="raise")
    inv_min, inv_max = float(inv.min()), float(inv.max())
    project_risk_calc = ((inv - inv_min) / (inv_max - inv_min)).clip(0, 1)
    project_risk_stored = pd.to_numeric(reference["risk_project_size"], errors="raise")
    project_risk_error = float((project_risk_calc - project_risk_stored).abs().max())

    share = pd.to_numeric(reference["state_financial_share_within_scope"], errors="raise")
    share_min, share_max = float(share.min()), float(share.max())
    geo_risk_calc = ((share - share_min) / (share_max - share_min)).clip(0, 1)
    geo_risk_stored = pd.to_numeric(reference["risk_geographic_concentration"], errors="raise")
    geo_risk_error = float((geo_risk_calc - geo_risk_stored).abs().max())

    macro_by_year: dict[int, dict[str, float]] = {}
    macro_consistency_errors: dict[str, float] = {}
    for year, group in reference.groupby(pd.to_numeric(reference["approval_year"], errors="raise").astype(int)):
        vector: dict[str, float] = {}
        for column in MACRO_RISK_COLUMNS:
            values = pd.to_numeric(group[column], errors="raise")
            spread = float(values.max() - values.min())
            macro_consistency_errors[f"{year}:{column}"] = spread
            if spread > 1e-12:
                raise RuntimeError(f"Historical macro risk vector is not unique for year={year}, column={column}")
            vector[column] = float(values.iloc[0])
        macro_by_year[int(year)] = vector

    validation_pass = bool(
        max_score_error <= 1e-10
        and project_risk_error <= 1e-10
        and geo_risk_error <= 1e-10
        and max(macro_consistency_errors.values(), default=0.0) <= 1e-12
    )

    return {
        "stress_method_version": STRESS_METHOD_VERSION,
        "reference_projects": int(len(reference)),
        "weights": WEIGHTS,
        "scenario_severities": SCENARIOS,
        "scenario_score_max_abs_error": score_errors,
        "overall_score_max_abs_error": max_score_error,
        "project_size_normalization_max_abs_error": project_risk_error,
        "geographic_normalization_max_abs_error": geo_risk_error,
        "reference_investment_min_crore": inv_min,
        "reference_investment_max_crore": inv_max,
        "reference_state_share_min": share_min,
        "reference_state_share_max": share_max,
        "macro_risk_vectors_by_approval_year": macro_by_year,
        "macro_vector_consistency_max_spread": max(macro_consistency_errors.values(), default=0.0),
        "deterministic_method_reproduction_pass": validation_pass,
    }


def build_deterministic_evaluation(
    inference: pd.DataFrame,
    canonical: pd.DataFrame,
    reference: pd.DataFrame,
    validation: dict,
) -> pd.DataFrame:
    if inference.empty:
        return pd.DataFrame(columns=DETERMINISTIC_COLUMNS)

    if not validation["deterministic_method_reproduction_pass"]:
        raise RuntimeError("Deterministic Phase 3E method reproduction failed; no new-project stress scores were generated")

    canonical = canonical.copy()
    canonical["investment_crore"] = pd.to_numeric(canonical["investment_crore"], errors="coerce")
    if canonical["investment_crore"].isna().any():
        bad = canonical.loc[canonical["investment_crore"].isna(), "project_id"].astype(str).tolist()
        raise RuntimeError(f"Canonical projects have missing investment_crore: {bad}")

    total_investment = float(canonical["investment_crore"].sum())
    state_totals = canonical.groupby("state")["investment_crore"].sum().to_dict()
    canonical_lookup = canonical.set_index(canonical["project_id"].astype(str), drop=False)

    inv_min = float(validation["reference_investment_min_crore"])
    inv_max = float(validation["reference_investment_max_crore"])
    share_min = float(validation["reference_state_share_min"])
    share_max = float(validation["reference_state_share_max"])
    macro_map = {int(k): v for k, v in validation["macro_risk_vectors_by_approval_year"].items()}

    rows = []
    for _, inferred in inference.iterrows():
        project_id = clean(inferred.get("project_id"))
        if project_id not in canonical_lookup.index:
            raise RuntimeError(f"Inferred project {project_id} is not present in the canonical master")
        project = canonical_lookup.loc[project_id]
        if isinstance(project, pd.DataFrame):
            raise RuntimeError(f"Duplicate canonical project_id: {project_id}")

        investment = float(project["investment_crore"])
        state = clean(project.get("state"))
        state_share = float(state_totals.get(state, 0.0)) / total_investment if total_investment > 0 else np.nan
        risk_size, size_signal = minmax(investment, inv_min, inv_max)
        risk_geo, geo_signal = minmax(state_share, share_min, share_max)

        approval_year_raw = pd.to_numeric(pd.Series([project.get("approval_year")]), errors="coerce").iloc[0]
        approval_year = int(approval_year_raw) if pd.notna(approval_year_raw) else None
        macro = macro_map.get(approval_year) if approval_year is not None else None

        base_row = {
            "project_id": project_id,
            "company": clean(project.get("company")),
            "state": state,
            "project_type": clean(project.get("project_type")),
            "approval_year": approval_year,
            "investment_crore": investment,
            "current_state_investment_share": state_share,
            "risk_project_size": risk_size,
            "risk_geographic_concentration": risk_geo,
            "project_size_reference_range_signal": size_signal,
            "geographic_reference_range_signal": geo_signal,
            "stress_method_version": STRESS_METHOD_VERSION,
            "evaluated_at": utc_now(),
        }

        if macro is None:
            base_row.update({
                **{column: pd.NA for column in MACRO_RISK_COLUMNS},
                "baseline_score": pd.NA,
                "mild_score": pd.NA,
                "moderate_score": pd.NA,
                "severe_score": pd.NA,
                "absolute_severe_increase": pd.NA,
                "relative_severe_increase_pct": pd.NA,
                "macro_context_status": "MACRO_CONTEXT_REVIEW_REQUIRED",
                "deterministic_evaluation_status": "NOT_SCORED_MISSING_VERIFIED_APPROVAL_YEAR_MACRO_VECTOR",
            })
        else:
            risks = {
                "risk_project_size": risk_size,
                "risk_geographic_concentration": risk_geo,
                **{column: float(macro[column]) for column in MACRO_RISK_COLUMNS},
            }
            scores = {scenario: stress_score(risks, severity) for scenario, severity in SCENARIOS.items()}
            baseline = scores["baseline"]
            severe = scores["severe"]
            relative = ((severe - baseline) / baseline * 100.0) if baseline > 0 else np.nan
            base_row.update({
                **{column: float(macro[column]) for column in MACRO_RISK_COLUMNS},
                "baseline_score": scores["baseline"],
                "mild_score": scores["mild"],
                "moderate_score": scores["moderate"],
                "severe_score": scores["severe"],
                "absolute_severe_increase": severe - baseline,
                "relative_severe_increase_pct": relative,
                "macro_context_status": f"HISTORICAL_APPROVAL_YEAR_VECTOR_AVAILABLE_{approval_year}",
                "deterministic_evaluation_status": "DETERMINISTIC_STRESS_EVALUATED",
            })
        rows.append(base_row)

    return pd.DataFrame(rows)


def parse_mc_reference_contract() -> dict:
    shock = read_csv(MC_SHOCK_REFERENCE_FILE, required=False)
    system = read_csv(MC_SYSTEM_REFERENCE_FILE, required=False)
    contract: dict = {
        "status": MC_METHOD_STATUS,
        "reason": (
            "Historical Phase 6B output files expose shock distributions and system weights, but the repository "
            "does not currently expose a fully reproducible simulation/scoring implementation. Phase 13F therefore "
            "does not invent a Monte Carlo formula for new projects."
        ),
    }

    if not system.empty:
        row = system.iloc[0]
        for source, target in [
            ("n_simulations", "historical_reference_simulations"),
            ("systemic_weight", "historical_systemic_weight"),
            ("project_idiosyncratic_weight", "historical_project_idiosyncratic_weight"),
        ]:
            if source in system.columns:
                value = pd.to_numeric(pd.Series([row[source]]), errors="coerce").iloc[0]
                contract[target] = float(value) if pd.notna(value) else None

    known = []
    if not shock.empty:
        for _, row in shock.iterrows():
            known.append({
                "shock": clean(row.get("shock")),
                "distribution": clean(row.get("distribution")),
                "parameters": clean(row.get("parameters")),
            })
    contract["known_shock_distributions"] = known
    return contract


def build_mc_status(inference: pd.DataFrame, contract: dict) -> pd.DataFrame:
    if inference.empty:
        return pd.DataFrame(columns=MC_COLUMNS)
    rows = []
    known_text = "; ".join(
        f"{x['shock']}:{x['distribution']}({x['parameters']})" for x in contract.get("known_shock_distributions", [])
    )
    for _, row in inference.iterrows():
        rows.append({
            "project_id": clean(row.get("project_id")),
            "company": clean(row.get("company")),
            "monte_carlo_status": MC_METHOD_STATUS,
            "historical_reference_simulations": contract.get("historical_reference_simulations"),
            "historical_systemic_weight": contract.get("historical_systemic_weight"),
            "historical_project_idiosyncratic_weight": contract.get("historical_project_idiosyncratic_weight"),
            "known_shock_distribution_contract": known_text,
            "reason": contract["reason"],
            "evaluated_at": utc_now(),
        })
    return pd.DataFrame(rows)


def exact_project_presence(path: Path, project_id: str) -> bool:
    df = read_csv(path, required=False)
    if df.empty or "project_id" not in df.columns:
        return False
    return bool(df["project_id"].astype(str).str.strip().eq(project_id).any())


def build_banking_status(inference: pd.DataFrame) -> pd.DataFrame:
    if inference.empty:
        return pd.DataFrame(columns=BANKING_COLUMNS)

    rows = []
    for _, row in inference.iterrows():
        project_id = clean(row.get("project_id"))
        company = clean(row.get("company"))
        presence = {name: exact_project_presence(path, project_id) for name, path in BANKING_FILES.items()}
        layer_count = sum(int(presence[name]) for name in ["borrower_financial", "project_finance", "security_recovery", "execution", "ews"])

        if presence["integrated"]:
            integrated_status = "EXACT_PROJECT_OUTPUT_PRESENT_REVIEW_REQUIRED"
        else:
            integrated_status = "NO_EXACT_PROJECT_INTEGRATED_OUTPUT"

        if layer_count == 0:
            overall = "INSUFFICIENT_VERIFIED_BANKING_EVIDENCE"
            treatment = "HOLD_BANKING_CONCLUSION_AND_REQUEST_PROJECT_SPECIFIC_EVIDENCE"
        else:
            overall = "PARTIAL_PROJECT_SPECIFIC_BANKING_EVIDENCE_REVIEW_REQUIRED"
            treatment = "HUMAN_REVIEW_REQUIRED_BEFORE_BANKING_INTERPRETATION"

        rows.append({
            "project_id": project_id,
            "company": company,
            "borrower_financial_evidence_status": "EXACT_PROJECT_OUTPUT_PRESENT" if presence["borrower_financial"] else "NOT_AVAILABLE_FOR_NEW_PROJECT",
            "project_finance_evidence_status": "EXACT_PROJECT_OUTPUT_PRESENT" if presence["project_finance"] else "NOT_AVAILABLE_FOR_NEW_PROJECT",
            "security_recovery_evidence_status": "EXACT_PROJECT_OUTPUT_PRESENT" if presence["security_recovery"] else "NOT_AVAILABLE_FOR_NEW_PROJECT",
            "execution_evidence_status": "EXACT_PROJECT_OUTPUT_PRESENT" if presence["execution"] else "NOT_AVAILABLE_FOR_NEW_PROJECT",
            "ews_monitoring_evidence_status": "EXACT_PROJECT_OUTPUT_PRESENT" if presence["ews"] else "NOT_AVAILABLE_FOR_NEW_PROJECT",
            "integrated_banking_output_status": integrated_status,
            "verified_banking_layers_present": layer_count,
            "banking_evidence_status": overall,
            "banking_decision_treatment": treatment,
            "evaluated_at": utc_now(),
        })
    return pd.DataFrame(rows)


def build_register(
    inference: pd.DataFrame,
    deterministic: pd.DataFrame,
    mc: pd.DataFrame,
    banking: pd.DataFrame,
) -> pd.DataFrame:
    if inference.empty:
        return pd.DataFrame(columns=REGISTER_COLUMNS)

    det_lookup = deterministic.set_index("project_id", drop=False) if not deterministic.empty else pd.DataFrame()
    mc_lookup = mc.set_index("project_id", drop=False) if not mc.empty else pd.DataFrame()
    bank_lookup = banking.set_index("project_id", drop=False) if not banking.empty else pd.DataFrame()

    rows = []
    for _, row in inference.iterrows():
        project_id = clean(row.get("project_id"))
        det = det_lookup.loc[project_id] if not det_lookup.empty and project_id in det_lookup.index else None
        mc_row = mc_lookup.loc[project_id] if not mc_lookup.empty and project_id in mc_lookup.index else None
        bank = bank_lookup.loc[project_id] if not bank_lookup.empty and project_id in bank_lookup.index else None

        det_status = clean(det.get("deterministic_evaluation_status")) if det is not None else "NOT_AVAILABLE"
        mc_status = clean(mc_row.get("monte_carlo_status")) if mc_row is not None else "NOT_AVAILABLE"
        banking_status = clean(bank.get("banking_evidence_status")) if bank is not None else "INSUFFICIENT_VERIFIED_BANKING_EVIDENCE"
        extrapolation = clean(row.get("structural_extrapolation_signal"))

        blockers = []
        if extrapolation == "STRUCTURAL_EXTRAPOLATION_REVIEW_REQUIRED":
            blockers.append("STRUCTURAL_EXTRAPOLATION_REVIEW")
        if det_status != "DETERMINISTIC_STRESS_EVALUATED":
            blockers.append("DETERMINISTIC_STRESS_REVIEW")
        if mc_status == MC_METHOD_STATUS:
            blockers.append("MONTE_CARLO_METHOD_REPRODUCTION")
        if banking_status == "INSUFFICIENT_VERIFIED_BANKING_EVIDENCE":
            blockers.append("PROJECT_SPECIFIC_BANKING_EVIDENCE")

        overall = "AUTOMATED_PUBLIC_DATA_EVALUATION_COMPLETE_WITH_GAPS" if not blockers else "REVIEW_REQUIRED_BEFORE_DASHBOARD_ACTIVE"
        next_action = "NONE" if not blockers else ";".join(blockers)

        rows.append({
            "project_id": project_id,
            "company": clean(row.get("company")),
            "state": clean(row.get("state")),
            "project_type": clean(row.get("project_type")),
            "investment_crore": row.get("investment_crore"),
            "predicted_validated_cluster": row.get("predicted_validated_cluster"),
            "structural_extrapolation_signal": extrapolation,
            "structural_model_status": clean(row.get("model_evaluation_status")) or "STRUCTURAL_MODEL_EVALUATED",
            "deterministic_stress_status": det_status,
            "baseline_score": det.get("baseline_score") if det is not None else pd.NA,
            "severe_score": det.get("severe_score") if det is not None else pd.NA,
            "monte_carlo_status": mc_status,
            "banking_evidence_status": banking_status,
            "overall_automated_evaluation_status": overall,
            "next_required_action": next_action,
            "evaluated_at": utc_now(),
        })
    return pd.DataFrame(rows)


def main() -> int:
    started = utc_now()
    try:
        inference = read_csv(INFERENCE_FILE)
        canonical = read_csv(CANONICAL_FILE)
        reference = read_csv(STRESS_REFERENCE_FILE)

        validation = validate_deterministic_method(reference)
        mc_contract = parse_mc_reference_contract()
        method_validation = {
            "phase": "13F",
            "validated_at": utc_now(),
            "deterministic_stress": validation,
            "monte_carlo": mc_contract,
            "governance": {
                "project_investment_is_bank_exposure": False,
                "pd_lgd_ead_ecl_generated": False,
                "automatic_credit_approval_or_rejection": False,
                "missing_banking_values_imputed": False,
            },
        }
        write_json_atomic(method_validation, VALIDATION_OUT)

        if not validation["deterministic_method_reproduction_pass"]:
            raise RuntimeError("Phase 13F deterministic stress method failed historical reproduction")

        deterministic = build_deterministic_evaluation(inference, canonical, reference, validation)
        mc = build_mc_status(inference, mc_contract)
        banking = build_banking_status(inference)
        register = build_register(inference, deterministic, mc, banking)

        write_csv_atomic(deterministic, DETERMINISTIC_OUT, DETERMINISTIC_COLUMNS)
        write_csv_atomic(mc, MC_OUT, MC_COLUMNS)
        write_csv_atomic(banking, BANKING_OUT, BANKING_COLUMNS)
        write_csv_atomic(register, REGISTER_OUT, REGISTER_COLUMNS)

        summary = {
            "phase": "13F",
            "run_at": utc_now(),
            "started_at": started,
            "status": "SUCCESS",
            "new_structurally_evaluated_projects_seen": int(len(inference)),
            "deterministic_stress_evaluated": int(
                deterministic.get("deterministic_evaluation_status", pd.Series(dtype=str)).astype(str).eq("DETERMINISTIC_STRESS_EVALUATED").sum()
            ),
            "macro_context_review_required": int(
                deterministic.get("macro_context_status", pd.Series(dtype=str)).astype(str).eq("MACRO_CONTEXT_REVIEW_REQUIRED").sum()
            ),
            "monte_carlo_method_reproduction_required": int(len(mc)) if MC_METHOD_STATUS else 0,
            "banking_evidence_review_required": int(
                banking.get("banking_evidence_status", pd.Series(dtype=str)).astype(str).ne("").sum()
            ),
            "deterministic_reference_max_error": validation["overall_score_max_abs_error"],
            "outputs": [
                str(DETERMINISTIC_OUT.relative_to(ROOT)),
                str(MC_OUT.relative_to(ROOT)),
                str(BANKING_OUT.relative_to(ROOT)),
                str(REGISTER_OUT.relative_to(ROOT)),
                str(VALIDATION_OUT.relative_to(ROOT)),
            ],
        }
        append_audit(summary)

        print("PHASE 13F - AUTOMATED NEW-PROJECT EVALUATION")
        print("=" * 68)
        print(f"Structural inference rows        : {len(inference)}")
        print(f"Phase 3E reproduction max error : {validation['overall_score_max_abs_error']:.12g}")
        print(f"Deterministic method reproduced : {validation['deterministic_method_reproduction_pass']}")
        print(f"Deterministic projects scored   : {summary['deterministic_stress_evaluated']}")
        print(f"Macro-context review required   : {summary['macro_context_review_required']}")
        print(f"Monte Carlo method status       : {MC_METHOD_STATUS}")
        print(f"Banking evidence rows           : {len(banking)}")
        print(f"Evaluation register rows        : {len(register)}")
        print(f"Register output                 : {REGISTER_OUT.relative_to(ROOT)}")
        if inference.empty:
            print("No newly canonicalized projects require Phase 13F evaluation yet.")
        else:
            print("\nNEW PROJECT EVALUATION STATUS")
            for _, r in register.iterrows():
                print(
                    f"- {r['project_id']} | {r['company']} | "
                    f"deterministic={r['deterministic_stress_status']} | "
                    f"mc={r['monte_carlo_status']} | banking={r['banking_evidence_status']}"
                )
        print("\nGuardrail: no PD/LGD/EAD/ECL, no invented bank exposure, and no automated credit decision.")
        return 0

    except Exception as exc:
        append_audit({
            "phase": "13F",
            "run_at": utc_now(),
            "started_at": started,
            "status": "FAILED_SAFE",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        print("PHASE 13F - FAILED SAFE", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
