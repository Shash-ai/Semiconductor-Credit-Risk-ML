from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import banking_dashboard_v2 as core
import banking_dashboard_v3 as ui
import banking_dashboard_v3_1 as hardened


ROOT = Path(__file__).resolve().parents[1]
PHASE13 = ROOT / "13_Continuous_Ingestion"

SOURCE_REGISTRY = PHASE13 / "00_Config" / "source_registry.csv"
CANDIDATES = PHASE13 / "02_Candidates" / "Project_Discovery_Candidates.csv"
DISCOVERY_AUDIT = PHASE13 / "03_Audit" / "Discovery_Run_Log.jsonl"
VERIFICATION_QUEUE = PHASE13 / "04_Verification" / "Verification_Queue.csv"
STRUCTURED_CANDIDATES = PHASE13 / "04_Verification" / "Structured_Project_Candidates.csv"
VERIFICATION_AUDIT = PHASE13 / "04_Verification" / "Verification_Run_Log.jsonl"
CANONICAL_REVIEW = PHASE13 / "05_Canonicalization" / "Canonicalization_Review.csv"
CANONICAL_STAGING = PHASE13 / "05_Canonicalization" / "Canonical_Staging.csv"
CANONICAL_CONFLICTS = PHASE13 / "05_Canonicalization" / "Canonicalization_Conflicts.csv"
CANONICAL_AUDIT = PHASE13 / "05_Canonicalization" / "Canonicalization_Run_Log.jsonl"
FROZEN_VALIDATION = PHASE13 / "06_Frozen_Model" / "artifacts" / "Frozen_Model_Validation.json"
FROZEN_MANIFEST = PHASE13 / "06_Frozen_Model" / "artifacts" / "Frozen_Model_Manifest.json"
FROZEN_INFERENCE = PHASE13 / "06_Frozen_Model" / "Frozen_Model_New_Project_Inference.csv"
FROZEN_AUDIT = PHASE13 / "06_Frozen_Model" / "Frozen_Model_Run_Log.jsonl"
EVALUATION_REGISTER = PHASE13 / "07_Automated_Evaluation" / "New_Project_Evaluation_Register.csv"
DETERMINISTIC_STRESS = PHASE13 / "07_Automated_Evaluation" / "New_Project_Deterministic_Stress.csv"
MC_STATUS = PHASE13 / "07_Automated_Evaluation" / "New_Project_Monte_Carlo_Status.csv"
BANKING_STATUS = PHASE13 / "07_Automated_Evaluation" / "New_Project_Banking_Evidence_Status.csv"
METHOD_VALIDATION = PHASE13 / "07_Automated_Evaluation" / "Phase_13F_Method_Validation.json"
EVALUATION_AUDIT = PHASE13 / "07_Automated_Evaluation" / "Automated_Evaluation_Run_Log.jsonl"


def _csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, UnicodeDecodeError, OSError):
        return pd.DataFrame()


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}


def _latest_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError, OSError):
        return {}
    for line in reversed(lines):
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    return {}


def _text(value: Any, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    text = str(value).strip()
    return text if text else fallback


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass", "passed", "success"}


def _first_timestamp(*payloads: dict[str, Any]) -> str:
    keys = ("run_at", "completed_at", "validated_at", "evaluated_at", "started_at", "discovered_at", "timestamp")
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if value:
                return str(value)
    return "Not yet published"


def _mtime(path: Path) -> str:
    if not path.exists():
        return "Not yet published"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
    except OSError:
        return "Not yet published"


def _status_count(df: pd.DataFrame, column: str, contains: str | None = None, equals: str | None = None) -> int:
    if df.empty or column not in df.columns:
        return 0
    values = df[column].fillna("").astype(str)
    if equals is not None:
        return int(values.eq(equals).sum())
    if contains is not None:
        return int(values.str.contains(contains, case=False, regex=False, na=False).sum())
    return int(values.ne("").sum())


def _native_record_table(df: pd.DataFrame, columns: list[str], height: int = 320) -> None:
    if df.empty:
        st.caption("No records are currently available for this stage.")
        return
    display = df[[c for c in columns if c in df.columns]].copy()
    if display.empty:
        st.caption("The current file does not contain displayable fields for this view.")
        return
    st.dataframe(display, width="stretch", hide_index=True, height=height)


def _model_validation_status(frozen_validation: dict[str, Any]) -> tuple[str, str]:
    if not frozen_validation:
        return "Runtime output not published", "Phase 13E validation exists locally only or has not yet been produced in this runtime."

    raw_ok = _bool(frozen_validation.get("raw_feature_contract_pass"))
    z_ok = _bool(frozen_validation.get("stored_z_reconstruction_pass"))
    pca_ok = _bool(frozen_validation.get("pca_reconstruction_pass"))
    cluster_ok = _bool(frozen_validation.get("cluster_recovery_pass"))
    if raw_ok and z_ok and pca_ok and cluster_ok:
        return "VALIDATED", "Historical feature, scaling, PCA and cluster-recovery gates passed."

    return _text(frozen_validation.get("status"), "REVIEW REQUIRED"), "At least one frozen-reference validation gate has not passed."


def _deterministic_status(method_validation: dict[str, Any]) -> tuple[str, str]:
    block = method_validation.get("deterministic_stress", {}) if isinstance(method_validation, dict) else {}
    if not isinstance(block, dict) or not block:
        return "Runtime output not published", "Phase 13F method validation is not available in this runtime."
    passed = _bool(block.get("deterministic_method_reproduction_pass"))
    if passed:
        err = block.get("overall_score_max_abs_error")
        suffix = f" Maximum reproduction error: {err}." if err is not None else ""
        return "VALIDATED", "Historical deterministic stress method reproduced successfully." + suffix
    return "REVIEW REQUIRED", "Historical deterministic stress reproduction gate has not passed."


def _mc_status(method_validation: dict[str, Any]) -> tuple[str, str]:
    block = method_validation.get("monte_carlo", {}) if isinstance(method_validation, dict) else {}
    if not isinstance(block, dict) or not block:
        return "Runtime output not published", "Monte Carlo method-state output is not available in this runtime."
    return _text(block.get("status")), _text(block.get("reason"), "No explanatory note is available.")


def _pipeline_health(
    frozen_validation: dict[str, Any],
    method_validation: dict[str, Any],
    latest_audits: list[dict[str, Any]],
) -> tuple[str, str]:
    failures = [
        audit for audit in latest_audits
        if str(audit.get("status", "")).upper() in {"FAILED", "FAILED_SAFE", "ERROR"}
    ]
    if failures:
        return "REVIEW REQUIRED", "At least one latest runtime audit reports a fail-safe or error state."

    model_status, _ = _model_validation_status(frozen_validation)
    det_status, _ = _deterministic_status(method_validation)
    if model_status == "VALIDATED" and det_status == "VALIDATED":
        return "READY FOR SCHEDULING", "Core structural and deterministic evaluation gates are validated. Monte Carlo remains separately governed."

    if not frozen_validation and not method_validation:
        return "RUNTIME OUTPUTS NOT PUBLISHED", "The dashboard code is present, but local Phase 13 runtime artifacts are not yet in this deployment."

    return "PARTIAL / REVIEW", "Some Phase 13 runtime validation outputs are unavailable or have not passed their gate."


def page_continuous_pipeline(master: pd.DataFrame) -> None:
    ui.header(
        "Continuous Data Pipeline",
        "Official-source intake, human-gated verification, frozen-model inference and automated public-data evaluation for newly approved semiconductor projects.",
    )

    registry = _csv(SOURCE_REGISTRY)
    candidates = _csv(CANDIDATES)
    verification = _csv(VERIFICATION_QUEUE)
    structured = _csv(STRUCTURED_CANDIDATES)
    canonical_review = _csv(CANONICAL_REVIEW)
    staging = _csv(CANONICAL_STAGING)
    conflicts = _csv(CANONICAL_CONFLICTS)
    inference = _csv(FROZEN_INFERENCE)
    evaluation = _csv(EVALUATION_REGISTER)
    deterministic = _csv(DETERMINISTIC_STRESS)
    mc = _csv(MC_STATUS)
    banking = _csv(BANKING_STATUS)

    frozen_validation = _json(FROZEN_VALIDATION)
    frozen_manifest = _json(FROZEN_MANIFEST)
    method_validation = _json(METHOD_VALIDATION)

    discovery_audit = _latest_jsonl(DISCOVERY_AUDIT)
    verification_audit = _latest_jsonl(VERIFICATION_AUDIT)
    canonical_audit = _latest_jsonl(CANONICAL_AUDIT)
    frozen_audit = _latest_jsonl(FROZEN_AUDIT)
    evaluation_audit = _latest_jsonl(EVALUATION_AUDIT)
    audits = [discovery_audit, verification_audit, canonical_audit, frozen_audit, evaluation_audit]

    health, health_note = _pipeline_health(frozen_validation, method_validation, audits)
    active_sources = 0
    if not registry.empty:
        if "active" in registry.columns:
            active_sources = int(registry["active"].astype(str).str.lower().isin({"true", "1", "yes"}).sum())
        else:
            active_sources = len(registry)

    last_scan = _first_timestamp(discovery_audit)
    if last_scan == "Not yet published":
        last_scan = _mtime(DISCOVERY_AUDIT)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pipeline state", health)
    c2.metric("Active official/reference sources", active_sources)
    c3.metric("Canonical projects", len(master))
    c4.metric("New projects evaluated", len(evaluation))
    st.caption(health_note)

    st.subheader("Lifecycle")
    l1, l2, l3, l4, l5 = st.columns(5)
    l1.metric("1 · Discovered", len(candidates))
    l2.metric("2 · Verification queue", len(verification))
    l3.metric("3 · Canonical staging", len(staging))
    l4.metric("4 · Structural inference", len(inference))
    l5.metric("5 · Evaluation register", len(evaluation))
    st.caption("DISCOVERED → SOURCE VERIFIED → CANONICALIZED → MODEL EVALUATED → DASHBOARD ACTIVE. Human review remains mandatory where evidence is ambiguous or incomplete.")

    st.subheader("Method controls")
    structural_status, structural_note = _model_validation_status(frozen_validation)
    det_status, det_note = _deterministic_status(method_validation)
    monte_status, monte_note = _mc_status(method_validation)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Structural model", structural_status)
    m2.metric("Deterministic stress", det_status)
    m3.metric("Monte Carlo", monte_status)
    m4.metric("Banking treatment", "VERIFIED DATA ONLY")

    with st.expander("Method-control details", expanded=False):
        st.markdown(f"**Structural model:** {structural_note}")
        st.markdown(f"**Deterministic stress:** {det_note}")
        st.markdown(f"**Monte Carlo:** {monte_note}")
        model_version = frozen_manifest.get("model_version") or frozen_validation.get("model_version")
        st.markdown(f"**Frozen model version:** {_text(model_version)}")
        st.markdown("**Credit guardrail:** structural segment and stress outputs are research decision-support; they are not PD, LGD, EAD, ECL, a bank/CRA rating, or an automated approval/rejection decision.")

    st.subheader("Runtime activity")
    activity = pd.DataFrame(
        [
            ["13B Discovery", _text(discovery_audit.get("status")), _first_timestamp(discovery_audit), _text(discovery_audit.get("new_candidates"), "0")],
            ["13C Verification", _text(verification_audit.get("status")), _first_timestamp(verification_audit), _text(verification_audit.get("candidates_processed"), str(len(structured)))],
            ["13D Canonicalization", _text(canonical_audit.get("status")), _first_timestamp(canonical_audit), _text(canonical_audit.get("staged_rows"), str(len(staging)))],
            ["13E Frozen inference", _text(frozen_audit.get("status")), _first_timestamp(frozen_audit), _text(frozen_audit.get("new_canonical_projects"), str(len(inference)))],
            ["13F Automated evaluation", _text(evaluation_audit.get("status")), _first_timestamp(evaluation_audit), _text(evaluation_audit.get("new_structurally_evaluated_projects_seen"), str(len(evaluation)))],
        ],
        columns=["Stage", "Latest status", "Latest runtime timestamp", "Rows / new items"],
    )
    st.dataframe(activity, width="stretch", hide_index=True)
    st.caption(f"Latest discovery scan visible to this runtime: {last_scan}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "New project intake",
        "Verification & canonicalization",
        "Model evaluation",
        "Source registry",
    ])

    with tab1:
        if candidates.empty:
            st.info("No discovery candidates are currently published in this runtime. A zero-candidate state is valid when no new approval is detected.")
        else:
            _native_record_table(
                candidates.sort_values("discovered_at", ascending=False, na_position="last") if "discovered_at" in candidates.columns else candidates,
                [
                    "discovery_id", "source_name", "title", "published_at", "candidate_score",
                    "candidate_status", "verification_status", "canonicalization_status",
                    "model_evaluation_status", "url",
                ],
                420,
            )
            review_count = _status_count(candidates, "candidate_status", contains="REVIEW")
            st.caption(f"Candidates currently carrying a review-oriented status: {review_count}")

    with tab2:
        v1, v2, v3 = st.columns(3)
        v1.metric("Structured candidates", len(structured))
        v2.metric("Review rows", len(canonical_review))
        v3.metric("Conflicts", len(conflicts))

        st.markdown("#### Verification queue")
        _native_record_table(
            verification,
            [
                "discovery_id", "title", "verification_status", "review_status",
                "possible_existing_project", "multi_project_announcement", "review_reason", "url",
            ],
            300,
        )

        st.markdown("#### Canonicalization review")
        _native_record_table(
            canonical_review,
            [
                "discovery_id", "review_decision", "confirmed_company", "confirmed_state",
                "confirmed_project_type", "confirmed_investment_crore", "reviewer", "review_notes",
            ],
            300,
        )

        if not conflicts.empty:
            st.markdown("#### Canonicalization conflicts")
            _native_record_table(conflicts, list(conflicts.columns)[:10], 260)

    with tab3:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Structural inference rows", len(inference))
        e2.metric("Deterministic stress rows", len(deterministic))
        e3.metric("Monte Carlo status rows", len(mc))
        e4.metric("Banking evidence rows", len(banking))

        if evaluation.empty:
            st.info("No newly canonicalized projects require automated Phase 13 evaluation yet.")
        else:
            _native_record_table(
                evaluation,
                [
                    "project_id", "company", "state", "project_type", "investment_crore",
                    "predicted_validated_cluster", "structural_extrapolation_signal",
                    "deterministic_stress_status", "baseline_score", "severe_score",
                    "monte_carlo_status", "banking_evidence_status",
                    "overall_automated_evaluation_status", "next_required_action", "evaluated_at",
                ],
                460,
            )

    with tab4:
        if registry.empty:
            st.warning("The Phase 13 source registry is unavailable in this runtime.")
        else:
            _native_record_table(
                registry,
                ["source_id", "source_name", "source_type", "authority", "active", "url", "notes"],
                320,
            )
        st.caption("Discovery is source-backed. A fetched announcement is not automatically treated as verified project-finance or banking data.")

    st.divider()
    st.markdown("**Activation rule:** a newly discovered project is not allowed into the canonical research dataset or banking decision-support layer merely because an online announcement exists. Verification, duplicate/entity reconciliation and controlled canonicalization remain separate gates.")


def _install() -> None:
    # Keep V3.1's hardened HTML renderer for the existing dashboard, then install the V3
    # institutional page overrides. Phase 13G itself uses native Streamlit components for
    # records and status views to avoid raw-markup rendering failures.
    hardened.install_patch()
    ui.install_overrides()

    ui.GROUPS = {
        "Executive": ["Portfolio Overview", "Credit Committee"],
        "Project Review": [
            "Project Dossier",
            "Borrower Financials",
            "Project Finance",
            "Execution Risk",
        ],
        "Risk Analytics": [
            "Stress & Tail Risk",
            "Security & Recovery",
            "Early Warning System",
        ],
        "Portfolio & Evidence": [
            "Evidence & Data Gaps",
            "Portfolio Allocation",
        ],
        "Data Operations": ["Continuous Pipeline"],
        "Governance": ["Governance"],
    }
    ui.PAGE_LABELS["Continuous Pipeline"] = "Continuous pipeline"
    core.sidebar = ui.sidebar


def render_app() -> None:
    _install()
    st.markdown(core.CSS, unsafe_allow_html=True)

    master = core.load_master()
    page, filtered = core.sidebar(master)

    if page == "Continuous Pipeline":
        page_continuous_pipeline(master)
        return

    if filtered.empty:
        st.warning("No projects match the current filters.")
        return

    if page == "Portfolio Overview":
        core.page_overview(filtered)
    elif page == "Credit Committee":
        core.page_committee(filtered)
    elif page == "Project Dossier":
        core.page_dossier(filtered)
    elif page == "Borrower Financials":
        core.page_borrower(filtered)
    elif page == "Project Finance":
        core.page_project_finance(filtered)
    elif page == "Execution Risk":
        core.page_execution(filtered)
    elif page == "Stress & Tail Risk":
        core.page_stress()
    elif page == "Security & Recovery":
        core.page_security(filtered)
    elif page == "Early Warning System":
        core.page_ews(filtered)
    elif page == "Evidence & Data Gaps":
        core.page_evidence(filtered)
    elif page == "Portfolio Allocation":
        core.page_allocation()
    elif page == "Governance":
        core.page_governance()
    else:
        st.error(f"Unknown dashboard page: {page}")
