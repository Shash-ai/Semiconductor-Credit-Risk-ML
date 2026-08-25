from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
CONFIG_FILE = PHASE_DIR / "00_Config" / "financial_data_contract.json"
ENTITY_DIR = PHASE_DIR / "01_Entity_Master"
STAGING_DIR = PHASE_DIR / "02_Staging"
MASTER_DIR = PHASE_DIR / "03_Master"
AUDIT_DIR = PHASE_DIR / "04_Audit"

CANONICAL_FILE = (
    ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"
)
PHASE6F_FILE = ROOT / "03_Modeling" / "Phase_6F_Borrower_Fundamentals" / "Borrower_Fundamental_Risk_Scores.csv"
ARCHETYPE_FILE = ROOT / "03_Modeling" / "Phase_6F_Borrower_Fundamentals" / "NonComparable_Borrower_Archetypes.csv"

ENTITY_OUT = ENTITY_DIR / "Company_Financial_Entity_Master.csv"
STAGING_OUT = STAGING_DIR / "Financial_Statement_Staging.csv"
MASTER_OUT = MASTER_DIR / "Company_Financials_Longitudinal.csv"
GAP_OUT = AUDIT_DIR / "Financial_Data_Gap_Register.csv"
RUN_LOG = AUDIT_DIR / "Phase_14A_Run_Log.jsonl"

CONTRACT_VERSION = "SCI_FINANCIAL_MASTER_CONTRACT_V1"

ENTITY_COLUMNS = [
    "project_company_id",
    "project_company_name",
    "linked_project_ids",
    "project_count",
    "financial_entity_id",
    "financial_entity_name",
    "entity_relationship",
    "financial_statement_scope_status",
    "public_financials_status",
    "existing_financial_evidence_status",
    "existing_financial_year",
    "existing_primary_source_type",
    "existing_primary_source_authority",
    "existing_primary_source_url",
    "entity_resolution_notes",
    "entity_master_version",
    "updated_at",
]

STATEMENT_COLUMNS = [
    "observation_id",
    "project_company_id",
    "project_company_name",
    "linked_project_ids",
    "financial_entity_id",
    "financial_entity_name",
    "entity_scope",
    "financial_year",
    "financial_year_end",
    "currency",
    "unit",
    "accounting_standard",
    "statement_basis",
    "audited",
    "source_type",
    "source_authority",
    "source_url",
    "source_document",
    "page_reference",
    "verification_status",
    "evidence_type",
    "revenue",
    "other_income",
    "ebitda",
    "ebit",
    "depreciation_amortization",
    "finance_cost",
    "interest_expense",
    "pbt",
    "tax_expense",
    "pat",
    "total_assets",
    "noncurrent_assets",
    "ppe",
    "intangible_assets",
    "current_assets",
    "inventory",
    "receivables",
    "cash_and_equivalents",
    "total_equity",
    "net_worth",
    "total_debt",
    "short_term_debt",
    "long_term_debt",
    "current_liabilities",
    "total_liabilities",
    "operating_cash_flow",
    "capex",
    "investing_cash_flow",
    "financing_cash_flow",
    "dividends_paid",
    "free_cash_flow",
    "normalization_status",
    "observation_status",
    "review_notes",
    "collected_at",
]

CORE_FIELDS = [
    "revenue",
    "ebitda",
    "ebit",
    "pat",
    "total_debt",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "interest_expense",
    "operating_cash_flow",
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


def as_bool(value) -> bool | None:
    text = clean(value).lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def as_number(value):
    text = clean(value).replace(",", "")
    if not text:
        return pd.NA
    try:
        return float(text)
    except Exception:
        return pd.NA


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def observation_id(financial_entity_id: str, financial_year: str, entity_scope: str, source_url: str) -> str:
    return stable_id("OBS", "|".join([financial_entity_id, financial_year, entity_scope, source_url]))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def write_csv_atomic(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[columns]
    tmp = path.with_suffix(path.suffix + ".tmp")
    out.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def load_contract() -> dict:
    payload = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError(
            f"Financial data contract mismatch: {payload.get('contract_version')} != {CONTRACT_VERSION}"
        )
    return payload


def company_lookup(df: pd.DataFrame) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    if df.empty or "company" not in df.columns:
        return out
    for _, row in df.iterrows():
        company = clean(row.get("company"))
        if company and company not in out:
            out[company] = row
    return out


def scope_status(financial_row: pd.Series | None, archetype_row: pd.Series | None) -> str:
    if financial_row is not None:
        if as_bool(financial_row.get("is_parent_financials")) is True:
            return "RESOLVED_PARENT_ONLY"
        if as_bool(financial_row.get("is_exact_company_financials")) is True:
            return "RESOLVED_EXACT_PROJECT_COMPANY"
        if as_bool(financial_row.get("financial_evidence_verified")) is True:
            return "RESOLVED_COMPANY_OR_ENTITY_LEVEL"
    if archetype_row is not None:
        status = clean(archetype_row.get("verification_status")).upper()
        evidence_type = clean(archetype_row.get("financial_evidence_type")).upper()
        if "PARENT" in status or evidence_type == "PARENT_LEVEL":
            return "RESOLVED_PARENT_ONLY"
        if "EXACT" in status or evidence_type == "COMPANY_OR_ENTITY_LEVEL":
            return "RESOLVED_EXACT_ENTITY_PARTIAL"
    return "UNRESOLVED_FINANCIAL_SCOPE"


def build_entity_master(canonical: pd.DataFrame, phase6f: pd.DataFrame, archetypes: pd.DataFrame) -> pd.DataFrame:
    required = {"project_id", "company"}
    missing = required - set(canonical.columns)
    if canonical.empty or missing:
        raise RuntimeError(f"Canonical master invalid; missing columns={sorted(missing)}")

    evidence_lookup = company_lookup(phase6f)
    archetype_lookup = company_lookup(archetypes)
    now = utc_now()
    rows = []

    for company, group in canonical.groupby("company", sort=True):
        company = clean(company)
        linked_ids = sorted(group["project_id"].astype(str).map(clean).tolist())
        financial_row = evidence_lookup.get(company)
        archetype_row = archetype_lookup.get(company)

        financial_entity_name = company
        relationship = "UNRESOLVED_FINANCIAL_ENTITY_SCOPE"
        public_status = "NOT_VERIFIED"
        evidence_status = "NOT_COLLECTED"
        existing_year = source_type = source_authority = source_url = notes = ""

        if financial_row is not None:
            financial_entity_name = clean(financial_row.get("financial_entity_name")) or company
            relationship = clean(financial_row.get("entity_relationship")) or "COMPANY_OR_ENTITY_LEVEL"
            public_status = clean(financial_row.get("public_financials_available")) or "UNKNOWN"
            evidence_status = clean(financial_row.get("verification_status")) or clean(
                financial_row.get("financial_data_status")
            )
            existing_year = clean(financial_row.get("financial_year"))
            source_type = clean(financial_row.get("primary_source_type"))
            source_authority = clean(financial_row.get("primary_source_authority"))
            source_url = clean(financial_row.get("primary_source_url")) or clean(financial_row.get("value_source_url"))
            notes = clean(financial_row.get("notes")) or clean(financial_row.get("review_notes"))
        elif archetype_row is not None:
            relationship = clean(archetype_row.get("borrower_archetype")) or relationship
            evidence_status = clean(archetype_row.get("verification_status")) or evidence_status
            notes = clean(archetype_row.get("review_notes"))
            if "VERIFIED" in evidence_status.upper():
                public_status = "VERIFIED_PARTIAL_EVIDENCE_EXISTS"

        rows.append(
            {
                "project_company_id": stable_id("PCO", company),
                "project_company_name": company,
                "linked_project_ids": ";".join(linked_ids),
                "project_count": len(linked_ids),
                "financial_entity_id": stable_id("FEN", financial_entity_name),
                "financial_entity_name": financial_entity_name,
                "entity_relationship": relationship,
                "financial_statement_scope_status": scope_status(financial_row, archetype_row),
                "public_financials_status": public_status,
                "existing_financial_evidence_status": evidence_status,
                "existing_financial_year": existing_year,
                "existing_primary_source_type": source_type,
                "existing_primary_source_authority": source_authority,
                "existing_primary_source_url": source_url,
                "entity_resolution_notes": notes,
                "entity_master_version": CONTRACT_VERSION,
                "updated_at": now,
            }
        )
    return pd.DataFrame(rows, columns=ENTITY_COLUMNS)


def migrate_verified_phase6f(phase6f: pd.DataFrame, entity_master: pd.DataFrame) -> pd.DataFrame:
    if phase6f.empty:
        return pd.DataFrame(columns=STATEMENT_COLUMNS)

    entities = {
        clean(row["project_company_name"]): row
        for _, row in entity_master.iterrows()
    }
    rows = []
    now = utc_now()

    for _, src in phase6f.iterrows():
        if as_bool(src.get("financial_evidence_verified")) is not True:
            continue
        company = clean(src.get("company"))
        financial_year = clean(src.get("financial_year"))
        if company not in entities or not financial_year:
            continue

        entity = entities[company]
        is_parent = as_bool(src.get("is_parent_financials")) is True
        is_exact = as_bool(src.get("is_exact_company_financials")) is True
        evidence_type = clean(src.get("financial_evidence_type"))
        entity_scope = (
            "PARENT_LEVEL" if is_parent else
            "EXACT_PROJECT_COMPANY" if is_exact else
            "COMPANY_OR_ENTITY_LEVEL"
        )

        source_url = clean(src.get("value_source_url")) or clean(src.get("primary_source_url"))
        source_type = clean(src.get("primary_source_type"))
        verification_status = clean(src.get("verification_status"))
        if not source_type and "CRA" in verification_status.upper():
            source_type = "CREDIT_RATING_AGENCY_FINANCIAL_DISCLOSURE"

        record = {col: pd.NA for col in STATEMENT_COLUMNS}
        record.update(
            {
                "observation_id": observation_id(
                    clean(entity["financial_entity_id"]), financial_year, entity_scope, source_url
                ),
                "project_company_id": clean(entity["project_company_id"]),
                "project_company_name": company,
                "linked_project_ids": clean(entity["linked_project_ids"]),
                "financial_entity_id": clean(entity["financial_entity_id"]),
                "financial_entity_name": clean(src.get("financial_entity_name")) or clean(entity["financial_entity_name"]),
                "entity_scope": entity_scope,
                "financial_year": financial_year,
                "financial_year_end": "",
                "currency": clean(src.get("numbers_currency")) or clean(src.get("financial_currency")),
                "unit": clean(src.get("numbers_unit")) or clean(src.get("financial_unit")),
                "accounting_standard": "",
                "statement_basis": "",
                "audited": clean(src.get("audited")),
                "source_type": source_type,
                "source_authority": clean(src.get("primary_source_authority")),
                "source_url": source_url,
                "source_document": "",
                "page_reference": clean(src.get("page_reference")),
                "verification_status": verification_status,
                "evidence_type": evidence_type,
                "revenue": as_number(src.get("revenue")),
                "ebitda": as_number(src.get("ebitda")),
                "ebit": as_number(src.get("ebit")),
                "interest_expense": as_number(src.get("interest_expense")),
                "pat": as_number(src.get("pat")),
                "total_assets": as_number(src.get("total_assets_reported_crore")),
                "current_assets": as_number(src.get("current_assets")),
                "total_equity": as_number(src.get("total_equity")),
                "total_debt": as_number(src.get("total_debt")),
                "current_liabilities": as_number(src.get("current_liabilities")),
                "total_liabilities": as_number(src.get("total_liabilities_reported_crore")),
                "operating_cash_flow": as_number(src.get("operating_cash_flow")),
                "normalization_status": "SOURCE_CURRENCY_AND_UNIT_PRESERVED_PHASE14A",
                "observation_status": "MIGRATED_FROM_VERIFIED_PHASE6F",
                "review_notes": clean(src.get("review_notes")),
                "collected_at": now,
            }
        )
        rows.append(record)

    if not rows:
        return pd.DataFrame(columns=STATEMENT_COLUMNS)
    return pd.DataFrame(rows, columns=STATEMENT_COLUMNS).drop_duplicates("observation_id", keep="last")


def ensure_staging_template() -> None:
    if not STAGING_OUT.exists():
        write_csv_atomic(pd.DataFrame(columns=STATEMENT_COLUMNS), STAGING_OUT, STATEMENT_COLUMNS)


def build_gap_register(entity_master: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, entity in entity_master.iterrows():
        entity_id = clean(entity.get("financial_entity_id"))
        observations = (
            master[master["financial_entity_id"].astype(str).eq(entity_id)].copy()
            if not master.empty else pd.DataFrame()
        )
        available = {
            field for field in CORE_FIELDS
            if not observations.empty and field in observations.columns and observations[field].notna().any()
        }
        missing = [field for field in CORE_FIELDS if field not in available]
        coverage = round(len(available) / len(CORE_FIELDS) * 100.0, 2)

        if not observations.empty and coverage >= 80:
            status = "STRONG_CORE_COVERAGE"
            priority = "PRIORITY_3_REFRESH_HISTORY"
        elif not observations.empty:
            status = "PARTIAL_VERIFIED_FINANCIALS"
            priority = "PRIORITY_1_FILL_BALANCE_SHEET_AND_CASH_FLOW"
        else:
            status = "NO_VERIFIED_LONGITUDINAL_OBSERVATION"
            priority = "PRIORITY_1_ENTITY_RESOLUTION_AND_SOURCE_COLLECTION"

        rows.append(
            {
                "project_company_id": clean(entity.get("project_company_id")),
                "project_company_name": clean(entity.get("project_company_name")),
                "linked_project_ids": clean(entity.get("linked_project_ids")),
                "financial_entity_id": entity_id,
                "financial_entity_name": clean(entity.get("financial_entity_name")),
                "financial_statement_scope_status": clean(entity.get("financial_statement_scope_status")),
                "verified_observation_count": int(len(observations)),
                "latest_financial_year": clean(observations.iloc[-1].get("financial_year")) if not observations.empty else "",
                "core_fields_available": len(available),
                "core_fields_total": len(CORE_FIELDS),
                "core_coverage_pct": coverage,
                "missing_core_fields": ";".join(missing),
                "financial_data_status": status,
                "next_collection_priority": priority,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    started = utc_now()
    contract = load_contract()
    canonical = read_csv(CANONICAL_FILE)
    phase6f = read_csv(PHASE6F_FILE)
    archetypes = read_csv(ARCHETYPE_FILE)

    entity_master = build_entity_master(canonical, phase6f, archetypes)
    migrated_master = migrate_verified_phase6f(phase6f, entity_master)

    existing_master = read_csv(MASTER_OUT)
    if not existing_master.empty:
        for col in STATEMENT_COLUMNS:
            if col not in existing_master.columns:
                existing_master[col] = pd.NA
        combined = pd.concat(
            [existing_master[STATEMENT_COLUMNS], migrated_master[STATEMENT_COLUMNS]],
            ignore_index=True,
        ).drop_duplicates(subset=["observation_id"], keep="first")
    else:
        combined = migrated_master.copy()

    write_csv_atomic(entity_master, ENTITY_OUT, ENTITY_COLUMNS)
    ensure_staging_template()
    write_csv_atomic(combined, MASTER_OUT, STATEMENT_COLUMNS)
    gaps = build_gap_register(entity_master, combined)
    write_csv_atomic(gaps, GAP_OUT, list(gaps.columns))

    verified_phase6f = 0
    if not phase6f.empty and "financial_evidence_verified" in phase6f.columns:
        verified_phase6f = int(
            phase6f["financial_evidence_verified"].astype(str).str.lower().isin(["1", "true", "yes"]).sum()
        )

    summary = {
        "phase": "14A",
        "run_at": utc_now(),
        "started_at": started,
        "status": "SUCCESS",
        "contract_version": contract.get("contract_version"),
        "canonical_project_rows": int(len(canonical)),
        "unique_project_companies": int(entity_master["project_company_name"].nunique()),
        "entity_master_rows": int(len(entity_master)),
        "verified_phase6f_rows_available": verified_phase6f,
        "longitudinal_master_rows": int(len(combined)),
        "companies_with_at_least_one_verified_observation": int(
            combined["project_company_id"].nunique() if not combined.empty else 0
        ),
        "companies_without_verified_observation": int(
            (gaps["verified_observation_count"] == 0).sum() if not gaps.empty else 0
        ),
        "guardrails": {
            "project_investment_used_as_bank_exposure_or_ead": False,
            "parent_financials_treated_as_project_financials": False,
            "missing_financial_values_imputed": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False
        },
        "outputs": [
            str(ENTITY_OUT.relative_to(ROOT)),
            str(STAGING_OUT.relative_to(ROOT)),
            str(MASTER_OUT.relative_to(ROOT)),
            str(GAP_OUT.relative_to(ROOT))
        ]
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14A - COMPANY FINANCIAL MASTER")
    print("=" * 72)
    print(f"Canonical project rows                  : {summary['canonical_project_rows']}")
    print(f"Unique project companies                : {summary['unique_project_companies']}")
    print(f"Entity master rows                      : {summary['entity_master_rows']}")
    print(f"Verified Phase 6F rows migrated         : {summary['verified_phase6f_rows_available']}")
    print(f"Longitudinal financial observations     : {summary['longitudinal_master_rows']}")
    print(f"Companies with verified observations    : {summary['companies_with_at_least_one_verified_observation']}")
    print(f"Companies needing financial collection  : {summary['companies_without_verified_observation']}")
    print()
    print(f"Entity master                           : {ENTITY_OUT.relative_to(ROOT)}")
    print(f"Longitudinal master                     : {MASTER_OUT.relative_to(ROOT)}")
    print(f"Gap register                            : {GAP_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: public corporate-finance evidence only; no invented bank exposure, PD/LGD/EAD/ECL or automatic credit decision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
