from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
CONTRACT_FILE = PHASE_DIR / "00_Config" / "financial_data_contract.json"
ENTITY_FILE = PHASE_DIR / "01_Entity_Master" / "Company_Financial_Entity_Master.csv"
STAGING_FILE = PHASE_DIR / "02_Staging" / "Financial_Statement_Staging.csv"
MASTER_FILE = PHASE_DIR / "03_Master" / "Company_Financials_Longitudinal.csv"
AUDIT_DIR = PHASE_DIR / "04_Audit"
VALIDATION_FILE = AUDIT_DIR / "Financial_Observation_Validation_Report.csv"
CONFLICT_FILE = AUDIT_DIR / "Financial_Observation_Promotion_Conflicts.csv"
RUN_LOG = AUDIT_DIR / "Phase_14B_Promotion_Run_Log.jsonl"
BACKUP_DIR = AUDIT_DIR / "Master_Backups"

CONFIRMATION_TOKEN = "PROMOTE_VERIFIED_FINANCIAL_OBSERVATIONS"
READY_VERIFICATION = "PRIMARY_SOURCE_VERIFIED_REVIEW_READY"
READY_OBSERVATION = "REVIEW_READY_NOT_PROMOTED"
PROMOTED_VERIFICATION = "PRIMARY_SOURCE_VERIFIED_PROMOTED"
PROMOTED_OBSERVATION = "PROMOTED_TO_LONGITUDINAL_MASTER"

PROVENANCE_FIELDS = [
    "observation_id",
    "project_company_id",
    "project_company_name",
    "financial_entity_id",
    "financial_entity_name",
    "entity_scope",
    "financial_year",
    "financial_year_end",
    "currency",
    "unit",
    "source_type",
    "source_authority",
    "source_url",
    "verification_status",
    "observation_status",
]

NUMERIC_FIELDS = [
    "revenue", "other_income", "ebitda", "ebit", "depreciation_amortization",
    "finance_cost", "interest_expense", "pbt", "tax_expense", "pat",
    "total_assets", "noncurrent_assets", "ppe", "intangible_assets",
    "current_assets", "inventory", "receivables", "cash_and_equivalents",
    "total_equity", "net_worth", "total_debt", "short_term_debt",
    "long_term_debt", "current_liabilities", "total_liabilities",
    "operating_cash_flow", "capex", "investing_cash_flow",
    "financing_cash_flow", "dividends_paid", "free_cash_flow",
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
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def numeric(value):
    if clean(value) == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def add_check(checks: list[dict], row, check_name: str, passed: bool, severity: str, detail: str) -> None:
    checks.append({
        "observation_id": clean(row.get("observation_id")),
        "project_company_name": clean(row.get("project_company_name")),
        "financial_entity_name": clean(row.get("financial_entity_name")),
        "financial_year": clean(row.get("financial_year")),
        "entity_scope": clean(row.get("entity_scope")),
        "check_name": check_name,
        "passed": bool(passed),
        "severity": severity,
        "detail": detail,
    })


def validate(staging: pd.DataFrame, entity_master: pd.DataFrame, contract: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    checks: list[dict] = []
    conflicts: list[dict] = []

    if staging.empty:
        raise RuntimeError("Financial staging table is empty. Run the Phase 14B staging gate first.")

    missing_columns = [c for c in PROVENANCE_FIELDS if c not in staging.columns]
    if missing_columns:
        raise RuntimeError(f"Staging table missing required columns: {missing_columns}")

    allowed_scopes = set(contract.get("allowed_entity_scopes", []))
    allowed_sources = set(contract.get("source_hierarchy", []))

    entity_pairs = set()
    if not entity_master.empty:
        for _, e in entity_master.iterrows():
            entity_pairs.add((clean(e.get("project_company_id")), clean(e.get("project_company_name"))))

    obs_ids = staging["observation_id"].astype(str)
    duplicate_ids = set(obs_ids[obs_ids.duplicated(keep=False)].tolist())

    economic_key_seen: dict[tuple[str, str, str], str] = {}

    for idx, row in staging.iterrows():
        oid = clean(row.get("observation_id"))

        for field in PROVENANCE_FIELDS:
            ok = bool(clean(row.get(field)))
            add_check(checks, row, f"required_provenance:{field}", ok, "HARD", "present" if ok else "missing")

        scope = clean(row.get("entity_scope"))
        add_check(
            checks, row, "allowed_entity_scope", scope in allowed_scopes, "HARD",
            f"scope={scope}; allowed={scope in allowed_scopes}"
        )

        source_type = clean(row.get("source_type"))
        add_check(
            checks, row, "allowed_source_type", source_type in allowed_sources, "HARD",
            f"source_type={source_type}; allowed={source_type in allowed_sources}"
        )

        source_url = clean(row.get("source_url"))
        url_ok = source_url.startswith("https://") or source_url.startswith("http://")
        add_check(checks, row, "source_url_format", url_ok, "HARD", source_url)

        entity_ok = (clean(row.get("project_company_id")), clean(row.get("project_company_name"))) in entity_pairs
        add_check(checks, row, "project_company_entity_master_match", entity_ok, "HARD", str(entity_ok))

        ready_status = clean(row.get("verification_status")) in {READY_VERIFICATION, PROMOTED_VERIFICATION}
        add_check(checks, row, "verification_status_gate", ready_status, "HARD", clean(row.get("verification_status")))

        observation_status_ok = clean(row.get("observation_status")) in {READY_OBSERVATION, PROMOTED_OBSERVATION}
        add_check(checks, row, "observation_status_gate", observation_status_ok, "HARD", clean(row.get("observation_status")))

        add_check(checks, row, "unique_observation_id", oid not in duplicate_ids, "HARD", oid)

        # Numeric parse checks: blanks are legitimate; populated accounting facts must parse.
        for field in NUMERIC_FIELDS:
            if field not in staging.columns or clean(row.get(field)) == "":
                continue
            ok = numeric(row.get(field)) is not None
            add_check(checks, row, f"numeric_parse:{field}", ok, "HARD", clean(row.get(field)))

        # Basic accounting sanity/reconciliation. Negative cash-flow and profit values are allowed.
        total_assets = numeric(row.get("total_assets"))
        total_liabilities = numeric(row.get("total_liabilities"))
        total_equity = numeric(row.get("total_equity"))
        current_assets = numeric(row.get("current_assets"))
        current_liabilities = numeric(row.get("current_liabilities"))
        total_debt = numeric(row.get("total_debt"))
        short_debt = numeric(row.get("short_term_debt"))
        long_debt = numeric(row.get("long_term_debt"))

        if total_assets is not None:
            add_check(checks, row, "total_assets_nonnegative", total_assets >= 0, "HARD", str(total_assets))
        if total_liabilities is not None:
            add_check(checks, row, "total_liabilities_nonnegative", total_liabilities >= 0, "HARD", str(total_liabilities))
        if total_debt is not None:
            add_check(checks, row, "total_debt_nonnegative", total_debt >= 0, "HARD", str(total_debt))

        if total_assets is not None and current_assets is not None:
            tol = max(1.0, abs(total_assets) * 0.001)
            add_check(checks, row, "current_assets_le_total_assets", current_assets <= total_assets + tol, "HARD", f"{current_assets} <= {total_assets}")
        if total_liabilities is not None and current_liabilities is not None:
            tol = max(1.0, abs(total_liabilities) * 0.001)
            add_check(checks, row, "current_liabilities_le_total_liabilities", current_liabilities <= total_liabilities + tol, "HARD", f"{current_liabilities} <= {total_liabilities}")

        if total_assets is not None and total_liabilities is not None and total_equity is not None:
            diff = abs(total_assets - (total_liabilities + total_equity))
            tol = max(1.0, abs(total_assets) * 0.001)
            add_check(
                checks, row, "balance_sheet_equation",
                diff <= tol, "HARD",
                f"assets={total_assets}; liabilities+equity={total_liabilities + total_equity}; diff={diff}; tol={tol}"
            )

        if total_debt is not None and short_debt is not None and long_debt is not None:
            diff = abs(total_debt - (short_debt + long_debt))
            tol = max(1.0, abs(total_debt) * 0.001)
            add_check(
                checks, row, "debt_component_reconciliation",
                diff <= tol, "HARD",
                f"total_debt={total_debt}; short+long={short_debt + long_debt}; diff={diff}; tol={tol}"
            )

        key = (clean(row.get("financial_entity_id")), scope, clean(row.get("financial_year")))
        prior = economic_key_seen.get(key)
        if prior and prior != oid:
            conflicts.append({
                "conflict_type": "DUPLICATE_ECONOMIC_KEY_IN_STAGING",
                "financial_entity_id": key[0],
                "entity_scope": key[1],
                "financial_year": key[2],
                "observation_id_1": prior,
                "observation_id_2": oid,
                "detail": "Two observation IDs represent the same entity/scope/financial-year key.",
            })
        else:
            economic_key_seen[key] = oid

    return pd.DataFrame(checks), pd.DataFrame(conflicts)


def master_conflicts(staging: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    rows = []
    for _, row in staging.iterrows():
        oid = clean(row.get("observation_id"))
        key = (
            clean(row.get("financial_entity_id")),
            clean(row.get("entity_scope")),
            clean(row.get("financial_year")),
        )
        same_key = master[
            master.get("financial_entity_id", pd.Series(dtype=str)).astype(str).eq(key[0])
            & master.get("entity_scope", pd.Series(dtype=str)).astype(str).eq(key[1])
            & master.get("financial_year", pd.Series(dtype=str)).astype(str).eq(key[2])
        ] if {"financial_entity_id", "entity_scope", "financial_year"}.issubset(master.columns) else pd.DataFrame()

        different = same_key[~same_key["observation_id"].astype(str).eq(oid)] if not same_key.empty and "observation_id" in same_key.columns else pd.DataFrame()
        if not different.empty:
            rows.append({
                "conflict_type": "ECONOMIC_KEY_ALREADY_EXISTS_IN_MASTER_WITH_DIFFERENT_OBSERVATION_ID",
                "financial_entity_id": key[0],
                "entity_scope": key[1],
                "financial_year": key[2],
                "staging_observation_id": oid,
                "master_observation_ids": ";".join(different["observation_id"].astype(str).tolist()),
                "detail": "Manual review required before replacing an existing entity/scope/year observation.",
            })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and explicitly promote Phase 14B financial observations")
    parser.add_argument("--promote", action="store_true", help="Promote validated staging rows into the longitudinal master")
    parser.add_argument("--confirmation", default="", help=f"Required with --promote: {CONFIRMATION_TOKEN}")
    args = parser.parse_args()

    contract = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
    staging = read_csv(STAGING_FILE)
    entity_master = read_csv(ENTITY_FILE)
    master = read_csv(MASTER_FILE)

    checks, staging_conflicts = validate(staging, entity_master, contract)
    existing_conflicts = master_conflicts(staging, master)
    conflicts = pd.concat([staging_conflicts, existing_conflicts], ignore_index=True) if not staging_conflicts.empty or not existing_conflicts.empty else pd.DataFrame()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(checks, VALIDATION_FILE)
    atomic_write(conflicts, CONFLICT_FILE)

    hard_failures = checks[(checks["severity"] == "HARD") & (~checks["passed"].astype(bool))] if not checks.empty else pd.DataFrame()
    validation_pass = hard_failures.empty and conflicts.empty

    if not args.promote:
        summary = {
            "phase": "14B",
            "run_at": utc_now(),
            "mode": "VALIDATE_ONLY",
            "status": "PASS_READY_FOR_EXPLICIT_PROMOTION" if validation_pass else "FAIL_VALIDATION_OR_CONFLICTS",
            "staging_rows": int(len(staging)),
            "validation_checks": int(len(checks)),
            "hard_failures": int(len(hard_failures)),
            "conflicts": int(len(conflicts)),
            "master_modified": False,
        }
        append_jsonl(RUN_LOG, summary)
        print("PHASE 14B - FINANCIAL OBSERVATION VALIDATION")
        print("=" * 72)
        print(f"Staging rows                     : {len(staging)}")
        print(f"Validation checks                : {len(checks)}")
        print(f"Hard failures                    : {len(hard_failures)}")
        print(f"Promotion conflicts              : {len(conflicts)}")
        print(f"Status                           : {summary['status']}")
        print("Master modified                  : False")
        print(f"Validation report                : {VALIDATION_FILE.relative_to(ROOT)}")
        print(f"Conflict report                  : {CONFLICT_FILE.relative_to(ROOT)}")
        return 0 if validation_pass else 1

    if args.confirmation != CONFIRMATION_TOKEN:
        raise RuntimeError(f"Promotion requires --confirmation {CONFIRMATION_TOKEN}")
    if not validation_pass:
        raise RuntimeError(
            f"Promotion blocked: hard_failures={len(hard_failures)}, conflicts={len(conflicts)}. Review audit outputs first."
        )

    # Promote only rows that are not already marked promoted. Keep raw accounting facts unchanged.
    promote_rows = staging[staging["observation_status"].astype(str).eq(READY_OBSERVATION)].copy()
    if promote_rows.empty:
        print("No REVIEW_READY_NOT_PROMOTED rows remain. Master not modified.")
        return 0

    promote_rows["verification_status"] = PROMOTED_VERIFICATION
    promote_rows["observation_status"] = PROMOTED_OBSERVATION

    all_columns = list(dict.fromkeys(list(master.columns) + list(promote_rows.columns))) if not master.empty else list(promote_rows.columns)
    master_aligned = master.reindex(columns=all_columns) if not master.empty else pd.DataFrame(columns=all_columns)
    promote_aligned = promote_rows.reindex(columns=all_columns)

    if MASTER_FILE.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = BACKUP_DIR / f"Company_Financials_Longitudinal_before_{stamp}.csv"
        shutil.copy2(MASTER_FILE, backup)
    else:
        backup = None

    combined = pd.concat([master_aligned, promote_aligned], ignore_index=True)
    combined = combined.drop_duplicates(subset=["observation_id"], keep="last")
    atomic_write(combined, MASTER_FILE)

    # Preserve staged evidence and mark promoted rows there as promoted for rerun safety.
    updated_staging = staging.copy()
    ids = set(promote_rows["observation_id"].astype(str))
    mask = updated_staging["observation_id"].astype(str).isin(ids)
    updated_staging.loc[mask, "verification_status"] = PROMOTED_VERIFICATION
    updated_staging.loc[mask, "observation_status"] = PROMOTED_OBSERVATION
    atomic_write(updated_staging, STAGING_FILE)

    summary = {
        "phase": "14B",
        "run_at": utc_now(),
        "mode": "EXPLICIT_PROMOTION",
        "status": "PASS_PROMOTED_TO_LONGITUDINAL_MASTER",
        "promoted_rows": int(len(promote_rows)),
        "master_rows_after": int(len(combined)),
        "backup_file": str(backup.relative_to(ROOT)) if backup else None,
        "guardrails": {
            "raw_accounting_facts_recalculated_during_promotion": False,
            "project_investment_used_as_bank_exposure_or_ead": False,
            "missing_financial_values_imputed": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14B - EXPLICIT FINANCIAL OBSERVATION PROMOTION")
    print("=" * 72)
    print(f"Promoted rows                    : {len(promote_rows)}")
    print(f"Master rows after                : {len(combined)}")
    print(f"Master backup                    : {summary['backup_file']}")
    print("Status                           : PASS_PROMOTED_TO_LONGITUDINAL_MASTER")
    print("Guardrail: promotion preserves source accounting facts; it does not calculate risk scores or private bank variables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
