from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PEER_DIR = ROOT / "14_Financial_Intelligence" / "09_Peer_Benchmarking"
IN_DIR = PEER_DIR / "External_Peer_Financials"
INPUT_PATTERN = "External_Peer_Financial_Observations_*.csv"
RATIO_OUT = IN_DIR / "External_Peer_Financial_Ratios_Wide.csv"
VALIDATION_OUT = IN_DIR / "External_Peer_Financial_Validation_Report.csv"
RUN_LOG = IN_DIR / "Phase_14E2_External_Peer_Ratio_Run_Log.jsonl"

ENGINE_VERSION = "SCI_EXTERNAL_PEER_RATIO_ENGINE_V1"
REQUIRED_FIELDS = [
    "observation_id", "peer_group_id", "financial_entity_id", "financial_entity_name",
    "entity_scope", "financial_year", "financial_year_end", "currency", "unit",
    "audited", "source_type", "source_authority", "source_url", "verification_status",
    "revenue", "pat", "total_assets", "current_assets", "total_equity", "total_debt",
    "short_term_debt", "long_term_debt", "current_liabilities", "total_liabilities",
    "operating_cash_flow",
]
RATIO_FIELDS = [
    "net_profit_margin", "ocf_margin", "debt_to_equity", "debt_to_assets",
    "current_ratio", "ocf_to_debt", "return_on_assets_ending",
    "return_on_equity_ending", "asset_turnover_ending",
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


def num(value):
    if clean(value) == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def divide(a, b):
    if a is None or b is None or b <= 0:
        return None
    return a / b


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def add_check(checks: list[dict], row: pd.Series, name: str, passed: bool, detail: str) -> None:
    checks.append({
        "observation_id": clean(row.get("observation_id")),
        "financial_entity_name": clean(row.get("financial_entity_name")),
        "financial_year": clean(row.get("financial_year")),
        "check_name": name,
        "passed": bool(passed),
        "severity": "HARD",
        "detail": detail,
    })


def validate_row(row: pd.Series, checks: list[dict]) -> None:
    for field in REQUIRED_FIELDS:
        add_check(checks, row, f"required:{field}", bool(clean(row.get(field))), clean(row.get(field)))

    add_check(checks, row, "audited_yes", clean(row.get("audited")).upper() == "YES", clean(row.get("audited")))
    add_check(
        checks, row, "verified_external_peer_status",
        clean(row.get("verification_status")) == "PRIMARY_SOURCE_VERIFIED_EXTERNAL_PEER",
        clean(row.get("verification_status")),
    )
    add_check(
        checks, row, "corporate_group_scope",
        clean(row.get("entity_scope")) == "CONSOLIDATED_GROUP_LEVEL",
        clean(row.get("entity_scope")),
    )
    source_url = clean(row.get("source_url"))
    add_check(checks, row, "source_url_format", source_url.startswith("https://") or source_url.startswith("http://"), source_url)

    revenue = num(row.get("revenue"))
    pat = num(row.get("pat"))
    assets = num(row.get("total_assets"))
    current_assets = num(row.get("current_assets"))
    equity = num(row.get("total_equity"))
    debt = num(row.get("total_debt"))
    short_debt = num(row.get("short_term_debt"))
    long_debt = num(row.get("long_term_debt"))
    current_liabilities = num(row.get("current_liabilities"))
    liabilities = num(row.get("total_liabilities"))
    ocf = num(row.get("operating_cash_flow"))

    for field, value in {
        "revenue": revenue, "pat": pat, "total_assets": assets,
        "current_assets": current_assets, "total_equity": equity, "total_debt": debt,
        "short_term_debt": short_debt, "long_term_debt": long_debt,
        "current_liabilities": current_liabilities, "total_liabilities": liabilities,
        "operating_cash_flow": ocf,
    }.items():
        add_check(checks, row, f"numeric_parse:{field}", value is not None, clean(row.get(field)))

    if assets is not None and liabilities is not None and equity is not None:
        diff = abs(assets - (liabilities + equity))
        tol = max(1.0, abs(assets) * 0.001)
        add_check(checks, row, "balance_sheet_equation", diff <= tol, f"diff={diff}; tol={tol}")

    if debt is not None and short_debt is not None and long_debt is not None:
        diff = abs(debt - (short_debt + long_debt))
        tol = max(0.01, abs(debt) * 0.001)
        add_check(checks, row, "debt_reconciliation", diff <= tol, f"diff={diff}; tol={tol}")

    if assets is not None and current_assets is not None:
        add_check(checks, row, "current_assets_le_assets", current_assets <= assets, f"{current_assets} <= {assets}")
    if liabilities is not None and current_liabilities is not None:
        add_check(checks, row, "current_liabilities_le_liabilities", current_liabilities <= liabilities, f"{current_liabilities} <= {liabilities}")


def calculate_ratios(row: pd.Series) -> dict:
    revenue = num(row.get("revenue"))
    pat = num(row.get("pat"))
    assets = num(row.get("total_assets"))
    current_assets = num(row.get("current_assets"))
    equity = num(row.get("total_equity"))
    debt = num(row.get("total_debt"))
    current_liabilities = num(row.get("current_liabilities"))
    ocf = num(row.get("operating_cash_flow"))
    return {
        "net_profit_margin": divide(pat, revenue),
        "ocf_margin": divide(ocf, revenue),
        "debt_to_equity": divide(debt, equity),
        "debt_to_assets": divide(debt, assets),
        "current_ratio": divide(current_assets, current_liabilities),
        "ocf_to_debt": divide(ocf, debt),
        "return_on_assets_ending": divide(pat, assets),
        "return_on_equity_ending": divide(pat, equity),
        "asset_turnover_ending": divide(revenue, assets),
    }


def main() -> int:
    files = sorted(IN_DIR.glob(INPUT_PATTERN))
    if not files:
        raise RuntimeError(f"No external peer observation files found in {IN_DIR}")

    frames = []
    for path in files:
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if not df.empty:
            df["source_batch_file"] = path.name
            frames.append(df)
    if not frames:
        raise RuntimeError("External peer observation files contain no rows")

    observations = pd.concat(frames, ignore_index=True)
    if observations["observation_id"].astype(str).duplicated().any():
        raise RuntimeError("Duplicate external peer observation_id detected")

    checks: list[dict] = []
    for _, row in observations.iterrows():
        validate_row(row, checks)
    validation = pd.DataFrame(checks)
    hard_failures = validation[(validation["severity"] == "HARD") & (~validation["passed"].astype(bool))]
    atomic_write(validation, VALIDATION_OUT)
    if not hard_failures.empty:
        print("PHASE 14E.2 - EXTERNAL PEER FINANCIAL VALIDATION")
        print("=" * 72)
        print(f"External peer observations        : {len(observations)}")
        print(f"Validation hard failures          : {len(hard_failures)}")
        print(f"Validation report                 : {VALIDATION_OUT.relative_to(ROOT)}")
        return 1

    ratio_rows = []
    for _, row in observations.iterrows():
        base = row.to_dict()
        base.update(calculate_ratios(row))
        base["ratio_engine_version"] = ENGINE_VERSION
        base["ratio_scope_note"] = "EXTERNAL_AUDITED_CORPORATE_PEER_ONLY"
        base["ratio_calculated_at"] = utc_now()
        ratio_rows.append(base)
    ratios = pd.DataFrame(ratio_rows)
    atomic_write(ratios, RATIO_OUT)

    ratio_cells = len(ratios) * len(RATIO_FIELDS)
    calculated = sum(int(ratios[c].notna().sum()) for c in RATIO_FIELDS)
    summary = {
        "phase": "14E.2",
        "run_at": utc_now(),
        "status": "SUCCESS_EXTERNAL_PEER_RATIOS_VALIDATED",
        "engine_version": ENGINE_VERSION,
        "source_files": [p.name for p in files],
        "external_peer_observations": int(len(observations)),
        "validation_hard_failures": 0,
        "ratio_metrics": len(RATIO_FIELDS),
        "ratios_calculated": int(calculated),
        "possible_ratio_cells": int(ratio_cells),
        "guardrails": {
            "external_peers_added_to_project_company_master": False,
            "raw_monetary_amounts_compared_across_units": False,
            "missing_values_imputed": False,
            "peer_percentiles_treated_as_credit_ratings": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14E.2 - EXTERNAL PEER FINANCIAL RATIO DATASET")
    print("=" * 72)
    print(f"External peer observations        : {len(observations)}")
    print(f"Validation hard failures          : 0")
    print(f"Ratio metrics                     : {len(RATIO_FIELDS)}")
    print(f"Ratios calculated                 : {calculated} / {ratio_cells}")
    print(f"External peer ratio output        : {RATIO_OUT.relative_to(ROOT)}")
    print(f"Validation report                 : {VALIDATION_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: external peers remain separate from the semiconductor project-company financial master and are used only for audited corporate peer benchmarking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
