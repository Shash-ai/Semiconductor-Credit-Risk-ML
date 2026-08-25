from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "08_Governance"
HASH_OUT = OUT_DIR / "Phase_13I_Artifact_Hashes.csv"
CHANGE_OUT = OUT_DIR / "Phase_13I_Change_Register.csv"
MANIFEST_OUT = OUT_DIR / "Phase_13I_Lineage_Manifest.json"
AUDIT_OUT = OUT_DIR / "Phase_13I_Run_Log.jsonl"

AUDIT_VERSION = "SCI_PHASE13_LINEAGE_AUDIT_V1"

# Required = absence or integrity failure blocks a PASS result.
ARTIFACTS = [
    ("13_Continuous_Ingestion/00_Config/source_registry.csv", "SOURCE_CONFIG", True),
    ("13_Continuous_Ingestion/00_Config/source_monitor_config.json", "SOURCE_CONFIG", True),
    ("01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Master_Canonical.csv", "CANONICAL_DATA", True),
    ("01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Ecosystem_Master.csv", "MODEL_REFERENCE", True),
    ("01_Raw_Data/Semiconductor/Semiconductor_Master/Ecosystem_Clustering_Final.csv", "MODEL_REFERENCE", True),
    ("03_Modeling/Phase_3A_PCA_KMeans/PCA_Loadings.csv", "MODEL_REFERENCE", True),
    ("03_Modeling/Phase_3A_PCA_KMeans/PCA_Explained_Variance.csv", "MODEL_REFERENCE", True),
    ("03_Modeling/Phase_3B_Cluster_Validation/Validated_Cluster_Assignments.csv", "MODEL_REFERENCE", True),
    ("03_Modeling/Phase_3E_Robust_Stress_Test/Robust_Stress_Test_Full.csv", "STRESS_REFERENCE", True),
    ("03_Modeling/Phase_6B_Monte_Carlo_Stress/Monte_Carlo_Shock_Distributions.csv", "MC_REFERENCE", True),
    ("03_Modeling/Phase_6B_Monte_Carlo_Stress/Monte_Carlo_System_Summary.csv", "MC_REFERENCE", True),
    ("13_Continuous_Ingestion/01_Discovery/discover_new_projects.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/04_Verification/verify_candidates.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/05_Canonicalization/canonicalize_reviewed_candidates.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/freeze_and_infer.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/freeze_and_infer_v2.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/freeze_and_infer_v2_1.py", "PIPELINE_CODE", True),
    ("13_Continuous_Ingestion/07_Automated_Evaluation/evaluate_new_projects.py", "PIPELINE_CODE", True),
    (".github/workflows/phase13_continuous_ingestion.yml", "ORCHESTRATION", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Model_Manifest.json", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Model_Validation.json", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Scaler_Parameters.csv", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_PCA_Components.csv", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Cluster_Centroids.csv", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Reference_PCA_Scores.csv", "FROZEN_MODEL", True),
    ("13_Continuous_Ingestion/07_Automated_Evaluation/Phase_13F_Method_Validation.json", "METHOD_VALIDATION", True),
    ("13_Continuous_Ingestion/02_Candidates/Project_Discovery_Candidates.csv", "RUNTIME_OUTPUT", False),
    ("13_Continuous_Ingestion/04_Verification/Verification_Queue.csv", "RUNTIME_OUTPUT", False),
    ("13_Continuous_Ingestion/05_Canonicalization/Canonical_Staging.csv", "RUNTIME_OUTPUT", False),
    ("13_Continuous_Ingestion/06_Frozen_Model/Frozen_Model_New_Project_Inference.csv", "RUNTIME_OUTPUT", False),
    ("13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Evaluation_Register.csv", "RUNTIME_OUTPUT", False),
]

REFERENCE_HASH_MAP = {
    "baseline_ecosystem_sha256": "01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Ecosystem_Master.csv",
    "authoritative_feature_matrix_sha256": "01_Raw_Data/Semiconductor/Semiconductor_Master/Ecosystem_Clustering_Final.csv",
    "pca_loadings_sha256": "03_Modeling/Phase_3A_PCA_KMeans/PCA_Loadings.csv",
    "validated_assignments_sha256": "03_Modeling/Phase_3B_Cluster_Validation/Validated_Cluster_Assignments.csv",
    "pca_variance_sha256": "03_Modeling/Phase_3A_PCA_KMeans/PCA_Explained_Variance.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def latest_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return {}
    for line in reversed(lines):
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return {}


def safe_csv_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(len(pd.read_csv(path)))
    except Exception:
        return None


def git_sha() -> str:
    env_sha = os.getenv("GITHUB_SHA", "").strip()
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def load_previous_hashes() -> dict[str, str]:
    if not HASH_OUT.exists():
        return {}
    try:
        df = pd.read_csv(HASH_OUT)
    except Exception:
        return {}
    if not {"path", "sha256"}.issubset(df.columns):
        return {}
    return dict(zip(df["path"].astype(str), df["sha256"].fillna("").astype(str)))


def build_hash_table(previous: dict[str, str]) -> pd.DataFrame:
    rows = []
    for rel, category, required in ARTIFACTS:
        path = ROOT / rel
        exists = path.exists() and path.is_file()
        digest = sha256_file(path) if exists else ""
        prior = previous.get(rel, "")
        if not exists:
            change = "MISSING_REQUIRED" if required else "MISSING_OPTIONAL"
        elif not prior:
            change = "NEW"
        elif prior == digest:
            change = "UNCHANGED"
        else:
            change = "MODIFIED"
        rows.append({
            "path": rel,
            "category": category,
            "required": bool(required),
            "exists": bool(exists),
            "size_bytes": int(path.stat().st_size) if exists else pd.NA,
            "sha256": digest,
            "previous_sha256": prior,
            "change_status": change,
        })
    return pd.DataFrame(rows)


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def append_audit(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_OUT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def main() -> int:
    now = utc_now()
    previous = load_previous_hashes()
    hashes = build_hash_table(previous)

    hard_failures: list[str] = []
    warnings: list[str] = []

    missing_required = hashes.loc[hashes["required"] & ~hashes["exists"], "path"].astype(str).tolist()
    if missing_required:
        hard_failures.extend([f"MISSING_REQUIRED_ARTIFACT:{path}" for path in missing_required])

    frozen_manifest_path = ROOT / "13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Model_Manifest.json"
    frozen_validation_path = ROOT / "13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Model_Validation.json"
    method_validation_path = ROOT / "13_Continuous_Ingestion/07_Automated_Evaluation/Phase_13F_Method_Validation.json"

    frozen_manifest = read_json(frozen_manifest_path)
    frozen_validation = read_json(frozen_validation_path)
    method_validation = read_json(method_validation_path)

    reference_checks = []
    expected_hashes = frozen_manifest.get("reference_hashes", {}) if isinstance(frozen_manifest, dict) else {}
    for key, rel in REFERENCE_HASH_MAP.items():
        path = ROOT / rel
        expected = str(expected_hashes.get(key, ""))
        actual = sha256_file(path) if path.exists() else ""
        passed = bool(expected and actual and expected == actual)
        reference_checks.append({"manifest_key": key, "path": rel, "expected_sha256": expected, "actual_sha256": actual, "pass": passed})
        if not passed:
            hard_failures.append(f"FROZEN_REFERENCE_HASH_MISMATCH:{key}:{rel}")

    e13_pass = bool(
        frozen_validation.get("raw_feature_contract_pass") is True
        and frozen_validation.get("stored_z_reconstruction_pass") is True
        and frozen_validation.get("pca_reconstruction_pass") is True
        and frozen_validation.get("cluster_recovery_pass") is True
        and frozen_validation.get("status") == "PASS_FROZEN_REFERENCE_REPRODUCED"
    )
    if not e13_pass:
        hard_failures.append("PHASE_13E_VALIDATION_GATE_NOT_PASSING")

    deterministic = method_validation.get("deterministic_stress", {}) if isinstance(method_validation, dict) else {}
    f13_pass = deterministic.get("deterministic_method_reproduction_pass") is True
    if not f13_pass:
        hard_failures.append("PHASE_13F_DETERMINISTIC_REPRODUCTION_NOT_PASSING")

    governance = method_validation.get("governance", {}) if isinstance(method_validation, dict) else {}
    expected_false = [
        "project_investment_is_bank_exposure",
        "pd_lgd_ead_ecl_generated",
        "automatic_credit_approval_or_rejection",
        "missing_banking_values_imputed",
    ]
    governance_check = {key: governance.get(key) is False for key in expected_false}
    for key, passed in governance_check.items():
        if not passed:
            hard_failures.append(f"GOVERNANCE_GUARDRAIL_NOT_CONFIRMED:{key}")

    mc = method_validation.get("monte_carlo", {}) if isinstance(method_validation, dict) else {}
    mc_status = str(mc.get("status", "NOT_AVAILABLE"))
    if mc_status != "MC_METHOD_REPRODUCTION_REQUIRED":
        warnings.append(f"MONTE_CARLO_STATUS_CHANGED:{mc_status}")
    else:
        warnings.append("MONTE_CARLO_METHOD_REPRODUCTION_REQUIRED")

    discovery_audit = latest_jsonl(ROOT / "13_Continuous_Ingestion/03_Audit/Discovery_Run_Log.jsonl")
    source_errors = discovery_audit.get("errors", []) if isinstance(discovery_audit, dict) else []
    if source_errors:
        warnings.append(f"DISCOVERY_SOURCE_ERRORS:{len(source_errors)}")

    changed = hashes[hashes["change_status"].isin(["NEW", "MODIFIED", "MISSING_REQUIRED", "MISSING_OPTIONAL"])].copy()
    atomic_csv(hashes, HASH_OUT)
    atomic_csv(changed, CHANGE_OUT)

    execution_sha = git_sha()
    run_id = os.getenv("GITHUB_RUN_ID", "LOCAL")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    event_name = os.getenv("GITHUB_EVENT_NAME", "local")

    status = "FAIL_INTEGRITY" if hard_failures else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    manifest = {
        "phase": "13I",
        "audit_version": AUDIT_VERSION,
        "generated_at": now,
        "status": status,
        "execution": {
            "git_sha": execution_sha,
            "github_run_id": run_id,
            "github_run_attempt": run_attempt,
            "github_event_name": event_name,
            "github_ref_name": os.getenv("GITHUB_REF_NAME", ""),
        },
        "model_versions": {
            "structural_model_version": frozen_manifest.get("model_version"),
            "structural_model_scope": frozen_manifest.get("model_scope"),
            "deterministic_stress_method_version": deterministic.get("stress_method_version"),
            "monte_carlo_method_status": mc_status,
        },
        "integrity": {
            "required_artifacts": int(hashes["required"].sum()),
            "required_artifacts_present": int((hashes["required"] & hashes["exists"]).sum()),
            "frozen_reference_hash_checks": reference_checks,
            "phase_13e_reference_reproduction_pass": e13_pass,
            "phase_13f_deterministic_reproduction_pass": f13_pass,
            "governance_guardrails_confirmed": governance_check,
            "hard_failures": hard_failures,
            "warnings": warnings,
        },
        "runtime_counts": {
            "canonical_projects": safe_csv_count(ROOT / "01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Master_Canonical.csv"),
            "discovery_candidates": safe_csv_count(ROOT / "13_Continuous_Ingestion/02_Candidates/Project_Discovery_Candidates.csv"),
            "verification_queue": safe_csv_count(ROOT / "13_Continuous_Ingestion/04_Verification/Verification_Queue.csv"),
            "canonical_staging": safe_csv_count(ROOT / "13_Continuous_Ingestion/05_Canonicalization/Canonical_Staging.csv"),
            "new_project_inference": safe_csv_count(ROOT / "13_Continuous_Ingestion/06_Frozen_Model/Frozen_Model_New_Project_Inference.csv"),
            "new_project_evaluation_register": safe_csv_count(ROOT / "13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Evaluation_Register.csv"),
        },
        "source_monitoring": {
            "latest_discovery_run_at": discovery_audit.get("run_at"),
            "latest_rss_sources": discovery_audit.get("rss_sources"),
            "latest_rss_items_scanned": discovery_audit.get("rss_items_scanned"),
            "latest_new_candidates": discovery_audit.get("new_candidates"),
            "latest_error_count": len(source_errors) if isinstance(source_errors, list) else None,
        },
        "change_tracking": {
            "tracked_artifacts": int(len(hashes)),
            "new_or_modified_or_missing": int(len(changed)),
            "change_register": str(CHANGE_OUT.relative_to(ROOT)),
            "artifact_hash_register": str(HASH_OUT.relative_to(ROOT)),
        },
        "governance_note": "Lineage/integrity evidence only. This audit does not convert structural or stress outputs into PD, LGD, EAD, ECL, bank/CRA ratings, or automated lending decisions.",
    }
    atomic_json(manifest, MANIFEST_OUT)
    append_audit({
        "phase": "13I",
        "run_at": now,
        "status": status,
        "audit_version": AUDIT_VERSION,
        "git_sha": execution_sha,
        "hard_failure_count": len(hard_failures),
        "warning_count": len(warnings),
        "tracked_artifacts": int(len(hashes)),
        "changed_artifacts": int(len(changed)),
    })

    print("PHASE 13I - MODEL / VERSION / ARTIFACT LINEAGE AUDIT")
    print("=" * 70)
    print(f"Audit version                  : {AUDIT_VERSION}")
    print(f"Execution git SHA              : {execution_sha}")
    print(f"Tracked artifacts              : {len(hashes)}")
    print(f"Required artifacts present     : {(hashes['required'] & hashes['exists']).sum()}/{hashes['required'].sum()}")
    print(f"Frozen reference hash checks   : {sum(int(x['pass']) for x in reference_checks)}/{len(reference_checks)}")
    print(f"Phase 13E reproduction gate    : {e13_pass}")
    print(f"Phase 13F deterministic gate   : {f13_pass}")
    print(f"Governance guardrails confirmed: {all(governance_check.values())}")
    print(f"Monte Carlo method status      : {mc_status}")
    print(f"Discovery source errors        : {len(source_errors) if isinstance(source_errors, list) else 'N/A'}")
    print(f"Changed/new/missing artifacts  : {len(changed)}")
    print(f"FINAL STATUS                   : {status}")
    print(f"Manifest                       : {MANIFEST_OUT.relative_to(ROOT)}")
    print(f"Hash register                  : {HASH_OUT.relative_to(ROOT)}")
    print(f"Change register                : {CHANGE_OUT.relative_to(ROOT)}")

    if hard_failures:
        print("\nHARD FAILURES")
        for item in hard_failures:
            print(f"- {item}")
    if warnings:
        print("\nGOVERNED WARNINGS")
        for item in warnings:
            print(f"- {item}")

    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
