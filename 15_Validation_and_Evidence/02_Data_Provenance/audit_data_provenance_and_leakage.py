from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "15_Validation_and_Evidence" / "00_Config" / "provenance_leakage_audit_config.json"
OUT_DIR = ROOT / "15_Validation_and_Evidence" / "02_Data_Provenance"

AUDIT_OUT = OUT_DIR / "Data_Provenance_Audit.csv"
LINEAGE_OUT = OUT_DIR / "Data_Lineage_Register.csv"
COVERAGE_OUT = OUT_DIR / "Source_Provenance_Coverage.csv"
FEATURE_OUT = OUT_DIR / "Feature_Reconstruction_Audit.csv"
HASH_OUT = OUT_DIR / "Frozen_Artifact_Hash_Verification.csv"
LEAKAGE_OUT = OUT_DIR / "Leakage_Risk_Register.csv"
RUN_LOG = OUT_DIR / "Phase_15B_Run_Log.jsonl"

AUDIT_VERSION = "SCI_DATA_PROVENANCE_LEAKAGE_AUDIT_V1"


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


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def add_check(rows, check_id, category, severity, status, observed, expected, detail) -> None:
    rows.append({
        "check_id": check_id,
        "category": category,
        "severity": severity,
        "status": status,
        "observed": observed,
        "expected": expected,
        "detail": detail,
        "audit_version": AUDIT_VERSION,
    })


def status(condition: bool) -> str:
    return "PASS" if bool(condition) else "FAIL"


def text_blob(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ["project_name", "technology", "application", "project_type"] if c in df.columns]
    out = pd.Series("", index=df.index, dtype=str)
    for col in cols:
        out = out + " " + df[col].fillna("").astype(str)
    return out.str.lower().str.replace(r"\s+", " ", regex=True)


def contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.str.contains(pattern, regex=True, case=False, na=False)


def build_raw_features(ecosystem: pd.DataFrame, raw_features: list[str]) -> pd.DataFrame:
    """Exact structural-feature definitions used by the frozen Phase 13 model."""
    df = ecosystem.copy()
    required = [
        "ecosystem_id", "project_scope", "company", "state",
        "financial_measure_crore", "project_type_standardized",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Ecosystem missing feature-engineering columns: {missing}")

    financial = pd.to_numeric(df["financial_measure_crore"], errors="coerce")
    if financial.isna().any():
        bad = df.loc[financial.isna(), "ecosystem_id"].astype(str).tolist()
        raise RuntimeError(f"financial_measure_crore missing for ecosystem rows: {bad}")

    df["financial_rank_within_scope"] = financial.groupby(df["project_scope"]).rank(
        method="average", ascending=True, pct=True
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
        blob, r"artificial intelligence|ai accelerator|edge[- ]?ai|\bai\b|machine learning|\bml acceleration\b"
    ).astype(float)
    df["is_telecom_related"] = contains(
        blob,
        r"telecommunications|telecom|\b5g\b|\b4g\b|\blte\b|nb[- ]?iot|broadband|gpon|fttx|satcom|satellite communication|rf/radar|\brf\b|\bradar\b",
    ).astype(float)
    df["is_automotive_related"] = contains(blob, r"automotive|automobile|\btire\b|motor control").astype(float)
    df["is_iot_related"] = contains(blob, r"\biot\b|nb[- ]?iot").astype(float)
    df["is_medical_related"] = contains(blob, r"medical|cardiac|health").astype(float)
    partner = df.get("technology_partner", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
    df["has_technology_partner"] = partner.ne("").astype(float)

    missing_contract = [c for c in raw_features if c not in df.columns]
    if missing_contract:
        raise RuntimeError(f"Raw feature contract cannot be generated: {missing_contract}")
    out = df[["ecosystem_id"] + raw_features].copy()
    for feature in raw_features:
        out[feature] = pd.to_numeric(out[feature], errors="coerce")
    return out


def coverage_row(dataset: str, df: pd.DataFrame, fields: list[str], affirmative: dict[str, str] | None = None) -> dict:
    row = {"dataset": dataset, "rows": int(len(df))}
    for field in fields:
        if field not in df.columns:
            row[f"{field}_coverage_pct"] = 0.0
        else:
            row[f"{field}_coverage_pct"] = float(df[field].map(clean).ne("").mean() * 100.0) if len(df) else 0.0
    for field, expected in (affirmative or {}).items():
        if field not in df.columns:
            row[f"{field}_affirmative_pct"] = 0.0
        else:
            good = df[field].astype(str).str.strip().str.upper().eq(expected.upper())
            row[f"{field}_affirmative_pct"] = float(good.mean() * 100.0) if len(df) else 0.0
    return row


def compare_string_field(source: pd.DataFrame, ecosystem: pd.DataFrame, key: str, field: str) -> list[str]:
    merged = source[[key, field]].merge(
        ecosystem[[key, field]], on=key, how="inner", suffixes=("_source", "_ecosystem")
    )
    mismatch = merged[
        merged[f"{field}_source"].map(clean).ne(merged[f"{field}_ecosystem"].map(clean))
    ]
    return mismatch[key].astype(str).tolist()


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("audit_version") != AUDIT_VERSION:
        raise RuntimeError(f"Config version mismatch: {config.get('audit_version')} != {AUDIT_VERSION}")

    paths = {name: ROOT / rel for name, rel in config["files"].items()}
    missing_files = [str(path.relative_to(ROOT)) for path in paths.values() if not path.exists()]
    if missing_files:
        raise RuntimeError(f"Required Phase 15B inputs missing: {missing_files}")

    mfg = read_csv(paths["manufacturing_canonical"])
    dli = read_csv(paths["design_canonical"])
    ecosystem = read_csv(paths["ecosystem_master"])
    features = read_csv(paths["feature_matrix"])
    feature_selection = read_csv(paths["feature_selection_audit"])
    manifest = json.loads(paths["frozen_manifest"].read_text(encoding="utf-8"))

    raw_features = [str(x) for x in manifest.get("raw_features", [])]
    z_features = [f"z_{x}" for x in raw_features]
    raw_tol = float(config.get("raw_feature_tolerance", 1e-12))
    z_tol = float(config.get("z_feature_tolerance", 1e-10))
    amount_tol = float(config.get("amount_tolerance", 1e-8))
    checks = []

    schemas = [
        ("SCHEMA_MFG", mfg, {"project_id", "company", "state", "project_type_standardized", "approval_date", "approval_year", "investment_crore", "source_document", "source_page", "source", "data_quality_flag"}),
        ("SCHEMA_DLI", dli, {"dli_project_id", "company", "project_outlay_crore", "source_document", "source_url", "source_type", "source_authority", "official_source_confirmed", "financial_support_confirmed", "data_quality_flag"}),
        ("SCHEMA_ECOSYSTEM", ecosystem, {"ecosystem_id", "source_project_id", "project_scope", "company", "state", "project_type_standardized", "financial_measure_crore", "source_document", "source_authority", "data_quality_flag"}),
    ]
    for cid, df, required in schemas:
        missing = sorted(required - set(df.columns))
        add_check(checks, cid, "SCHEMA", "HARD", status(not missing), ";".join(missing) if missing else "NONE", "NONE", "Required-column audit.")

    for cid, df, key in [
        ("KEY_MFG_UNIQUE", mfg, "project_id"),
        ("KEY_DLI_UNIQUE", dli, "dli_project_id"),
        ("KEY_ECOSYSTEM_UNIQUE", ecosystem, "ecosystem_id"),
        ("KEY_FEATURE_UNIQUE", features, "ecosystem_id"),
    ]:
        duplicates = int(df[key].astype(str).duplicated().sum())
        add_check(checks, cid, "KEY_INTEGRITY", "HARD", status(duplicates == 0), duplicates, 0, f"Duplicate count for {key}.")

    source_ids = set(mfg["project_id"].astype(str)) | set(dli["dli_project_id"].astype(str))
    ecosystem_source_ids = set(ecosystem["source_project_id"].astype(str))
    add_check(checks, "SOURCE_ID_SET_MATCH", "LINEAGE", "HARD", status(source_ids == ecosystem_source_ids), len(source_ids.symmetric_difference(ecosystem_source_ids)), 0, "Canonical source-project IDs must exactly equal ecosystem source_project_id values.")
    add_check(checks, "ROW_COUNT_COMPOSITION", "LINEAGE", "HARD", status(len(mfg) + len(dli) == len(ecosystem)), len(ecosystem), len(mfg) + len(dli), "Ecosystem rows must equal manufacturing + DLI canonical rows.")

    reference_rows = int(manifest.get("reference_universe_rows", len(ecosystem)))
    add_check(checks, "FROZEN_REFERENCE_ROW_COUNT", "FROZEN_CONTRACT", "HARD", status(len(ecosystem) == reference_rows and len(features) == reference_rows), f"ecosystem={len(ecosystem)};features={len(features)}", reference_rows, "Frozen reference-universe row count must remain unchanged.")

    eco_mfg = ecosystem[ecosystem["project_scope"].astype(str).eq("Manufacturing")].copy()
    eco_dli = ecosystem[ecosystem["project_scope"].astype(str).eq("Semiconductor Design")].copy()
    mfg_left = mfg.rename(columns={"project_id": "source_project_id"})
    dli_left = dli.rename(columns={"dli_project_id": "source_project_id"})

    mfg_mismatches = []
    for field in ["company", "state", "project_type_standardized"]:
        for pid in compare_string_field(mfg_left, eco_mfg, "source_project_id", field):
            mfg_mismatches.append(f"{field}:{pid}")
    add_check(checks, "MFG_STRING_LINEAGE", "LINEAGE", "HARD", status(not mfg_mismatches), len(mfg_mismatches), 0, "Manufacturing company/state/project-type lineage. " + ";".join(mfg_mismatches[:20]))

    dli_mismatch = compare_string_field(dli_left, eco_dli, "source_project_id", "company")
    add_check(checks, "DLI_STRING_LINEAGE", "LINEAGE", "HARD", status(not dli_mismatch), len(dli_mismatch), 0, "DLI company lineage. " + ";".join(dli_mismatch[:20]))

    mfg_amount = mfg_left[["source_project_id", "investment_crore"]].merge(eco_mfg[["source_project_id", "financial_measure_crore"]], on="source_project_id", how="inner")
    mfg_diff = (pd.to_numeric(mfg_amount["investment_crore"], errors="coerce") - pd.to_numeric(mfg_amount["financial_measure_crore"], errors="coerce")).abs()
    mfg_amount_ok = len(mfg_amount) == len(mfg) and mfg_diff.notna().all() and mfg_diff.le(amount_tol).all()
    add_check(checks, "MFG_AMOUNT_LINEAGE", "LINEAGE", "HARD", status(mfg_amount_ok), float(mfg_diff.max()) if len(mfg_diff) else np.nan, f"<= {amount_tol}", "Manufacturing investment_crore must reproduce ecosystem financial_measure_crore.")

    dli_amount = dli_left[["source_project_id", "project_outlay_crore"]].merge(eco_dli[["source_project_id", "financial_measure_crore"]], on="source_project_id", how="inner")
    dli_diff = (pd.to_numeric(dli_amount["project_outlay_crore"], errors="coerce") - pd.to_numeric(dli_amount["financial_measure_crore"], errors="coerce")).abs()
    dli_amount_ok = len(dli_amount) == len(dli) and dli_diff.notna().all() and dli_diff.le(amount_tol).all()
    add_check(checks, "DLI_AMOUNT_LINEAGE", "LINEAGE", "HARD", status(dli_amount_ok), float(dli_diff.max()) if len(dli_diff) else np.nan, f"<= {amount_tol}", "DLI project_outlay_crore must reproduce ecosystem financial_measure_crore.")

    approval_date = pd.to_datetime(mfg["approval_date"], errors="coerce")
    approval_year = pd.to_numeric(mfg["approval_year"], errors="coerce")
    comparable = approval_date.notna() & approval_year.notna()
    approval_mismatch = int((approval_date[comparable].dt.year.astype(float) != approval_year[comparable]).sum())
    add_check(checks, "MFG_APPROVAL_DATE_YEAR", "TEMPORAL_PROVENANCE", "HARD", status(approval_mismatch == 0), approval_mismatch, 0, "approval_year must equal approval_date year where both exist.")

    financial = pd.to_numeric(ecosystem["financial_measure_crore"], errors="coerce")
    bad_financial = int((financial.isna() | (financial <= 0)).sum())
    add_check(checks, "ECOSYSTEM_FINANCIAL_MEASURE_POSITIVE", "DATA_QUALITY", "HARD", status(bad_financial == 0), bad_financial, 0, "All ecosystem rows need positive financial_measure_crore for structural rank/share features.")

    coverage = pd.DataFrame([
        coverage_row("manufacturing_canonical", mfg, ["source_document", "source_page", "source", "data_quality_flag"]),
        coverage_row("design_canonical", dli, ["source_document", "source_url", "source_type", "source_authority", "data_quality_flag"], {"official_source_confirmed": "YES", "financial_support_confirmed": "YES"}),
        coverage_row("ecosystem_master", ecosystem, ["source_project_id", "source_document", "source_authority", "data_quality_flag", "financial_measure_crore"]),
    ])

    mfg_core = mfg["source_document"].map(clean).ne("") & mfg["source"].map(clean).ne("") & mfg["data_quality_flag"].map(clean).ne("")
    dli_core = dli["source_document"].map(clean).ne("") & dli["source_url"].map(clean).ne("") & dli["source_authority"].map(clean).ne("") & dli["data_quality_flag"].map(clean).ne("")
    eco_core = ecosystem["source_project_id"].map(clean).ne("") & ecosystem["source_document"].map(clean).ne("") & ecosystem["source_authority"].map(clean).ne("") & ecosystem["data_quality_flag"].map(clean).ne("")
    for cid, label, mask in [("MFG_CORE_PROVENANCE", "manufacturing", mfg_core), ("DLI_CORE_PROVENANCE", "DLI", dli_core), ("ECOSYSTEM_CORE_PROVENANCE", "ecosystem", eco_core)]:
        missing_count = int((~mask).sum())
        add_check(checks, cid, "PROVENANCE", "HARD", status(missing_count == 0), missing_count, 0, f"Rows missing minimum source identity in {label} layer.")

    dli_unconfirmed_official = int((~dli["official_source_confirmed"].astype(str).str.upper().eq("YES")).sum())
    dli_unconfirmed_support = int((~dli["financial_support_confirmed"].astype(str).str.upper().eq("YES")).sum())
    add_check(checks, "DLI_OFFICIAL_SOURCE_CONFIRMED", "PROVENANCE", "HARD", status(dli_unconfirmed_official == 0), dli_unconfirmed_official, 0, "Canonical DLI rows must be official-source-confirmed.")
    add_check(checks, "DLI_FINANCIAL_SUPPORT_CONFIRMED", "PROVENANCE", "HARD", status(dli_unconfirmed_support == 0), dli_unconfirmed_support, 0, "Canonical DLI rows must retain explicit financial-support evidence status.")

    dli_year_missing = int(dli.get("approval_year", pd.Series(index=dli.index, dtype=object)).map(clean).eq("").sum())
    dli_date_missing = int(dli.get("approval_date", pd.Series(index=dli.index, dtype=object)).map(clean).eq("").sum())
    add_check(checks, "DLI_EXACT_APPROVAL_TIMING", "TEMPORAL_PROVENANCE", "SOFT", "WARN" if dli_year_missing or dli_date_missing else "PASS", f"missing_year={dli_year_missing};missing_date={dli_date_missing}", "Publicly verified exact timing where available", "Missing DLI timing remains missing; it must not be invented for historical point-in-time claims.")

    feature_ids = set(features["ecosystem_id"].astype(str))
    ecosystem_ids = set(ecosystem["ecosystem_id"].astype(str))
    add_check(checks, "FEATURE_ID_SET_MATCH", "FEATURE_CONTRACT", "HARD", status(feature_ids == ecosystem_ids), len(feature_ids.symmetric_difference(ecosystem_ids)), 0, "Feature-matrix IDs must exactly match ecosystem IDs.")

    missing_feature_cols = [c for c in raw_features + z_features if c not in features.columns]
    add_check(checks, "FEATURE_COLUMNS_PRESENT", "FEATURE_CONTRACT", "HARD", status(not missing_feature_cols), ";".join(missing_feature_cols) if missing_feature_cols else "NONE", "NONE", "All frozen raw + z features must exist.")

    selected = set(feature_selection.loc[feature_selection["status"].astype(str).str.upper().eq("SELECTED"), "feature"].astype(str))
    feature_contract_match = selected == set(raw_features)
    add_check(checks, "FEATURE_SELECTION_CONTRACT_MATCH", "FEATURE_CONTRACT", "HARD", status(feature_contract_match), ";".join(sorted(selected.symmetric_difference(set(raw_features)))) if not feature_contract_match else "NONE", "NONE", "Feature-selection audit must equal frozen manifest raw-feature contract.")

    regenerated = build_raw_features(ecosystem, raw_features)
    compared = regenerated.merge(features[["ecosystem_id"] + raw_features], on="ecosystem_id", how="inner", suffixes=("_calc", "_stored"))
    feature_rows = []
    raw_pass = len(compared) == len(ecosystem)
    for feature in raw_features:
        calc = pd.to_numeric(compared[f"{feature}_calc"], errors="coerce")
        stored = pd.to_numeric(compared[f"{feature}_stored"], errors="coerce")
        diff = (calc - stored).abs()
        max_err = float(diff.max()) if len(diff) else np.inf
        passed = bool(diff.notna().all() and max_err <= raw_tol)
        raw_pass = raw_pass and passed
        feature_rows.append({"feature": feature, "layer": "RAW", "max_abs_error": max_err, "tolerance": raw_tol, "status": status(passed), "definition_source": "Frozen Phase 13 feature-engineering contract"})
    add_check(checks, "RAW_FEATURE_RECONSTRUCTION", "FEATURE_REPRODUCTION", "HARD", status(raw_pass), max([r["max_abs_error"] for r in feature_rows if r["layer"] == "RAW"], default=np.nan), f"<= {raw_tol}", "Re-derived raw features must reproduce authoritative stored features.")

    raw_ref = features.set_index("ecosystem_id")[raw_features].astype(float)
    means = raw_ref.mean(axis=0)
    scales = raw_ref.std(axis=0, ddof=0)
    zero_var = scales[scales <= 0].index.tolist()
    add_check(checks, "NO_ZERO_VARIANCE_RAW_FEATURES", "FEATURE_REPRODUCTION", "HARD", status(not zero_var), ";".join(zero_var) if zero_var else "NONE", "NONE", "Frozen ddof=0 scaling requires non-zero feature variance.")

    z_pass = not zero_var
    if not zero_var:
        z_calc = (raw_ref - means) / scales
        z_stored = features.set_index("ecosystem_id")[z_features].astype(float).copy()
        z_stored.columns = raw_features
        for feature in raw_features:
            diff = (z_calc[feature] - z_stored[feature]).abs()
            max_err = float(diff.max()) if len(diff) else np.inf
            passed = bool(diff.notna().all() and max_err <= z_tol)
            z_pass = z_pass and passed
            feature_rows.append({"feature": feature, "layer": "STANDARDIZED_Z", "max_abs_error": max_err, "tolerance": z_tol, "status": status(passed), "definition_source": "ddof=0 historical reference scaling"})
    add_check(checks, "Z_FEATURE_RECONSTRUCTION", "FEATURE_REPRODUCTION", "HARD", status(z_pass), max([r["max_abs_error"] for r in feature_rows if r["layer"] == "STANDARDIZED_Z"], default=np.nan), f"<= {z_tol}", "Stored z features must reproduce from raw features using ddof=0 scaling.")
    feature_audit = pd.DataFrame(feature_rows)

    expected_hashes = manifest.get("reference_hashes", {})
    hash_map = {
        "baseline_ecosystem_sha256": paths["ecosystem_master"],
        "authoritative_feature_matrix_sha256": paths["feature_matrix"],
        "pca_loadings_sha256": paths["pca_loadings"],
        "validated_assignments_sha256": paths["validated_assignments"],
        "pca_variance_sha256": paths["pca_variance"],
    }
    hash_rows = []
    for key, path in hash_map.items():
        expected = clean(expected_hashes.get(key))
        observed = sha256_file(path)
        passed = bool(expected and observed == expected)
        hash_rows.append({"hash_contract_key": key, "file": str(path.relative_to(ROOT)), "expected_sha256": expected, "observed_sha256": observed, "status": status(passed)})
    hash_df = pd.DataFrame(hash_rows)
    hash_failures = int((hash_df["status"] != "PASS").sum())
    add_check(checks, "FROZEN_HASH_CONTRACT", "FROZEN_CONTRACT", "HARD", status(hash_failures == 0), hash_failures, 0, "Frozen reference artifacts must match the manifest SHA-256 contract.")

    prohibited = [str(x).lower() for x in config.get("prohibited_outcome_tokens", [])]
    outcome_hits = {feature: [token for token in prohibited if token in feature.lower()] for feature in raw_features}
    outcome_hits = {k: v for k, v in outcome_hits.items() if v}
    identifiers = {"ecosystem_id", "source_project_id", "company", "state"} & set(raw_features)
    cohort_features = [x for x in config.get("cohort_relative_features", []) if x in raw_features]
    mfg_years = pd.to_numeric(mfg["approval_year"], errors="coerce").dropna()
    temporal_evidence = f"manufacturing approval years {int(mfg_years.min())}-{int(mfg_years.max())}" if len(mfg_years) else "manufacturing approval year unavailable"

    leakage_rows = [
        {"risk_id": "L01", "risk_type": "CONVENTIONAL_TARGET_LEAKAGE", "status": "PASS" if not outcome_hits else "FAIL", "severity": "CRITICAL", "evidence": json.dumps(outcome_hits, ensure_ascii=False), "interpretation": "The unsupervised raw feature contract must not contain downstream default/rating/stress/cluster outputs.", "required_action": "None" if not outcome_hits else "Remove contaminated features and revalidate the model."},
        {"risk_id": "L02", "risk_type": "DIRECT_IDENTIFIER_LEAKAGE", "status": "PASS" if not identifiers else "FAIL", "severity": "HIGH", "evidence": ";".join(sorted(identifiers)) if identifiers else "No direct ecosystem/company/state identifier features", "interpretation": "Direct identifiers should not become memorization features.", "required_action": "None" if not identifiers else "Remove direct identifiers from structural model inputs."},
        {"risk_id": "L03", "risk_type": "COHORT_RELATIVE_TRANSDUCTIVE_DEPENDENCE", "status": "WARN" if cohort_features else "PASS", "severity": "MEDIUM", "evidence": ";".join(cohort_features), "interpretation": "Rank/state-share/project-count depend on the contemporaneous ecosystem. This is acceptable for snapshot segmentation but a new project can change cohort-relative values.", "required_action": "Test leave-one-out and pseudo-new-project stability in Phase 15H."},
        {"risk_id": "L04", "risk_type": "HISTORICAL_POINT_IN_TIME_SCOPE", "status": "WARN", "severity": "HIGH", "evidence": temporal_evidence + f"; DLI exact approval year missing rows={dli_year_missing}", "interpretation": "The frozen model is a cross-sectional ecosystem snapshot, not an as-of-each-approval-date historical backtest.", "required_action": "Do not claim historical prediction performance; build rolling point-in-time cohorts only if separately validated."},
        {"risk_id": "L05", "risk_type": "OBSERVED_DEFAULT_TARGET_AVAILABILITY", "status": "LIMITATION", "severity": "CRITICAL", "evidence": "No observed project-level default/NPA target is present", "interpretation": "Accuracy, ROC-AUC, PD calibration and default/NPA prediction cannot be claimed.", "required_action": "Keep outputs framed as structural segmentation/stress decision support until real outcome data exist."},
        {"risk_id": "L06", "risk_type": "PROJECT_INVESTMENT_VS_BANK_EXPOSURE", "status": "PASS", "severity": "CRITICAL", "evidence": "financial_measure_crore is used only for structural rank/share; no EAD variable is in the frozen raw-feature contract", "interpretation": "Project investment/outlay is not bank exposure, EAD or realized loss.", "required_action": "Preserve this distinction everywhere."},
        {"risk_id": "L07", "risk_type": "POST_MODEL_OUTPUT_CIRCULARITY", "status": "PASS" if not outcome_hits else "FAIL", "severity": "CRITICAL", "evidence": "Raw feature names checked against downstream outcome tokens", "interpretation": "Cluster/stress/rating-like outputs must never feed the structural input matrix that generates them.", "required_action": "None" if not outcome_hits else "Rebuild contaminated model inputs."},
    ]
    leakage = pd.DataFrame(leakage_rows)
    leakage_failures = int((leakage["status"] == "FAIL").sum())
    leakage_limitations = int(leakage["status"].isin(["WARN", "LIMITATION"]).sum())
    add_check(checks, "LEAKAGE_HARD_FAILURES", "LEAKAGE", "HARD", status(leakage_failures == 0), leakage_failures, 0, "No conventional target/circularity/direct-identifier leakage hard failure may remain.")

    roles = {
        "manufacturing_canonical": "Verified manufacturing canonical source layer",
        "design_canonical": "Verified DLI design-project canonical source layer",
        "ecosystem_master": "Combined structural ecosystem master used for feature engineering",
        "feature_matrix": "Authoritative raw + standardized structural feature matrix",
        "feature_selection_audit": "Selected-feature contract evidence",
        "frozen_manifest": "Frozen model scope, feature and reference-hash contract",
        "pca_loadings": "Stored PCA loading evidence",
        "pca_variance": "Stored PCA explained-variance evidence",
        "validated_assignments": "Validated structural cluster assignment evidence",
    }
    lineage = pd.DataFrame([
        {"artifact_name": name, "file": str(path.relative_to(ROOT)), "role": roles.get(name, "Validation input"), "sha256": sha256_file(path), "bytes": int(path.stat().st_size), "audit_version": AUDIT_VERSION}
        for name, path in paths.items()
    ])

    audit = pd.DataFrame(checks)
    hard_failures = audit[(audit["severity"] == "HARD") & (audit["status"] == "FAIL")]
    declared_warnings = audit[audit["status"].isin(["WARN", "LIMITATION"])]
    overall = "FAIL_DATA_PROVENANCE_OR_LEAKAGE_AUDIT" if len(hard_failures) else ("PASS_WITH_DECLARED_SCOPE_LIMITATIONS" if leakage_limitations or len(declared_warnings) else "PASS_DATA_PROVENANCE_AND_LEAKAGE_AUDIT")

    atomic_write(audit, AUDIT_OUT)
    atomic_write(lineage, LINEAGE_OUT)
    atomic_write(coverage, COVERAGE_OUT)
    atomic_write(feature_audit, FEATURE_OUT)
    atomic_write(hash_df, HASH_OUT)
    atomic_write(leakage, LEAKAGE_OUT)

    summary = {
        "phase": "15B",
        "run_at": utc_now(),
        "status": overall,
        "audit_version": AUDIT_VERSION,
        "manufacturing_rows": int(len(mfg)),
        "design_rows": int(len(dli)),
        "ecosystem_rows": int(len(ecosystem)),
        "feature_matrix_rows": int(len(features)),
        "raw_features": int(len(raw_features)),
        "hard_failures": int(len(hard_failures)),
        "leakage_failures": leakage_failures,
        "declared_leakage_scope_limitations": leakage_limitations,
        "frozen_hashes_verified": int((hash_df["status"] == "PASS").sum()),
        "frozen_hashes_total": int(len(hash_df)),
        "raw_feature_reconstruction_pass": bool(raw_pass),
        "z_feature_reconstruction_pass": bool(z_pass),
        "guardrails": config.get("guardrails", {}),
        "outputs": [str(x.relative_to(ROOT)) for x in [AUDIT_OUT, LINEAGE_OUT, COVERAGE_OUT, FEATURE_OUT, HASH_OUT, LEAKAGE_OUT]],
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 15B - DATA PROVENANCE & LEAKAGE AUDIT")
    print("=" * 78)
    print(f"Manufacturing canonical rows       : {len(mfg)}")
    print(f"DLI design canonical rows          : {len(dli)}")
    print(f"Ecosystem rows                     : {len(ecosystem)}")
    print(f"Feature-matrix rows                : {len(features)}")
    print(f"Frozen raw features                : {len(raw_features)}")
    print(f"Hard audit failures                : {len(hard_failures)}")
    print(f"Leakage hard failures              : {leakage_failures}")
    print(f"Declared leakage/scope limitations : {leakage_limitations}")
    print(f"Frozen hashes verified             : {summary['frozen_hashes_verified']} / {summary['frozen_hashes_total']}")
    print(f"Raw feature reconstruction         : {'PASS' if raw_pass else 'FAIL'}")
    print(f"Z feature reconstruction           : {'PASS' if z_pass else 'FAIL'}")
    print(f"STATUS                              : {overall}")
    print()
    print(f"Audit report                        : {AUDIT_OUT.relative_to(ROOT)}")
    print(f"Leakage register                    : {LEAKAGE_OUT.relative_to(ROOT)}")
    print(f"Feature reconstruction              : {FEATURE_OUT.relative_to(ROOT)}")
    print(f"Hash verification                   : {HASH_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: this audit can validate lineage, frozen-feature reproducibility and leakage boundaries; it cannot create missing project-level default outcomes or turn structural clusters into credit ratings.")
    return 1 if len(hard_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
