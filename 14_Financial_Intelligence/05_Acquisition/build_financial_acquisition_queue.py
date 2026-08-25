from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
ENTITY_FILE = PHASE_DIR / "01_Entity_Master" / "Company_Financial_Entity_Master.csv"
MASTER_FILE = PHASE_DIR / "03_Master" / "Company_Financials_Longitudinal.csv"
GAP_FILE = PHASE_DIR / "04_Audit" / "Financial_Data_Gap_Register.csv"
OUT_DIR = PHASE_DIR / "05_Acquisition"
QUEUE_FILE = OUT_DIR / "Financial_Acquisition_Queue.csv"
SOURCE_REGISTRY_FILE = OUT_DIR / "Financial_Source_Registry.csv"
RUN_LOG = OUT_DIR / "Phase_14B_Acquisition_Run_Log.jsonl"

ACQUISITION_VERSION = "SCI_FINANCIAL_ACQUISITION_V1"
TARGET_HISTORY_YEARS = 5

SOURCE_HIERARCHY = [
    "AUDITED_ANNUAL_REPORT_OR_FINANCIAL_STATEMENTS",
    "STOCK_EXCHANGE_OR_STATUTORY_REGULATORY_FILING",
    "SEC_OR_EQUIVALENT_FOREIGN_REGULATOR_FILING",
    "COMPANY_INVESTOR_RELATIONS_FILING",
    "CREDIT_RATING_AGENCY_FINANCIAL_DISCLOSURE",
]

QUEUE_COLUMNS = [
    "acquisition_id",
    "project_company_id",
    "project_company_name",
    "linked_project_ids",
    "financial_entity_id",
    "financial_entity_name",
    "financial_statement_scope_status",
    "verified_observation_count",
    "latest_financial_year",
    "core_coverage_pct",
    "missing_core_fields",
    "target_history_years",
    "target_period_policy",
    "preferred_source_1",
    "preferred_source_2",
    "preferred_source_3",
    "existing_primary_source_type",
    "existing_primary_source_authority",
    "existing_primary_source_url",
    "source_research_status",
    "collection_objective",
    "next_collection_priority",
    "human_review_required",
    "queue_status",
    "acquisition_version",
    "generated_at",
]

SOURCE_COLUMNS = [
    "source_record_id",
    "financial_entity_id",
    "financial_entity_name",
    "source_type",
    "source_authority",
    "source_url",
    "source_document",
    "financial_year",
    "entity_scope",
    "audited",
    "verification_status",
    "primary_accounting_evidence",
    "review_notes",
    "source_registry_version",
    "updated_at",
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


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"


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


def require_phase14a_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [str(p.relative_to(ROOT)) for p in [ENTITY_FILE, MASTER_FILE, GAP_FILE] if not p.exists()]
    if missing:
        raise RuntimeError(
            "Phase 14A outputs are required before Phase 14B. Missing: " + ", ".join(missing)
        )

    entities = read_csv(ENTITY_FILE)
    master = read_csv(MASTER_FILE)
    gaps = read_csv(GAP_FILE)

    required_entity = {"project_company_id", "project_company_name", "financial_entity_id", "financial_entity_name"}
    required_gap = {"project_company_id", "verified_observation_count", "core_coverage_pct", "missing_core_fields"}
    if not required_entity.issubset(entities.columns):
        raise RuntimeError("Phase 14A entity master schema is incomplete")
    if not required_gap.issubset(gaps.columns):
        raise RuntimeError("Phase 14A gap register schema is incomplete")
    return entities, master, gaps


def collection_objective(observation_count: int, coverage: float, missing_fields: str) -> str:
    if observation_count == 0:
        return "RESOLVE_ENTITY_SCOPE_AND_COLLECT_FIRST_VERIFIED_FINANCIAL_STATEMENT"
    if coverage < 80:
        return "COMPLETE_PARTIAL_STATEMENT_AND_FILL_MISSING_CORE_FIELDS"
    if missing_fields:
        return "FILL_REMAINING_CORE_FIELDS_AND_EXTEND_HISTORY"
    return "EXTEND_VERIFIED_LONGITUDINAL_HISTORY"


def build_queue(entities: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    now = utc_now()
    merged = entities.merge(
        gaps,
        on=["project_company_id", "project_company_name", "linked_project_ids", "financial_entity_id", "financial_entity_name", "financial_statement_scope_status"],
        how="left",
        suffixes=("", "_gap"),
    )

    rows = []
    for _, row in merged.iterrows():
        company_id = clean(row.get("project_company_id"))
        entity_id = clean(row.get("financial_entity_id"))
        obs_count = int(pd.to_numeric(row.get("verified_observation_count"), errors="coerce") or 0)
        coverage_val = pd.to_numeric(row.get("core_coverage_pct"), errors="coerce")
        coverage = float(coverage_val) if pd.notna(coverage_val) else 0.0
        missing_fields = clean(row.get("missing_core_fields"))
        existing_url = clean(row.get("existing_primary_source_url"))

        rows.append({
            "acquisition_id": stable_id("ACQ", f"{company_id}|{entity_id}"),
            "project_company_id": company_id,
            "project_company_name": clean(row.get("project_company_name")),
            "linked_project_ids": clean(row.get("linked_project_ids")),
            "financial_entity_id": entity_id,
            "financial_entity_name": clean(row.get("financial_entity_name")),
            "financial_statement_scope_status": clean(row.get("financial_statement_scope_status")),
            "verified_observation_count": obs_count,
            "latest_financial_year": clean(row.get("latest_financial_year")),
            "core_coverage_pct": coverage,
            "missing_core_fields": missing_fields,
            "target_history_years": TARGET_HISTORY_YEARS,
            "target_period_policy": "COLLECT_LATEST_FIVE_VERIFIED_ANNUAL_PERIODS_WHERE_PUBLICLY_AVAILABLE; DO_NOT_SYNTHESIZE_MISSING_YEARS",
            "preferred_source_1": SOURCE_HIERARCHY[0],
            "preferred_source_2": SOURCE_HIERARCHY[1],
            "preferred_source_3": SOURCE_HIERARCHY[2],
            "existing_primary_source_type": clean(row.get("existing_primary_source_type")),
            "existing_primary_source_authority": clean(row.get("existing_primary_source_authority")),
            "existing_primary_source_url": existing_url,
            "source_research_status": "EXISTING_SOURCE_AVAILABLE_FOR_REVIEW" if existing_url else "SOURCE_RESEARCH_REQUIRED",
            "collection_objective": collection_objective(obs_count, coverage, missing_fields),
            "next_collection_priority": clean(row.get("next_collection_priority")),
            "human_review_required": True,
            "queue_status": "READY_FOR_SOURCE_RESEARCH",
            "acquisition_version": ACQUISITION_VERSION,
            "generated_at": now,
        })

    out = pd.DataFrame(rows, columns=QUEUE_COLUMNS)
    if not out.empty:
        priority_order = {
            "PRIORITY_1_ENTITY_RESOLUTION_AND_SOURCE_COLLECTION": 1,
            "PRIORITY_1_FILL_BALANCE_SHEET_AND_CASH_FLOW": 2,
            "PRIORITY_3_REFRESH_HISTORY": 3,
        }
        out["_priority"] = out["next_collection_priority"].map(priority_order).fillna(9)
        out = out.sort_values(["_priority", "core_coverage_pct", "project_company_name"]).drop(columns="_priority")
    return out


def build_source_registry(entities: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    now = utc_now()
    rows = []

    # Seed registry only from already-existing Phase 14A evidence. No new URL is
    # invented or promoted merely because a company appears in the project universe.
    if not master.empty:
        for _, src in master.iterrows():
            url = clean(src.get("source_url"))
            if not url:
                continue
            entity_id = clean(src.get("financial_entity_id"))
            entity_name = clean(src.get("financial_entity_name"))
            source_type = clean(src.get("source_type"))
            authority = clean(src.get("source_authority"))
            financial_year = clean(src.get("financial_year"))
            scope = clean(src.get("entity_scope"))
            key = "|".join([entity_id, url, financial_year, scope])
            rows.append({
                "source_record_id": stable_id("FSRC", key),
                "financial_entity_id": entity_id,
                "financial_entity_name": entity_name,
                "source_type": source_type,
                "source_authority": authority,
                "source_url": url,
                "source_document": clean(src.get("source_document")),
                "financial_year": financial_year,
                "entity_scope": scope,
                "audited": clean(src.get("audited")),
                "verification_status": clean(src.get("verification_status")),
                "primary_accounting_evidence": source_type.upper() in {
                    "AUDITED ANNUAL REPORT",
                    "AUDITED_ANNUAL_REPORT_OR_FINANCIAL_STATEMENTS",
                    "STOCK_EXCHANGE_OR_STATUTORY_REGULATORY_FILING",
                    "SEC_OR_EQUIVALENT_FOREIGN_REGULATOR_FILING",
                },
                "review_notes": "Seeded from already verified Phase 14A/Phase 6F evidence; source scope must remain explicit.",
                "source_registry_version": ACQUISITION_VERSION,
                "updated_at": now,
            })

    if not rows:
        return pd.DataFrame(columns=SOURCE_COLUMNS)
    return pd.DataFrame(rows, columns=SOURCE_COLUMNS).drop_duplicates("source_record_id", keep="last")


def main() -> int:
    started = utc_now()
    entities, master, gaps = require_phase14a_inputs()

    queue = build_queue(entities, gaps)
    seeded_registry = build_source_registry(entities, master)

    existing_registry = read_csv(SOURCE_REGISTRY_FILE)
    if not existing_registry.empty:
        for col in SOURCE_COLUMNS:
            if col not in existing_registry.columns:
                existing_registry[col] = pd.NA
        registry = pd.concat(
            [existing_registry[SOURCE_COLUMNS], seeded_registry[SOURCE_COLUMNS]],
            ignore_index=True,
        ).drop_duplicates("source_record_id", keep="first")
    else:
        registry = seeded_registry

    write_csv_atomic(queue, QUEUE_FILE, QUEUE_COLUMNS)
    write_csv_atomic(registry, SOURCE_REGISTRY_FILE, SOURCE_COLUMNS)

    summary = {
        "phase": "14B_ACQUISITION_BOOTSTRAP",
        "status": "SUCCESS",
        "run_at": utc_now(),
        "started_at": started,
        "acquisition_version": ACQUISITION_VERSION,
        "queue_rows": int(len(queue)),
        "companies_requiring_source_research": int((queue["source_research_status"] == "SOURCE_RESEARCH_REQUIRED").sum()) if not queue.empty else 0,
        "companies_with_existing_source_for_review": int((queue["source_research_status"] == "EXISTING_SOURCE_AVAILABLE_FOR_REVIEW").sum()) if not queue.empty else 0,
        "seeded_verified_source_records": int(len(registry)),
        "target_history_years": TARGET_HISTORY_YEARS,
        "guardrails": {
            "new_unverified_financial_values_added": False,
            "missing_years_synthesized": False,
            "parent_financials_promoted_to_project_company_without_scope_evidence": False,
            "project_investment_treated_as_bank_exposure_or_ead": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
        "outputs": [
            str(QUEUE_FILE.relative_to(ROOT)),
            str(SOURCE_REGISTRY_FILE.relative_to(ROOT)),
        ],
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14B - FINANCIAL ACQUISITION BOOTSTRAP")
    print("=" * 72)
    print(f"Acquisition queue rows                 : {summary['queue_rows']}")
    print(f"Companies requiring source research   : {summary['companies_requiring_source_research']}")
    print(f"Existing sources available for review : {summary['companies_with_existing_source_for_review']}")
    print(f"Seeded verified source records         : {summary['seeded_verified_source_records']}")
    print(f"Target longitudinal history            : {TARGET_HISTORY_YEARS} verified annual periods where available")
    print()
    print(f"Acquisition queue                      : {QUEUE_FILE.relative_to(ROOT)}")
    print(f"Source registry                        : {SOURCE_REGISTRY_FILE.relative_to(ROOT)}")
    print()
    print("No new financial fact has been invented. Source research and human scope verification remain mandatory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
