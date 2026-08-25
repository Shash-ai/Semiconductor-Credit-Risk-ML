from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
CONTRACT_FILE = PHASE_DIR / "00_Config" / "financial_data_contract.json"
ACQ_DIR = PHASE_DIR / "05_Acquisition"
STAGING_FILE = PHASE_DIR / "02_Staging" / "Financial_Statement_Staging.csv"
MASTER_FILE = PHASE_DIR / "03_Master" / "Company_Financials_Longitudinal.csv"
AUDIT_DIR = PHASE_DIR / "04_Audit"
RUN_LOG = AUDIT_DIR / "Phase_14B_Staging_Run_Log.jsonl"

REVIEW_PATTERN = "Reviewed_Financial_Observations_*.csv"
PROMOTED_VERIFICATION = "PRIMARY_SOURCE_VERIFIED_PROMOTED"
PROMOTED_OBSERVATION = "PROMOTED_TO_LONGITUDINAL_MASTER"
REQUIRED_FIELDS = [
    "observation_id",
    "project_company_id",
    "project_company_name",
    "financial_entity_id",
    "financial_entity_name",
    "entity_scope",
    "financial_year",
    "currency",
    "unit",
    "source_type",
    "source_url",
    "verification_status",
    "observation_status",
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
    return " ".join(str(value).split()).strip()


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def main() -> int:
    contract = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
    allowed_scopes = set(contract.get("allowed_entity_scopes", []))
    files = sorted(ACQ_DIR.glob(REVIEW_PATTERN))
    if not files:
        raise RuntimeError(f"No reviewed financial observation files found under {ACQ_DIR}")

    batches: list[pd.DataFrame] = []
    for path in files:
        df = read_csv(path)
        if df.empty:
            continue
        missing_cols = [c for c in REQUIRED_FIELDS if c not in df.columns]
        if missing_cols:
            raise RuntimeError(f"{path.name}: missing required columns {missing_cols}")

        for idx, row in df.iterrows():
            missing_values = [c for c in REQUIRED_FIELDS if not clean(row.get(c))]
            if missing_values:
                raise RuntimeError(
                    f"{path.name} row {idx}: missing required provenance values {missing_values}"
                )
            scope = clean(row.get("entity_scope"))
            if scope not in allowed_scopes:
                raise RuntimeError(f"{path.name} row {idx}: unsupported entity_scope={scope}")
            if clean(row.get("verification_status")) != "PRIMARY_SOURCE_VERIFIED_REVIEW_READY":
                raise RuntimeError(
                    f"{path.name} row {idx}: verification_status must be PRIMARY_SOURCE_VERIFIED_REVIEW_READY"
                )
            if clean(row.get("observation_status")) != "REVIEW_READY_NOT_PROMOTED":
                raise RuntimeError(
                    f"{path.name} row {idx}: observation_status must be REVIEW_READY_NOT_PROMOTED"
                )
        batches.append(df)

    if not batches:
        raise RuntimeError("Reviewed source files contained no rows")

    reviewed = pd.concat(batches, ignore_index=True)
    if reviewed["observation_id"].astype(str).duplicated().any():
        dupes = reviewed.loc[
            reviewed["observation_id"].astype(str).duplicated(keep=False), "observation_id"
        ].tolist()
        raise RuntimeError(f"Duplicate reviewed observation IDs: {dupes}")

    staging = read_csv(STAGING_FILE) if STAGING_FILE.exists() else pd.DataFrame()
    master = read_csv(MASTER_FILE) if MASTER_FILE.exists() else pd.DataFrame()

    # Never downgrade a previously promoted observation back to REVIEW_READY just
    # because its immutable reviewed source batch is scanned again on a later run.
    protected_ids: set[str] = set()
    if not staging.empty and {"observation_id", "observation_status"}.issubset(staging.columns):
        mask = staging["observation_status"].astype(str).eq(PROMOTED_OBSERVATION)
        protected_ids.update(staging.loc[mask, "observation_id"].astype(str).tolist())
    if not master.empty and "observation_id" in master.columns:
        if "observation_status" in master.columns:
            mask = master["observation_status"].astype(str).eq(PROMOTED_OBSERVATION)
            protected_ids.update(master.loc[mask, "observation_id"].astype(str).tolist())
        if "verification_status" in master.columns:
            mask = master["verification_status"].astype(str).eq(PROMOTED_VERIFICATION)
            protected_ids.update(master.loc[mask, "observation_id"].astype(str).tolist())

    reviewed_new = reviewed[~reviewed["observation_id"].astype(str).isin(protected_ids)].copy()

    if not staging.empty:
        all_columns = list(dict.fromkeys(list(staging.columns) + list(reviewed.columns)))
        staging = staging.reindex(columns=all_columns)
        reviewed_new = reviewed_new.reindex(columns=all_columns)
        combined = pd.concat([staging, reviewed_new], ignore_index=True)
    else:
        combined = reviewed_new.copy()

    combined = combined.drop_duplicates(subset=["observation_id"], keep="last")
    STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STAGING_FILE.with_suffix(".csv.tmp")
    combined.to_csv(tmp, index=False)
    tmp.replace(STAGING_FILE)

    summary = {
        "phase": "14B",
        "run_at": utc_now(),
        "status": "SUCCESS_REVIEWED_OBSERVATIONS_STAGED_NOT_PROMOTED",
        "review_files": [p.name for p in files],
        "reviewed_rows_seen": int(len(reviewed)),
        "new_review_ready_rows_staged": int(len(reviewed_new)),
        "protected_already_promoted_rows": int(len(reviewed) - len(reviewed_new)),
        "staging_rows_after": int(len(combined)),
        "master_modified": False,
        "guardrails": {
            "previously_promoted_rows_downgraded": False,
            "reviewed_rows_promoted_to_master": False,
            "project_investment_used_as_bank_exposure_or_ead": False,
            "missing_financial_values_imputed": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14B - REVIEWED FINANCIAL OBSERVATIONS STAGING")
    print("=" * 72)
    print(f"Reviewed source files             : {len(files)}")
    print(f"Reviewed rows seen                : {len(reviewed)}")
    print(f"New review-ready rows staged      : {len(reviewed_new)}")
    print(f"Already-promoted rows protected   : {len(reviewed) - len(reviewed_new)}")
    print(f"Staging rows after merge          : {len(combined)}")
    print("Master modified                   : False")
    print(f"Staging file                      : {STAGING_FILE.relative_to(ROOT)}")
    print()
    print("Guardrail: source-reviewed observations are staged only. Previously promoted observations are preserved and are never downgraded by a later source scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
