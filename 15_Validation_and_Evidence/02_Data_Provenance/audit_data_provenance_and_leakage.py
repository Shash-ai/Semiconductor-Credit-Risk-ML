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


def add_check(
    rows: list[dict],
    check_id: str,
    category: str,
    severity: str,
    status: str,
    observed,
    expected,
    detail: str,
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "category": category,
            "severity": severity,
            "status": status,
            "observed": observed,
            "expected": expected,
            "detail": detail,
            "audit_version": AUDIT_VERSION,
        }
    )


def bool_status(condition: bool) -> str:
    return "PASS" if bool(condition) else "FAIL"


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def text_blob(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ["project_name", "technology", "application", "project_type"] if c in df.columns]
    out = pd.Series("", index=df.index, dtype=str)
    for col in cols:
        out = out + " " + df[col].fillna("").astype(str)
    return out.str.lower().str.replace(r"\s+", " ", regex=True)


def contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.str.contains(pattern, regex=True, case=False, na=False)


def build_raw_features(ecosystem: pd.DataFrame, raw_features: list[str]) -> pd.DataFrame:
    """Reproduce the exact Phase 13 frozen feature definitions from the ecosystem master."""
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
        raise RuntimeError(f"Ecosystem master missing feature-engineering columns: {missing}")

    financial = pd.to_numeric(df["financial_measure_crore"], errors="coerce")
    if financial.isna().any():
        ids = df.loc[financial.isna(), "ecosystem_id"].astype(str).tolist()
        raise RuntimeError(f"financial_measure_crore missing for ecosystem rows: {ids}")

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

    partner = df.get("technology_partner", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
    df["has_technology_partner"] = partner.ne("").astype(float)

    missing_contract = [c for c in raw_features if c not in df.columns]
    if missing_contract:
        raise RuntimeError(f"Configured raw feature contract cannot be generated: {missing_contract}")

    out = df[["ecosystem_id"] + raw_features].copy()
    for feature in raw_features:
        out[feature] = pd.to_numeric(out[feature], errors="coerce")
    return out


def compare_string_fields(left: pd.DataFrame, right: pd.DataFrame, key: str, fields: list[str]) -> tuple[int, list[str]]:
    merged = left.merge(right, on=key, how="inner", suffixes=("_source", "_ecosystem"))
    mismatches = []
    for field in fields:
        a = merged[f"{field}_source"].map(clean)
        b = merged[f"{field}_ecosystem"].map(clean)
        bad = merged.loc[a.ne(b), key].astype(str).tolist()
        mismatches.extend([f"{field}:{x}" for x in bad])
    return len(mismatches), mismatches


def coverage_row(dataset: str, df: pd.DataFrame, fields: list[str], affirmative_fields: dict[str, str] | None = None) -> dict:
    row = {"dataset": dataset, "rows": int(len(df))}
    affirmative_fields = affirmative_fields or {}
    for field in fields:
        if field not in df.columns:
            row[f"{field}_coverage_pct"] = 0.0
            continue
        populated = df[field].map(clean).ne("")
        row[f"{field}_coverage_pct"] = float(populated.mean() * 100.0) if len(df) else 0.0
    for field, affirmative in affirmative_fields.items():
        if field not in df.columns:
            row[f"{field}_affirmative_pct"] = 0.0
            continue
        good = df[field].astype(str).str.strip().str.upper().eq(str(affirmative).upper())
        row[f"{field}_affirmative_pct"] = float(good.mean() * 100.0) if len(df) else 0.0
    return row


def has_prohibited_token(name: str, tokens: list[str]) -> list[str]:
    lowered = name.lower()
    hits = []
    for token in tokens:
        t = token.lower()
        if t in lowered:
            hits.append(token)
    return hits


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("audit_version") != AUDIT_VERSION:
        raise RuntimeError(
            f"Audit config version mismatch: {config.get('audit_version')} != {AUDIT_VERSION}"
        )

    file_cfg = config["files"]
    paths = {name: ROOT / rel for name, rel in file_cfg.items()}
    missing_files = [str(path.relative_to(ROOT)) for path in paths.values() if not path.exists()]
    if missing_files:
        raise RuntimeError(f"Required Phase 15B input files are missing: {missing_files}")

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

    checks: list[dict] = []

    # ------------------------------------------------------------------
    # Dataset identity, schema and key integrity.
    # ------------------------------------------------------------------
    required_mfg = {
        "project_id", "company", "state", "project_type_standardized", "approval_date",
        "approval_year", "investment_crore", "source_document", "source_page", "source",
        "data_quality_flag",
    }
    required_dli = {
        "dli_project_id", "company", "project_outlay_crore", "source_document", "source_url",
        "source_type", "source_authority", "official_source_confirmed",
        "financial_support_confirmed", "data_quality_flag",
    }
    required_ecosystem = {
        "ecosystem_id", "source_project_id", "project_scope", "company", "state",
        "project_type_standardized", "financial_measure_crore", "source_document",
        "source_authority", "data_quality_flag",
    }

    for check_id, name, df, required in [
        ("SCHEMA_MFG", "manufacturing_canonical", mfg, required_mfg),
        ("SCHEMA_DLI", "design_canonical", dli, required_dli),
        ("SCHEMA_ECOSYSTEM", "ecosystem_master", ecosystem, required_ecosystem),
    ]:
        missing = sorted(required - set(df.columns))
        add_check(
            checks, check_id, "SCHEMA", "HARD", bool_status(not missing),
            ";".join(missing) if missing else "NONE", "NONE",
            f"Required schema check for {name}.",
        )

    for check_id, name, df, key in [
        ("KEY_MFG_UNIQUE", "manufacturing_canonical", mfg, "project_id"),
        ("KEY_DLI_UNIQUE", "design_canonical", dli, "dli_project_id"),
        ("KEY_ECOSYSTEM_UNIQUE", "ecosystem_master", ecosystem, "ecosystem_id"),
        ("KEY_FEATURE_UNIQUE", "feature_matrix", features, "ecosystem_id"),
    ]:
        duplicate_count = int(df[key].astype(str).duplicated().sum()) if key in df.columns else len(df)
        add_check(
            checks, check_id, "KEY_INTEGRITY", "HARD", bool_status(duplicate_count == 0),
            duplicate_count, 0, f"Duplicate key count for {name}.{key}.",
        )

    source_ids = set(mfg["project_id"].astype(str)) | set(dli["dli_project_id"].astype(str))
    ecosystem_source_ids = set(ecosystem["source_project_id"].astype(str))
    add_check(
        checks, "SOURCE_ID_SET_MATCH", "LINEAGE", "HARD",
        bool_status(source_ids == ecosystem_source_ids),
        len(source_ids.symmetric_difference(ecosystem_source_ids)), 0,
        "Canonical manufacturing + DLI source-project IDs must exactly match ecosystem source_project_id values.",
    )

    add_check(
        checks, "ROW_COUNT_COMPOSITION", "LINEAGE", "HARD",
        bool_status(len(mfg) + len(dli) == len(ecosystem)),
        len(ecosystem), len(mfg) + len(dli),
        "Ecosystem rows must equal manufacturing canonical rows plus DLI canonical rows.",
    )

    expected_reference_rows = int(manifest.get("reference_universe_rows", len(ecosystem)))
    add_check(
        checks, "FROZEN_REFERENCE_ROW_COUNT", "FROZEN_CONTRACT", "HARD",
        bool_status(len(ecosystem) == expected_reference_rows and len(features) == expected_reference_rows),
        f"ecosystem={len(ecosystem)};feature_matrix={len(features)}", expected_reference_rows,
        "Current ecosystem and authoritative feature matrix must retain the frozen reference-universe size.",
    )

    # ------------------------------------------------------------------
    # Canonical -> ecosystem value lineage.
    # ------------------------------------------------------------------
    eco_mfg = ecosystem[ecosystem["project_scope"].astype(str).eq("Manufacturing")].copy()
    eco_dli = ecosystem[ecosystem["project_scope"].astype(str).eq("Semiconductor Design")].copy()

    mfg_left = mfg.rename(columns={"project_id": "source_project_id"})
    mfg_string_mismatch_count, mfg_string_mismatches = compare_string_fields(
        mfg_left,
        eco_mfg,
        "source_project_id",
        ["company", "state", "project_type_standardized"],
    )
    add_check(
        checks, "MFG_STRING_LINEAGE", "LINEAGE", "HARD",
        bool_status(mfg_string_mismatch_count == 0), mfg_string_mismatch_count, 0,
        "Canonical manufacturing company/state/project type must reproduce ecosystem values. "
        + ("; ".join(mfg_string_mismatches[:20]) if mfg_string_mismatches else ""),
    )

    mfg_amount = mfg_left[["source_project_id", "investment_crore"]].merge(
        eco_mfg[["source_project_id", "financial_measure_crore"]], on="source_project_id", how="inner"
    )
    mfg_amount_diff = (
        numeric_series(mfg_amount["investment_crore"]) - numeric_series(mfg_amount["financial_measure_crore"])
    ).abs()
    mfg_amount_max = float(mfg_amount_diff.max()) if len(mfg_amount_diff) else np.nan
    mfg_amount_ok = bool(len(mfg_amount) == len(mfg) and mfg_amount_diff.fillna(np.inf).le(amount_tol).all())
    add_check(
        checks, "MFG_AMOUNT_LINEAGE", "LINEAGE", "HARD", bool_status(mfg_amount_ok),
        mfg_amount_max, f"<= {amount_tol}",
        "Manufacturing investment_crore must equal ecosystem financial_measure_crore for the same source project.",
    )

    dli_left = dli.rename(columns={"dli_project_id": "source_project_id"})
    dli_string_mismatch_count, dli_string_mismatches = compare_string_fields(
        dli_left,
        eco_dli,
        "source_project_id",
        ["company"],
    )
    add_check(
        checks, "DLI_STRING_LINEAGE", "LINEAGE", "HARD",
        bool_status(dli_string_mismatch_count == 0), dli_string_mismatch_count, 0,
        "DLI company identity must reproduce ecosystem values. "
        + ("; ".join(dli_string_mismatches[:20]) if dli_string_mismatches else ""),
    )

    dli_amount = dli_left[["source_project_id", "project_outlay_crore"]].merge(
        eco_dli[["source_project_id", "financial_measure_crore"]], on="source_project_id", how="inner"
    )
    dli_amount_diff = (
        numeric_series(dli_amount["project_outlay_crore"]) - numeric_series(dli_amount["financial_measure_crore"])
    ).abs()
    dli_amount_max = float(dli_amount_diff.max()) if len(dli_amount_diff) else np.nan
    dli_amount_ok = bool(len(dli_amount) == len(dli) and dli_amount_diff.fillna(np.inf).le(amount_tol).all())
    add_check(
        checks, "DLI_AMOUNT_LINEAGE", "LINEAGE", "HARD", bool_status(dli_amount_ok),
        dli_amount_max, f"<= {amount_tol}",
        "DLI project_outlay_crore must equal ecosystem financial_measure_crore for the same source project.",
    )

    # Approval-year/date consistency is checked only where both are actually reported.
    approval_date = pd.to_datetime(mfg["approval_date"], errors="coerce")
    approval_year = pd.to_numeric(mfg["approval_year"], errors="coerce")
    comparable = approval_date.notna() & approval_year.notna()
    approval_mismatch = int((approval_date[comparable].dt.year.astype(float) != approval_year[comparable]).sum())
    add_check(
        checks, "MFG_APPROVAL_DATE_YEAR", "TEMPORAL_PROVENANCE", "HARD",
        bool_status(approval_mismatch == 0), approval_mismatch, 0,
        "Manufacturing approval_year must equal the year component of approval_date where both are populated.",
    )

    financial_measure = pd.to_numeric(ecosystem["financial_measure_crore"], errors="coerce")
    invalid_financial = int((financial_measure.isna() | (financial_measure <= 0)).sum())
    add_check(
        checks, "ECOSYSTEM_FINANCIAL_MEASURE_POSITIVE", "DATA_QUALITY", "HARD",
        bool_status(invalid_financial == 0), invalid_financial, 0,
        "Every structural ecosystem row requires a positive financial_measure_crore for rank/share construction.",
    )

    # ------------------------------------------------------------------
    # Provenance coverage.
    # ------------------------------------------------------------------
    coverage_rows = [
        coverage_row(
            "manufacturing_canonical",
            mfg,
            ["source_document", "source_page", "source", "data_quality_flag"],
        ),
        coverage_row(
            "design_canonical",
            dli,
            ["source_document", "source_url", "source_type", "source_authority", "data_quality_flag"],
            {"official_source_confirmed": "YES", "financial_support_confirmed": "YES"},
        ),
        coverage_row(
            "ecosystem_master",
            ecosystem,
            ["source_project_id", "source_document", "source_authority", "data_quality_flag", "financial_measure_crore"],
        ),
    ]
    coverage = pd.DataFrame(coverage_rows)

    # Hard provenance minimums: authority/document/data-quality identity must not be absent.
    mfg_core_provenance = (
        mfg["source_document"].map(clean).ne("")
        & mfg["source"].map(clean).ne("")
        & mfg["data_quality_flag"].map(clean).ne("")
    )
    dli_core_provenance = (
        dli["source_document"].map(clean).ne("")
        & dli["source_url"].map(clean).ne("")
        & dli["source_authority"].map(clean).ne("")
        & dli["data_quality_flag"].map(clean).ne("")
    )
    eco_core_provenance = (
        ecosystem["source_project_id"].map(clean).ne("")
        & ecosystem["source_document"].map(clean).ne("")
        & ecosystem["source_authority"].map(clean).ne("")
        & ecosystem["data_quality_flag"].map(clean).ne("")
    )
    for cid, label, mask in [
        ("MFG_CORE_PROVENANCE", "manufacturing canonical", mfg_core_provenance),
        ("DLI_CORE_PROVENANCE", "DLI canonical", dli_core_provenance),
        ("ECOSYSTEM_CORE_PROVENANCE", "ecosystem master", eco_core_provenance),
    ]:
        missing_count = int((~mask).sum())
        add_check(
            checks, cid, "PROVENANCE", "HARD", bool_status(missing_count == 0),
            missing_count, 0, f"Rows missing minimum source identity/provenance in {label}.",
        )

    dli_unconfirmed_official = int(~dli["official_source_confirmed"].astype(str).str.upper().eq("YES")).sum()
    dli_unconfirmed_support = int(~dli["financial_support_confirmed"].astype(str).str.upper().eq("YES")).sum()
    add_check(
        checks, "DLI_OFFICIAL_SOURCE_CONFIRMED", "PROVENANCE", "HARD",
        bool_status(dli_unconfirmed_official == 0), dli_unconfirmed_official, 0,
        "DLI rows included in the canonical ecosystem must be explicitly marked official-source-confirmed.",
    )
    add_check(
        checks, "DLI_FINANCIAL_SUPPORT_CONFIRMED", "PROVENANCE", "HARD",
        bool_status(dli_unconfirmed_support == 0), dli_unconfirmed_support, 0,
        "DLI financial-support evidence status must remain explicit for all included rows.",
    )

    # Exact DLI approval timing is intentionally not imputed.
    dli_year_missing = int(dli.get("approval_year", pd.Series(index=dli.index, dtype=object)).map(clean).eq("").sum())
    dli_date_missing = int(dli.get("approval_date", pd.Series(index=dli.index, dtype=object)).map(clean).eq("").sum())
    dli_temporal_status = "WARN" if dli_year_missing or dli_date_missing else "PASS"
    add_check(
        checks, "DLI_EXACT_APPROVAL_TIMING", "TEMPORAL_PROVENANCE", "SOFT", dli_temporal_status,
        f"missing_year={dli_year_missing};missing_date={dli_date_missing}", "Exact approval timing where publicly verified",
        "Missing DLI approval timing is preserved as missing. This prevents historical point-in-time claims that the evidence cannot support.",
    )

    # ------------------------------------------------------------------
    # Feature contract, exact reconstruction and standardization.
    # ------------------------------------------------------------------
    feature_ids = set(features["ecosystem_id"].astype(str))
    ecosystem_ids = set(ecosystem["ecosystem_id"].astype(str))
    add_check(
        checks, "FEATURE_ID_SET_MATCH", "FEATURE_CONTRACT", "HARD",
        bool_status(feature_ids == ecosystem_ids), len(feature_ids.symmetric_difference(ecosystem_ids)), 0,
        "Authoritative feature matrix ecosystem IDs must exactly match the ecosystem master.",
    )

    missing_feature_cols = [c for c in raw_features + z_features if c not in features.columns]
    add_check(
        checks, "FEATURE_COLUMNS_PRESENT", "FEATURE_CONTRACT", "HARD",
        bool_status(not missing_feature_cols), ";".join(missing_feature_cols) if missing_feature_cols else "NONE", "NONE",
        "All frozen raw and standardized feature columns must exist in the authoritative feature matrix.",
    )

    selected = set(
        feature_selection.loc[
            feature_selection["status"].astype(str).str.upper().eq("SELECTED"), "feature"
        ].astype(str)
    )
    add_check(
        checks, "FEATURE_SELECTION_CONTRACT_MATCH", "FEATURE_CONTRACT", "HARD",
        bool_status(selected == set(raw_features)),
        ";".join(sorted(selected.symmetric_difference(set(raw_features)))) if selected != set(raw_features) else "NONE",
        "NONE",
        "Selected feature-audit set must exactly equal the frozen manifest raw-feature contract.",
    )

    regenerated = build_raw_features(ecosystem, raw_features)
    feature_compare = regenerated.merge(
        features[["ecosystem_id"] + raw_features], on="ecosystem_id", how="inner", suffixes=("_calc", "_stored")
    )
    feature_audit_rows = []
    raw_feature_pass = True
    for feature in raw_features:
        calc = pd.to_numeric(feature_compare[f"{feature}_calc"], errors="coerce")
        stored = pd.to_numeric(feature_compare[f"{feature}_stored"], errors="coerce")
        diff = (calc - stored).abs()
        max_err = float(diff.max()) if len(diff) else np.inf
        passed = bool(max_err <= raw_tol and not diff.isna().any())
        raw_feature_pass = raw_feature_pass and passed
        feature_audit_rows.append(
            {
                "feature": feature,
                "layer": "RAW",
                "max_abs_error": max_err,
                "tolerance": raw_tol,
                "status": "PASS" if passed else "FAIL",
                "definition_source": "Phase 13 frozen feature engineering contract",
            }
        )

    add_check(
        checks, "RAW_FEATURE_RECONSTRUCTION", "FEATURE_REPRODUCTION", "HARD",
        bool_status(raw_feature_pass),
        max([x["max_abs_error"] for x in feature_audit_rows if x["layer"] == "RAW"], default=np.nan),
        f"<= {raw_tol}",
        "Re-derived structural raw features must reproduce the authoritative historical feature matrix.",
    )

    raw_ref = features.set_index("ecosystem_id")[raw_features].astype(float)
    means = raw_ref.mean(axis=0)
    scales = raw_ref.std(axis=0, ddof=0)
    zero_var = scales[scales <= 0].index.tolist()
    add_check(
        checks, "NO_ZERO_VARIANCE_RAW_FEATURES", "FEATURE_REPRODUCTION", "HARD",
        bool_status(not zero_var), ";".join(zero_var) if zero_var else "NONE", "NONE",
        "Frozen standardized features require non-zero reference standard deviations.",
    )

    z_feature_pass = False
    if not zero_var:
        z_calc = (raw_ref - means) / scales
        z_stored = features.set_index("ecosystem_id")[z_features].astype(float).copy()
        z_stored.columns = raw_features
        z_feature_pass = True
        for feature in raw_features:
            diff = (z_calc[feature] - z_stored[feature]).abs()
            max_err = float(diff.max()) if len(diff) else np.inf
            passed = bool(max_err <= z_tol and not diff.isna().any())
            z_feature_pass = z_feature_pass and passed
            feature_audit_rows.append(
                {
                    "feature": feature,
                    "layer": "STANDARDIZED_Z",
                    "max_abs_error": max_err,
                    "tolerance": z_tol,
                    "status": "PASS" if passed else "FAIL",
                    "definition_source": "ddof=0 reference mean/std reconstruction",
                }
            )

    add_check(
        checks, "Z_FEATURE_RECONSTRUCTION", "FEATURE_REPRODUCTION", "HARD",
        bool_status(z_feature_pass),
        max([x["max_abs_error"] for x in feature_audit_rows if x["layer"] == "STANDARDIZED_Z"], default=np.nan),
        f"<= {z_tol}",
        "Stored standardized features must reconstruct exactly from the authoritative raw feature matrix using ddof=0 scaling.",
    )

    feature_audit = pd.DataFrame(feature_audit_rows)

    # ------------------------------------------------------------------
    # Frozen artifact hash contract.
    # ------------------------------------------------------------------
    expected_hashes = manifest.get("reference_hashes", {})
    hash_mapping = {
        "baseline_ecosystem_sha256": paths["ecosystem_master"],
        "authoritative_feature_matrix_sha256": paths["feature_matrix"],
        "pca_loadings_sha256": paths["pca_loadings"],
        "validated_assignments_sha256": paths["validated_assignments"],
        "pca_variance_sha256": paths["pca_variance"],
    }
    hash_rows = []
    all_hashes_pass = True
    for key, path in hash_mapping.items():
        expected = clean(expected_hashes.get(key))
        observed = sha256_file(path)
        passed = bool(expected and observed == expected)
        all_hashes_pass = all_hashes_pass and passed
        hash_rows.append(
            {
                "hash_contract_key": key,
                "file": str(path.relative_to(ROOT)),
                "expected_sha256": expected,
                "observed_sha256": observed,
                "status": "PASS" if passed else "FAIL",
            }
        )
    hash_df = pd.DataFrame(hash_rows)
    add_check(
        checks, "FROZEN_HASH_CONTRACT", "FROZEN_CONTRACT", "HARD",
        bool_status(all_hashes_pass), int((hash_df["status"] != "PASS").sum()), 0,
        "Frozen reference files must match the SHA-256 values recorded when the structural model was frozen.",
    )

    # ------------------------------------------------------------------
    # Leakage and scope-boundary audit.
    # ------------------------------------------------------------------
    leakage_rows: list[dict] = []
    prohibited = [str(x) for x in config.get("prohibited_outcome_tokens", [])]
    outcome_hits = {}
    for feature in raw_features:
        hits = has_prohibited_token(feature, prohibited)
        if hits:
            outcome_hits[feature] = hits

    leakage_rows.append(
        {
            "risk_id": "L01",
            "risk_type": "CONVENTIONAL_TARGET_LEAKAGE",
            "status": "PASS" if not outcome_hits else "FAIL",
            "severity": "CRITICAL",
            "evidence": json.dumps(outcome_hits, ensure_ascii=False),
            "interpretation": "The model is unsupervised and the raw feature contract must not contain downstream default/rating/stress/cluster outcomes.",
            "required_action": "None" if not outcome_hits else "Remove contaminated feature(s) and revalidate the frozen model.",
        }
    )

    identifier_features = {"ecosystem_id", "source_project_id", "company", "state"} & set(raw_features)
    leakage_rows.append(
        {
            "risk_id": "L02",
            "risk_type": "DIRECT_IDENTIFIER_LEAKAGE",
            "status": "PASS" if not identifier_features else "FAIL",
            "severity": "HIGH",
            "evidence": ";".join(sorted(identifier_features)) if identifier_features else "No direct row/company/state identifiers in raw feature contract",
            "interpretation": "Identifiers should not act as memorization features. Structural aggregates such as company_project_count/state share are treated separately.",
            "required_action": "None" if not identifier_features else "Remove direct identifiers from model inputs.",
        }
    )

    cohort_features = [x for x in config.get("cohort_relative_features", []) if x in raw_features]
    leakage_rows.append(
        {
            "risk_id": "L03",
            "risk_type": "COHORT_RELATIVE_TRANSDUCTIVE_DEPENDENCE",
            "status": "WARN" if cohort_features else "PASS",
            "severity": "MEDIUM",
            "evidence": ";".join(cohort_features),
            "interpretation": "Rank, state-share and project-count features depend on the contemporaneous ecosystem universe. This is valid for current-snapshot structural segmentation but means adding a project can change cohort-relative values.",
            "required_action": "Retain as declared design choice; test pseudo-new-project/leave-one-out stability in Phase 15H.",
        }
    )

    mfg_years = pd.to_numeric(mfg["approval_year"], errors="coerce").dropna()
    temporal_range = (
        f"manufacturing approval years {int(mfg_years.min())}-{int(mfg_years.max())}"
        if len(mfg_years)
        else "manufacturing approval year unavailable"
    )
    leakage_rows.append(
        {
            "risk_id": "L04",
            "risk_type": "HISTORICAL_POINT_IN_TIME_SCOPE",
            "status": "WARN",
            "severity": "HIGH",
            "evidence": temporal_range + f"; DLI missing exact year rows={dli_year_missing}",
            "interpretation": "The frozen 36-row model is a cross-sectional ecosystem snapshot, not a historical as-of-each-approval-date backtest. Later-known cohort composition must not be used to claim historical prediction performance.",
            "required_action": "Do not make historical predictive claims; if needed, construct rolling point-in-time cohorts as a separate validation experiment.",
        }
    )

    leakage_rows.append(
        {
            "risk_id": "L05",
            "risk_type": "OBSERVED_DEFAULT_TARGET_AVAILABILITY",
            "status": "LIMITATION",
            "severity": "CRITICAL",
            "evidence": "No observed project-level default/NPA outcome target in the structural project dataset",
            "interpretation": "Accuracy, ROC-AUC, PD calibration, default prediction and NPA prediction cannot be claimed from this dataset.",
            "required_action": "Frame outputs as structural segmentation/stress decision support; future bank outcome data would be needed for supervised credit validation.",
        }
    )

    leakage_rows.append(
        {
            "risk_id": "L06",
            "risk_type": "PROJECT_INVESTMENT_VS_BANK_EXPOSURE",
            "status": "PASS",
            "severity": "CRITICAL",
            "evidence": "financial_measure_crore feeds structural rank/share; no EAD field is used in the structural feature contract",
            "interpretation": "Project investment/outlay is a structural scale variable and is not represented as bank exposure, EAD or realized credit loss.",
            "required_action": "Preserve this distinction in the paper, dashboard and all new-project assessments.",
        }
    )

    leakage_rows.append(
        {
            "risk_id": "L07",
            "risk_type": "POST_MODEL_OUTPUT_CIRCULARITY",
            "status": "PASS" if not outcome_hits else "FAIL",
            "severity": "CRITICAL",
            "evidence": "Frozen raw-feature list inspected against downstream outcome tokens",
            "interpretation": "Structural cluster/stress/rating-like outputs must never feed back into the clustering input matrix used to generate them.",
            "required_action": "None" if not outcome_hits else "Rebuild the contaminated feature contract.",
        }
    )

    leakage = pd.DataFrame(leakage_rows)
    leakage_failures = int((leakage["status"] == "FAIL").sum())
    leakage_warnings = int(leakage["status"].isin(["WARN", "LIMITATION"]).sum())
    add_check(
        checks, "LEAKAGE_HARD_FAILURES", "LEAKAGE", "HARD",
        bool_status(leakage_failures == 0), leakage_failures, 0,
        "No hard conventional leakage/circularity/identifier failure may remain in the frozen structural feature contract.",
    )

    # ------------------------------------------------------------------
    # Data lineage register with current file hashes.
    # ------------------------------------------------------------------
    lineage_roles = {
        "manufacturing_canonical": "Verified manufacturing project canonical source layer",
        "design_canonical": "Verified DLI design-project canonical source layer",
        "ecosystem_master": "Combined 36-row structural ecosystem master used for feature engineering",
        "feature_matrix": "Authoritative raw + standardized structural model feature matrix",
        "feature_selection_audit": "Explicit selected-feature contract evidence",
        "frozen_manifest": "Frozen structural model scope, feature and hash contract",
        "pca_loadings": "Stored PCA loading evidence used by the frozen model",
        "pca_variance": "Stored PCA explained-variance evidence",
        "validated_assignments": "Validated structural cluster assignment evidence",
    }
    lineage_rows = []
    for name, path in paths.items():
        lineage_rows.append(
            {
                "artifact_name": name,
                "file": str(path.relative_to(ROOT)),
                "role": lineage_roles.get(name, "Validation input"),
                "sha256": sha256_file(path),
                "bytes": int(path.stat().st_size),
                "audit_version": AUDIT_VERSION,
            }
        )
    lineage = pd.DataFrame(lineage_rows)

    audit = pd.DataFrame(checks)
    hard_failures = audit[(audit["severity"] == "HARD") & (audit["status"] == "FAIL")]
    soft_warnings = audit[audit["status"].isin(["WARN", "LIMITATION"])]

    if len(hard_failures):
        overall_status = "FAIL_DATA_PROVENANCE_OR_LEAKAGE_AUDIT"
    elif leakage_warnings or len(soft_warnings):
        overall_status = "PASS_WITH_DECLARED_SCOPE_LIMITATIONS"
    else:
        overall_status = "PASS_DATA_PROVENANCE_AND_LEAKAGE_AUDIT"

    atomic_write(audit, AUDIT_OUT)
    atomic_write(lineage, LINEAGE_OUT)
    atomic_write(coverage, COVERAGE_OUT)
    atomic_write(feature_audit, FEATURE_OUT)
    atomic_write(hash_df, HASH_OUT)
    atomic_write(leakage, LEAKAGE_OUT)

    summary = {
        "phase": "15B",
        "run_at": utc_now(),
        "status": overall_status,
        "audit_version": AUDIT_VERSION,
        "manufacturing_rows": int(len(mfg)),
        "design_rows": int(len(dli)),
        "ecosystem_rows": int(len(ecosystem)),
        "feature_matrix_rows": int(len(features)),
        "raw_features": int(len(raw_features)),
        "hard_failures": int(len(hard_failures)),
        "soft_scope_warnings": int(len(soft_warnings)),
        "leakage_failures": leakage_failures,
        "leakage_warnings_or_limitations": leakage_warnings,
        "frozen_hashes_verified": int((hash_df["status"] == "PASS").sum()),
        "frozen_hashes_total": int(len(hash_df)),
        "raw_feature_reconstruction_pass": bool(raw_feature_pass),
        "z_feature_reconstruction_pass": bool(z_feature_pass),
        "guardrails": config.get("guardrails", {}),
        "outputs": [
            str(AUDIT_OUT.relative_to(ROOT)),
            str(LINEAGE_OUT.relative_to(ROOT)),
            str(COVERAGE_OUT.relative_to(ROOT)),
            str(FEATURE_OUT.relative_to(ROOT)),
            str(HASH_OUT.relative_to(ROOT)),
            str(LEAKAGE_OUT.relative_to(ROOT)),
        ],
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
    print(f"Declared leakage/scope limitations : {leakage_warnings}")
    print(f"Frozen hashes verified             : {summary['frozen_hashes_verified']} / {summary['frozen_hashes_total']}")
    print(f"Raw feature reconstruction         : {'PASS' if raw_feature_pass else 'FAIL'}")
    print(f"Z feature reconstruction           : {'PASS' if z_feature_pass else 'FAIL'}")
    print(f"STATUS                              : {overall_status}")
    print()
    print(f"Audit report                        : {AUDIT_OUT.relative_to(ROOT)}")
    print(f"Leakage register                    : {LEAKAGE_OUT.relative_to(ROOT)}")
    print(f"Feature reconstruction              : {FEATURE_OUT.relative_to(ROOT)}")
    print(f"Hash verification                   : {HASH_OUT.relative_to(ROOT)}")
    print()
    print("Interpretation guardrail: this audit can validate lineage, reproducibility and leakage boundaries; it cannot create missing project-level default outcomes or convert structural clusters into credit ratings.")

    return 1 if len(hard_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
