from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
STRUCTURED_FILE = ROOT / "13_Continuous_Ingestion" / "04_Verification" / "Structured_Project_Candidates.csv"
CANONICAL_FILE = ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "05_Canonicalization"
REVIEW_FILE = OUT_DIR / "Canonicalization_Review.csv"
STAGING_FILE = OUT_DIR / "Canonical_Staging.csv"
CONFLICT_FILE = OUT_DIR / "Canonicalization_Conflicts.csv"
AUDIT_FILE = OUT_DIR / "Canonicalization_Run_Log.jsonl"
BACKUP_DIR = OUT_DIR / "backups"

APPLY_CONFIRMATION = "APPLY_REVIEWED_CANONICAL_ROWS"

CANONICAL_COLUMNS = [
    "project_id",
    "company",
    "project_type",
    "project_group",
    "state",
    "approval_date",
    "approval_year",
    "investment_crore",
    "investment_category",
    "capacity_value",
    "capacity_unit",
    "capacity_category",
    "technology",
    "technology_partner",
    "source_document",
    "source_page",
    "source",
    "data_quality_flag",
    "project_type_standardized",
    "state_verified",
]

REVIEW_COLUMNS = [
    "review_id",
    "discovery_id",
    "source_title",
    "source_url",
    "verification_decision",
    "extracted_company",
    "extracted_state",
    "extracted_project_type",
    "extracted_investment_crore",
    "review_decision",
    "confirmed_company",
    "confirmed_state",
    "confirmed_project_type",
    "confirmed_project_type_standardized",
    "confirmed_project_group",
    "confirmed_approval_date",
    "confirmed_investment_crore",
    "confirmed_investment_category",
    "confirmed_capacity_value",
    "confirmed_capacity_unit",
    "confirmed_capacity_category",
    "confirmed_technology",
    "confirmed_technology_partner",
    "confirmed_source_document",
    "confirmed_source_page",
    "confirmed_source_name",
    "confirmed_data_quality_flag",
    "confirmed_state_verified",
    "reviewer_notes",
    "reviewed_by",
    "reviewed_at",
]

STAGING_COLUMNS = [
    "review_id",
    "discovery_id",
] + CANONICAL_COLUMNS + [
    "canonicalization_status",
    "source_url",
    "reviewed_by",
    "reviewed_at",
    "reviewer_notes",
]

CONFLICT_COLUMNS = [
    "review_id",
    "discovery_id",
    "conflict_type",
    "conflict_detail",
    "matched_project_id",
    "matched_company",
    "resolution_status",
]

ALLOWED_REVIEW_DECISIONS = {
    "PENDING",
    "APPROVE_NEW_PROJECT",
    "REJECT_NOT_NEW_PROJECT",
    "HOLD_MANUAL_REVIEW",
}

REQUIRED_FOR_APPROVAL = [
    "confirmed_company",
    "confirmed_state",
    "confirmed_project_type",
    "confirmed_project_type_standardized",
    "confirmed_project_group",
    "confirmed_approval_date",
    "confirmed_investment_crore",
    "confirmed_investment_category",
    "confirmed_source_document",
    "confirmed_source_name",
    "confirmed_data_quality_flag",
    "confirmed_state_verified",
    "reviewed_by",
    "reviewed_at",
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


def norm(value) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_bool(value):
    text = clean(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def safe_float(value):
    text = clean(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns or [])
    if columns:
        for col in columns:
            if col not in df.columns:
                df[col] = pd.NA
        return df[columns]
    return df


def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp, index=False)
    temp.replace(path)


def append_audit(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def make_review_id(discovery_id: str, sequence: int = 1) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "", clean(discovery_id)) or "UNKNOWN"
    return f"REV-{safe}-{sequence:02d}"


def sync_review_template(structured: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    review = read_csv(REVIEW_FILE, REVIEW_COLUMNS)
    existing_discovery_ids = set(review["discovery_id"].astype(str).map(clean)) if not review.empty else set()
    additions = []

    for _, row in structured.iterrows():
        discovery_id = clean(row.get("discovery_id"))
        if not discovery_id or discovery_id in existing_discovery_ids:
            continue

        additions.append({
            "review_id": make_review_id(discovery_id),
            "discovery_id": discovery_id,
            "source_title": clean(row.get("title")),
            "source_url": clean(row.get("url")),
            "verification_decision": clean(row.get("verification_decision")),
            "extracted_company": clean(row.get("proposed_company")),
            "extracted_state": clean(row.get("proposed_state")),
            "extracted_project_type": clean(row.get("proposed_project_type")),
            "extracted_investment_crore": row.get("proposed_investment_crore"),
            "review_decision": "PENDING",
            "confirmed_company": "",
            "confirmed_state": "",
            "confirmed_project_type": "",
            "confirmed_project_type_standardized": "",
            "confirmed_project_group": "",
            "confirmed_approval_date": "",
            "confirmed_investment_crore": "",
            "confirmed_investment_category": "",
            "confirmed_capacity_value": "",
            "confirmed_capacity_unit": "",
            "confirmed_capacity_category": "",
            "confirmed_technology": "",
            "confirmed_technology_partner": "",
            "confirmed_source_document": "",
            "confirmed_source_page": "",
            "confirmed_source_name": "",
            "confirmed_data_quality_flag": "",
            "confirmed_state_verified": "",
            "reviewer_notes": "",
            "reviewed_by": "",
            "reviewed_at": "",
        })

    if additions:
        review = pd.concat([review, pd.DataFrame(additions)], ignore_index=True)
        review = review[REVIEW_COLUMNS]
        write_csv_atomic(review, REVIEW_FILE)
    elif not REVIEW_FILE.exists():
        write_csv_atomic(review, REVIEW_FILE)

    return review, len(additions)


def next_project_ids(canonical: pd.DataFrame, count: int) -> list[str]:
    nums = []
    if not canonical.empty and "project_id" in canonical.columns:
        for value in canonical["project_id"].astype(str):
            match = re.fullmatch(r"SEM-(\d+)", value.strip())
            if match:
                nums.append(int(match.group(1)))
    start = (max(nums) if nums else 0) + 1
    return [f"SEM-{i:04d}" for i in range(start, start + count)]


def validate_review_row(row: pd.Series, canonical: pd.DataFrame) -> list[str]:
    errors = []
    decision = clean(row.get("review_decision")).upper() or "PENDING"
    if decision not in ALLOWED_REVIEW_DECISIONS:
        errors.append(f"INVALID_REVIEW_DECISION:{decision}")
        return errors
    if decision != "APPROVE_NEW_PROJECT":
        return errors

    for field in REQUIRED_FOR_APPROVAL:
        if not clean(row.get(field)):
            errors.append(f"MISSING_REQUIRED_FIELD:{field}")

    investment = safe_float(row.get("confirmed_investment_crore"))
    if investment is None or investment <= 0:
        errors.append("INVALID_CONFIRMED_INVESTMENT_CRORE")

    try:
        approval_date = pd.to_datetime(clean(row.get("confirmed_approval_date")), format="%Y-%m-%d", errors="raise")
        if approval_date.year < 2000 or approval_date.year > 2100:
            errors.append("APPROVAL_DATE_OUT_OF_RANGE")
    except Exception:
        errors.append("INVALID_APPROVAL_DATE_USE_YYYY-MM-DD")

    state_verified = parse_bool(row.get("confirmed_state_verified"))
    if state_verified is not True:
        errors.append("STATE_MUST_BE_EXPLICITLY_VERIFIED_TRUE")

    if clean(row.get("confirmed_data_quality_flag")).upper() != "OK":
        errors.append("DATA_QUALITY_FLAG_MUST_BE_OK_FOR_APPROVAL")

    if not canonical.empty:
        allowed_standardized = {clean(x) for x in canonical.get("project_type_standardized", pd.Series(dtype=str)).dropna() if clean(x)}
        proposed_standardized = clean(row.get("confirmed_project_type_standardized"))
        if allowed_standardized and proposed_standardized not in allowed_standardized:
            errors.append("UNRECOGNIZED_PROJECT_TYPE_STANDARDIZED_REVIEW_REQUIRED")

        allowed_groups = {clean(x) for x in canonical.get("project_group", pd.Series(dtype=str)).dropna() if clean(x)}
        proposed_group = clean(row.get("confirmed_project_group"))
        if allowed_groups and proposed_group not in allowed_groups:
            errors.append("UNRECOGNIZED_PROJECT_GROUP_REVIEW_REQUIRED")

    return errors


def duplicate_conflicts(row: pd.Series, canonical: pd.DataFrame) -> list[dict]:
    if canonical.empty:
        return []

    company = clean(row.get("confirmed_company"))
    state = clean(row.get("confirmed_state"))
    project_type_std = clean(row.get("confirmed_project_type_standardized"))
    investment = safe_float(row.get("confirmed_investment_crore"))
    company_norm = norm(company)
    state_norm = norm(state)
    type_norm = norm(project_type_std)

    conflicts = []
    for _, existing in canonical.iterrows():
        ex_company = clean(existing.get("company"))
        ex_state = clean(existing.get("state"))
        ex_type = clean(existing.get("project_type_standardized"))
        ex_investment = safe_float(existing.get("investment_crore"))

        similarity = SequenceMatcher(None, company_norm, norm(ex_company)).ratio() if company_norm and ex_company else 0.0
        same_state = state_norm and state_norm == norm(ex_state)
        same_type = type_norm and type_norm == norm(ex_type)
        close_investment = False
        if investment is not None and ex_investment not in (None, 0):
            close_investment = abs(investment - ex_investment) / max(abs(ex_investment), 1.0) <= 0.05

        exact_key = similarity >= 0.98 and same_state and same_type
        strong_duplicate = similarity >= 0.90 and same_state and (same_type or close_investment)

        if exact_key or strong_duplicate:
            conflicts.append({
                "review_id": clean(row.get("review_id")),
                "discovery_id": clean(row.get("discovery_id")),
                "conflict_type": "POSSIBLE_CANONICAL_DUPLICATE",
                "conflict_detail": (
                    f"company_similarity={similarity:.3f};same_state={same_state};"
                    f"same_type={same_type};close_investment_5pct={close_investment}"
                ),
                "matched_project_id": clean(existing.get("project_id")),
                "matched_company": ex_company,
                "resolution_status": "BLOCKED_PENDING_MANUAL_RESOLUTION",
            })

    return conflicts


def build_canonical_row(review: pd.Series, project_id: str) -> dict:
    approval_date = pd.to_datetime(clean(review.get("confirmed_approval_date")), format="%Y-%m-%d")
    capacity_value = safe_float(review.get("confirmed_capacity_value"))

    return {
        "project_id": project_id,
        "company": clean(review.get("confirmed_company")),
        "project_type": clean(review.get("confirmed_project_type")),
        "project_group": clean(review.get("confirmed_project_group")),
        "state": clean(review.get("confirmed_state")),
        "approval_date": approval_date.strftime("%Y-%m-%d"),
        "approval_year": int(approval_date.year),
        "investment_crore": safe_float(review.get("confirmed_investment_crore")),
        "investment_category": clean(review.get("confirmed_investment_category")),
        "capacity_value": capacity_value if capacity_value is not None else pd.NA,
        "capacity_unit": clean(review.get("confirmed_capacity_unit")),
        "capacity_category": clean(review.get("confirmed_capacity_category")),
        "technology": clean(review.get("confirmed_technology")),
        "technology_partner": clean(review.get("confirmed_technology_partner")),
        "source_document": clean(review.get("confirmed_source_document")),
        "source_page": clean(review.get("confirmed_source_page")) or "WEB",
        "source": clean(review.get("confirmed_source_name")),
        "data_quality_flag": clean(review.get("confirmed_data_quality_flag")).upper(),
        "project_type_standardized": clean(review.get("confirmed_project_type_standardized")),
        "state_verified": True,
    }


def stage_rows(review: pd.DataFrame, canonical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    approved = review[review["review_decision"].astype(str).str.upper().eq("APPROVE_NEW_PROJECT")].copy()
    valid_records = []
    conflicts = []
    validation_errors = []

    for _, row in approved.iterrows():
        errors = validate_review_row(row, canonical)
        if errors:
            validation_errors.append(f"{clean(row.get('review_id'))}:" + "|".join(errors))
            conflicts.append({
                "review_id": clean(row.get("review_id")),
                "discovery_id": clean(row.get("discovery_id")),
                "conflict_type": "VALIDATION_ERROR",
                "conflict_detail": "|".join(errors),
                "matched_project_id": "",
                "matched_company": "",
                "resolution_status": "BLOCKED_PENDING_CORRECTION",
            })
            continue

        dupes = duplicate_conflicts(row, canonical)
        if dupes:
            conflicts.extend(dupes)
            continue

        valid_records.append(row)

    ids = next_project_ids(canonical, len(valid_records))
    staged_rows = []
    for row, project_id in zip(valid_records, ids):
        canonical_row = build_canonical_row(row, project_id)
        staged_rows.append({
            "review_id": clean(row.get("review_id")),
            "discovery_id": clean(row.get("discovery_id")),
            **canonical_row,
            "canonicalization_status": "STAGED_NOT_APPLIED",
            "source_url": clean(row.get("source_url")),
            "reviewed_by": clean(row.get("reviewed_by")),
            "reviewed_at": clean(row.get("reviewed_at")),
            "reviewer_notes": clean(row.get("reviewer_notes")),
        })

    staging = pd.DataFrame(staged_rows, columns=STAGING_COLUMNS)
    conflict_df = pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS)
    return staging, conflict_df, validation_errors


def apply_staging(staging: pd.DataFrame, canonical: pd.DataFrame, confirmation: str) -> tuple[pd.DataFrame, Path | None]:
    if confirmation != APPLY_CONFIRMATION:
        raise RuntimeError(
            "Apply mode requires --confirmation APPLY_REVIEWED_CANONICAL_ROWS. "
            "No canonical data was changed."
        )

    if staging.empty:
        return canonical, None

    existing_ids = set(canonical.get("project_id", pd.Series(dtype=str)).astype(str))
    if any(str(pid) in existing_ids for pid in staging["project_id"]):
        raise RuntimeError("Staged project_id collision detected. Re-stage before applying.")

    new_rows = staging[CANONICAL_COLUMNS].copy()
    combined = pd.concat([canonical[CANONICAL_COLUMNS], new_rows], ignore_index=True)

    if combined["project_id"].astype(str).duplicated().any():
        raise RuntimeError("Duplicate project_id detected after merge. Apply aborted.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"Semiconductor_Master_Canonical_before_{stamp}.csv"
    if CANONICAL_FILE.exists():
        shutil.copy2(CANONICAL_FILE, backup_path)

    write_csv_atomic(combined, CANONICAL_FILE)
    return combined, backup_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 13D controlled canonicalization")
    parser.add_argument("--apply", action="store_true", help="Apply staged reviewed rows to canonical master")
    parser.add_argument("--confirmation", default="", help="Required explicit confirmation token for --apply")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    structured = read_csv(STRUCTURED_FILE)
    canonical = read_csv(CANONICAL_FILE, CANONICAL_COLUMNS)

    review, added = sync_review_template(structured)

    staging, conflicts, validation_errors = stage_rows(review, canonical)
    write_csv_atomic(staging, STAGING_FILE)
    write_csv_atomic(conflicts, CONFLICT_FILE)

    applied_count = 0
    backup_path = None
    final_canonical_count = len(canonical)

    if args.apply:
        combined, backup_path = apply_staging(staging, canonical, args.confirmation)
        applied_count = len(staging)
        final_canonical_count = len(combined)
        if not staging.empty:
            staging = staging.copy()
            staging["canonicalization_status"] = "APPLIED_TO_CANONICAL_MASTER"
            write_csv_atomic(staging, STAGING_FILE)

    summary = {
        "run_at": utc_now(),
        "phase": "13D",
        "mode": "APPLY" if args.apply else "STAGE_ONLY",
        "structured_candidates_seen": int(len(structured)),
        "review_rows_total": int(len(review)),
        "new_review_rows_added": int(added),
        "approved_review_rows": int(review["review_decision"].astype(str).str.upper().eq("APPROVE_NEW_PROJECT").sum()) if not review.empty else 0,
        "staged_rows": int(len(staging)),
        "conflicts": int(len(conflicts)),
        "validation_errors": validation_errors,
        "applied_rows": int(applied_count),
        "canonical_rows_before": int(len(canonical)),
        "canonical_rows_after": int(final_canonical_count),
        "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
        "canonical_master_changed": bool(args.apply and applied_count > 0),
    }
    append_audit(summary)

    print("PHASE 13D - CONTROLLED CANONICALIZATION")
    print("=" * 64)
    print(f"Mode                      : {summary['mode']}")
    print(f"Structured candidates     : {summary['structured_candidates_seen']}")
    print(f"Review rows               : {summary['review_rows_total']}")
    print(f"New review rows added     : {summary['new_review_rows_added']}")
    print(f"Approved review rows      : {summary['approved_review_rows']}")
    print(f"Staged rows               : {summary['staged_rows']}")
    print(f"Conflicts                 : {summary['conflicts']}")
    print(f"Applied rows              : {summary['applied_rows']}")
    print(f"Canonical rows before     : {summary['canonical_rows_before']}")
    print(f"Canonical rows after      : {summary['canonical_rows_after']}")
    print(f"Canonical master changed  : {summary['canonical_master_changed']}")
    print()
    print(f"Review gate   : {REVIEW_FILE.relative_to(ROOT)}")
    print(f"Staging file  : {STAGING_FILE.relative_to(ROOT)}")
    print(f"Conflict file : {CONFLICT_FILE.relative_to(ROOT)}")
    print(f"Audit log     : {AUDIT_FILE.relative_to(ROOT)}")

    if validation_errors:
        print("\nVALIDATION BLOCKS")
        for item in validation_errors:
            print(f"- {item}")

    if not args.apply:
        print("\nNo canonical data was changed. This run is stage-only by design.")
        print("Only after a reviewer fills Canonicalization_Review.csv and sets")
        print("review_decision=APPROVE_NEW_PROJECT should --apply be considered.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
