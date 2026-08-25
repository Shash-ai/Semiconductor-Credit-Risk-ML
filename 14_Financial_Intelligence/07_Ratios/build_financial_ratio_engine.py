from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
MASTER_FILE = PHASE_DIR / "03_Master" / "Company_Financials_Longitudinal.csv"
DEFINITIONS_FILE = PHASE_DIR / "07_Ratios" / "ratio_definitions.json"
OUT_DIR = PHASE_DIR / "07_Ratios"
WIDE_OUT = OUT_DIR / "Company_Financial_Ratios_Wide.csv"
LONG_OUT = OUT_DIR / "Company_Financial_Ratios_Long.csv"
COVERAGE_OUT = OUT_DIR / "Financial_Ratio_Coverage_Report.csv"
RUN_LOG = OUT_DIR / "Phase_14C_Ratio_Run_Log.jsonl"

ENGINE_VERSION = "SCI_FINANCIAL_RATIO_ENGINE_V1"

BASE_COLUMNS = [
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
    "source_type",
    "source_authority",
    "source_url",
    "verification_status",
    "observation_status",
]

RATIO_NAMES = [
    "ebitda_margin",
    "ebit_margin",
    "pre_tax_margin",
    "net_profit_margin",
    "ocf_margin",
    "debt_to_equity",
    "debt_to_assets",
    "debt_to_revenue",
    "net_debt_to_equity",
    "debt_to_ebitda",
    "current_ratio",
    "cash_ratio",
    "working_capital_to_revenue",
    "ocf_to_debt",
    "ocf_to_pat",
    "ocf_to_assets",
    "capex_intensity",
    "derived_fcf_margin",
    "ebit_interest_coverage",
    "ebitda_interest_coverage",
    "return_on_assets_ending",
    "return_on_equity_ending",
    "asset_turnover_ending",
    "equity_multiplier_ending",
    "dupont_roe_ending",
]

DERIVED_AMOUNT_NAMES = ["net_debt", "working_capital", "derived_free_cash_flow"]


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


def number(row: pd.Series, field: str):
    if field not in row.index:
        return None
    value = row.get(field)
    if clean(value) == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def divide(numerator, denominator, *, positive_denominator: bool = False):
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    if positive_denominator and denominator <= 0:
        return None
    return numerator / denominator


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def calculate_row(row: pd.Series) -> dict:
    revenue = number(row, "revenue")
    ebitda = number(row, "ebitda")
    ebit = number(row, "ebit")
    pbt = number(row, "pbt")
    pat = number(row, "pat")
    total_assets = number(row, "total_assets")
    current_assets = number(row, "current_assets")
    cash = number(row, "cash_and_equivalents")
    total_equity = number(row, "total_equity")
    total_debt = number(row, "total_debt")
    current_liabilities = number(row, "current_liabilities")
    interest_expense = number(row, "interest_expense")
    ocf = number(row, "operating_cash_flow")
    capex = number(row, "capex")

    net_debt = None if total_debt is None or cash is None else total_debt - cash
    working_capital = None if current_assets is None or current_liabilities is None else current_assets - current_liabilities
    derived_fcf = None if ocf is None or capex is None else ocf - abs(capex)

    ratios = {
        "ebitda_margin": divide(ebitda, revenue, positive_denominator=True),
        "ebit_margin": divide(ebit, revenue, positive_denominator=True),
        "pre_tax_margin": divide(pbt, revenue, positive_denominator=True),
        "net_profit_margin": divide(pat, revenue, positive_denominator=True),
        "ocf_margin": divide(ocf, revenue, positive_denominator=True),
        "debt_to_equity": divide(total_debt, total_equity, positive_denominator=True),
        "debt_to_assets": divide(total_debt, total_assets, positive_denominator=True),
        "debt_to_revenue": divide(total_debt, revenue, positive_denominator=True),
        "net_debt_to_equity": divide(net_debt, total_equity, positive_denominator=True),
        "debt_to_ebitda": divide(total_debt, ebitda, positive_denominator=True),
        "current_ratio": divide(current_assets, current_liabilities, positive_denominator=True),
        "cash_ratio": divide(cash, current_liabilities, positive_denominator=True),
        "working_capital_to_revenue": divide(working_capital, revenue, positive_denominator=True),
        "ocf_to_debt": divide(ocf, total_debt, positive_denominator=True),
        "ocf_to_pat": divide(ocf, pat),
        "ocf_to_assets": divide(ocf, total_assets, positive_denominator=True),
        "capex_intensity": divide(abs(capex) if capex is not None else None, revenue, positive_denominator=True),
        "derived_fcf_margin": divide(derived_fcf, revenue, positive_denominator=True),
        "ebit_interest_coverage": divide(ebit, interest_expense, positive_denominator=True),
        "ebitda_interest_coverage": divide(ebitda, interest_expense, positive_denominator=True),
        "return_on_assets_ending": divide(pat, total_assets, positive_denominator=True),
        "return_on_equity_ending": divide(pat, total_equity, positive_denominator=True),
        "asset_turnover_ending": divide(revenue, total_assets, positive_denominator=True),
        "equity_multiplier_ending": divide(total_assets, total_equity, positive_denominator=True),
    }

    if all(ratios.get(k) is not None for k in ["net_profit_margin", "asset_turnover_ending", "equity_multiplier_ending"]):
        ratios["dupont_roe_ending"] = (
            ratios["net_profit_margin"]
            * ratios["asset_turnover_ending"]
            * ratios["equity_multiplier_ending"]
        )
    else:
        ratios["dupont_roe_ending"] = None

    return {
        **ratios,
        "net_debt": net_debt,
        "working_capital": working_capital,
        "derived_free_cash_flow": derived_fcf,
    }


def build_long(wide: pd.DataFrame, definitions: dict) -> pd.DataFrame:
    rows = []
    ratio_defs = definitions.get("ratios", {})
    amount_defs = definitions.get("derived_amounts", {})

    for _, row in wide.iterrows():
        base = {col: row.get(col, pd.NA) for col in BASE_COLUMNS}
        for ratio_name in RATIO_NAMES:
            value = row.get(ratio_name, pd.NA)
            definition = ratio_defs.get(ratio_name, {})
            rows.append({
                **base,
                "metric_name": ratio_name,
                "metric_type": "RATIO",
                "metric_category": definition.get("category", ""),
                "metric_value": value,
                "metric_unit": definition.get("unit", "ratio"),
                "formula": definition.get("formula", ""),
                "calculation_status": "CALCULATED" if pd.notna(value) else "INSUFFICIENT_SOURCE_FIELDS",
                "engine_version": ENGINE_VERSION,
            })

        for amount_name in DERIVED_AMOUNT_NAMES:
            value = row.get(amount_name, pd.NA)
            rows.append({
                **base,
                "metric_name": amount_name,
                "metric_type": "DERIVED_AMOUNT",
                "metric_category": "derived_amount",
                "metric_value": value,
                "metric_unit": clean(row.get("unit")),
                "formula": amount_defs.get(amount_name, ""),
                "calculation_status": "CALCULATED" if pd.notna(value) else "INSUFFICIENT_SOURCE_FIELDS",
                "engine_version": ENGINE_VERSION,
            })

    return pd.DataFrame(rows)


def build_coverage(wide: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in wide.iterrows():
        available = sum(pd.notna(row.get(name)) for name in RATIO_NAMES)
        rows.append({
            "observation_id": clean(row.get("observation_id")),
            "project_company_name": clean(row.get("project_company_name")),
            "financial_entity_name": clean(row.get("financial_entity_name")),
            "entity_scope": clean(row.get("entity_scope")),
            "financial_year": clean(row.get("financial_year")),
            "currency": clean(row.get("currency")),
            "unit": clean(row.get("unit")),
            "ratios_available": int(available),
            "ratios_total": len(RATIO_NAMES),
            "ratio_coverage_pct": round(available / len(RATIO_NAMES) * 100.0, 2),
            "missing_ratios": ";".join(name for name in RATIO_NAMES if pd.isna(row.get(name))),
            "engine_version": ENGINE_VERSION,
        })
    return pd.DataFrame(rows)


def main() -> int:
    definitions = json.loads(DEFINITIONS_FILE.read_text(encoding="utf-8"))
    if definitions.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError(
            f"Ratio-definition version mismatch: {definitions.get('engine_version')} != {ENGINE_VERSION}"
        )

    master = read_csv(MASTER_FILE)
    if master.empty:
        raise RuntimeError(
            "Longitudinal financial master is empty. Promote verified Phase 14B observations before running Phase 14C."
        )

    missing_base = [c for c in ["observation_id", "financial_entity_id", "entity_scope", "financial_year"] if c not in master.columns]
    if missing_base:
        raise RuntimeError(f"Longitudinal master missing required columns: {missing_base}")

    wide = master.copy()
    calculations = wide.apply(calculate_row, axis=1, result_type="expand")
    for col in calculations.columns:
        wide[col] = calculations[col]

    wide["ratio_engine_version"] = ENGINE_VERSION
    wide["ratio_calculated_at"] = utc_now()
    wide["ratio_scope_note"] = wide.get("entity_scope", pd.Series(dtype=str)).astype(str).map(
        lambda scope: "PARENT_OR_GROUP_CONTEXT_ONLY" if scope in {"PARENT_LEVEL", "CONSOLIDATED_GROUP_LEVEL"} else "ENTITY_SCOPE_PRESERVED"
    )

    # We keep all master observations. Missing source fields yield missing ratios rather than imputation.
    long = build_long(wide, definitions)
    coverage = build_coverage(wide)

    atomic_write(wide, WIDE_OUT)
    atomic_write(long, LONG_OUT)
    atomic_write(coverage, COVERAGE_OUT)

    ratio_cells = int(len(wide) * len(RATIO_NAMES))
    ratios_calculated = int(sum(wide[name].notna().sum() for name in RATIO_NAMES))
    summary = {
        "phase": "14C",
        "run_at": utc_now(),
        "status": "SUCCESS_FINANCIAL_RATIO_ENGINE",
        "engine_version": ENGINE_VERSION,
        "financial_observations": int(len(wide)),
        "ratio_definitions": len(RATIO_NAMES),
        "possible_ratio_cells": ratio_cells,
        "ratios_calculated": ratios_calculated,
        "ratio_fill_pct": round((ratios_calculated / ratio_cells * 100.0), 2) if ratio_cells else 0.0,
        "outputs": [
            str(WIDE_OUT.relative_to(ROOT)),
            str(LONG_OUT.relative_to(ROOT)),
            str(COVERAGE_OUT.relative_to(ROOT)),
        ],
        "guardrails": {
            "source_accounting_facts_overwritten": False,
            "missing_values_imputed": False,
            "cross_currency_arithmetic_performed": False,
            "parent_financials_recast_as_project_financials": False,
            "credit_rating_generated": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14C - CORPORATE FINANCIAL RATIO ENGINE")
    print("=" * 72)
    print(f"Financial observations           : {summary['financial_observations']}")
    print(f"Ratio definitions                : {summary['ratio_definitions']}")
    print(f"Ratios calculated                : {summary['ratios_calculated']} / {summary['possible_ratio_cells']}")
    print(f"Ratio fill                       : {summary['ratio_fill_pct']:.2f}%")
    print(f"Wide output                      : {WIDE_OUT.relative_to(ROOT)}")
    print(f"Long output                      : {LONG_OUT.relative_to(ROOT)}")
    print(f"Coverage report                  : {COVERAGE_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: ratios are transparent corporate-finance analytics only; no PD/LGD/EAD/ECL, credit rating or automatic lending decision is generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
