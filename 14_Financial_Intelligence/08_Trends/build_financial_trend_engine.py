from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
RATIO_FILE = PHASE_DIR / "07_Ratios" / "Company_Financial_Ratios_Wide.csv"
DEFINITIONS_FILE = PHASE_DIR / "08_Trends" / "trend_definitions.json"
OUT_DIR = PHASE_DIR / "08_Trends"
TREND_OUT = OUT_DIR / "Company_Financial_Trend_Observations.csv"
SUMMARY_OUT = OUT_DIR / "Company_Financial_Trend_Summary.csv"
SIGNAL_OUT = OUT_DIR / "Financial_Early_Warning_Signals.csv"
RUN_LOG = OUT_DIR / "Phase_14D_Trend_Run_Log.jsonl"

ENGINE_VERSION = "SCI_FINANCIAL_TREND_ENGINE_V1"
COMPARABILITY_COLUMNS = ["financial_entity_id", "entity_scope", "currency", "unit"]

YOY_AMOUNT_FIELDS = [
    "revenue",
    "pat",
    "total_debt",
    "operating_cash_flow",
    "total_assets",
    "total_equity",
]

RATIO_CHANGE_FIELDS = [
    "net_profit_margin",
    "ocf_margin",
    "debt_to_equity",
    "current_ratio",
    "return_on_assets_ending",
    "return_on_equity_ending",
]

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


def pct_change(current, previous):
    current = num(current)
    previous = num(previous)
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def absolute_change(current, previous):
    current = num(current)
    previous = num(previous)
    if current is None or previous is None:
        return None
    return current - previous


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


def parse_year_end(row: pd.Series) -> pd.Timestamp:
    raw = clean(row.get("financial_year_end"))
    if raw:
        parsed = pd.to_datetime(raw, errors="coerce")
        if pd.notna(parsed):
            return parsed

    fy = clean(row.get("financial_year"))
    digits = "".join(ch for ch in fy if ch.isdigit())
    if len(digits) >= 4:
        # Sorting fallback only. No accounting date is fabricated into the source master.
        year = int(digits[-4:])
        return pd.Timestamp(year=year, month=12, day=31)
    return pd.NaT


def cagr(first_value, last_value, first_date: pd.Timestamp, last_date: pd.Timestamp):
    first_value = num(first_value)
    last_value = num(last_value)
    if first_value is None or last_value is None or first_value <= 0 or last_value <= 0:
        return None
    if pd.isna(first_date) or pd.isna(last_date) or last_date <= first_date:
        return None
    years = (last_date - first_date).days / 365.25
    if years <= 0:
        return None
    return (last_value / first_value) ** (1.0 / years) - 1.0


def classify_cycle(revenue_yoy, npm_change, ocf_margin_change):
    vals = [revenue_yoy, npm_change]
    if any(v is None for v in vals):
        return "INSUFFICIENT_COMPARABLE_HISTORY"

    if revenue_yoy > 0 and npm_change > 0:
        if ocf_margin_change is not None and ocf_margin_change >= 0:
            return "EXPANSION_WITH_PROFIT_AND_CASHFLOW_IMPROVEMENT"
        return "EXPANSION_WITH_PROFITABILITY_IMPROVEMENT"
    if revenue_yoy > 0 and npm_change < 0:
        return "REVENUE_GROWTH_WITH_MARGIN_PRESSURE"
    if revenue_yoy < 0 and npm_change < 0:
        return "CONTRACTION_WITH_MARGIN_PRESSURE"
    if revenue_yoy < 0 and npm_change >= 0:
        return "CONTRACTION_WITH_MARGIN_RESILIENCE"
    return "MIXED_OR_FLAT"


def build_signal_flags(row: dict, thresholds: dict):
    deterioration = []
    strengthening = []
    signal_rows = []

    def test(metric: str, value, deterioration_rule, strengthening_rule, deterioration_threshold, strengthening_threshold):
        if value is None:
            return
        if deterioration_rule(value, deterioration_threshold):
            deterioration.append(metric)
            signal_rows.append((metric, "DETERIORATION", value, deterioration_threshold))
        if strengthening_rule(value, strengthening_threshold):
            strengthening.append(metric)
            signal_rows.append((metric, "STRENGTHENING", value, strengthening_threshold))

    test(
        "revenue_yoy",
        row.get("revenue_yoy"),
        lambda v, t: v <= t,
        lambda v, t: v >= t,
        thresholds["revenue_yoy_deterioration"],
        thresholds["revenue_yoy_strengthening"],
    )
    test(
        "net_profit_margin_change",
        row.get("net_profit_margin_change"),
        lambda v, t: v <= t,
        lambda v, t: v >= t,
        thresholds["net_profit_margin_change_deterioration"],
        thresholds["net_profit_margin_change_strengthening"],
    )
    test(
        "ocf_margin_change",
        row.get("ocf_margin_change"),
        lambda v, t: v <= t,
        lambda v, t: v >= t,
        thresholds["ocf_margin_change_deterioration"],
        thresholds["ocf_margin_change_strengthening"],
    )
    test(
        "debt_to_equity_change",
        row.get("debt_to_equity_change"),
        lambda v, t: v >= t,
        lambda v, t: v <= t,
        thresholds["debt_to_equity_change_deterioration"],
        thresholds["debt_to_equity_change_strengthening"],
    )
    test(
        "current_ratio_change",
        row.get("current_ratio_change"),
        lambda v, t: v <= t,
        lambda v, t: v >= t,
        thresholds["current_ratio_change_deterioration"],
        thresholds["current_ratio_change_strengthening"],
    )
    test(
        "return_on_assets_ending_change",
        row.get("return_on_assets_ending_change"),
        lambda v, t: v <= t,
        lambda v, t: v >= t,
        thresholds["roa_change_deterioration"],
        thresholds["roa_change_strengthening"],
    )

    # Sign-change warnings use accounting facts directly and do not require arbitrary ratio thresholds.
    prev_pat = row.get("previous_pat")
    curr_pat = row.get("pat")
    if prev_pat is not None and curr_pat is not None:
        if prev_pat >= 0 and curr_pat < 0:
            deterioration.append("pat_positive_to_negative")
            signal_rows.append(("pat_sign_change", "DETERIORATION", curr_pat, 0.0))
        elif prev_pat < 0 and curr_pat >= 0:
            strengthening.append("pat_negative_to_nonnegative")
            signal_rows.append(("pat_sign_change", "STRENGTHENING", curr_pat, 0.0))

    prev_ocf = row.get("previous_operating_cash_flow")
    curr_ocf = row.get("operating_cash_flow")
    if prev_ocf is not None and curr_ocf is not None:
        if prev_ocf >= 0 and curr_ocf < 0:
            deterioration.append("ocf_positive_to_negative")
            signal_rows.append(("ocf_sign_change", "DETERIORATION", curr_ocf, 0.0))
        elif prev_ocf < 0 and curr_ocf >= 0:
            strengthening.append("ocf_negative_to_nonnegative")
            signal_rows.append(("ocf_sign_change", "STRENGTHENING", curr_ocf, 0.0))

    return deterioration, strengthening, signal_rows


def aggregate_signal(deterioration_count: int, strengthening_count: int, policy: dict) -> str:
    d_cut = int(policy.get("deterioration_signal_count", 3))
    s_cut = int(policy.get("strengthening_signal_count", 3))

    if deterioration_count >= d_cut and strengthening_count >= s_cut:
        return "MIXED_HIGH_SIGNAL"
    if deterioration_count >= d_cut:
        return "FINANCIAL_DETERIORATION_SIGNAL"
    if strengthening_count >= s_cut:
        return "FINANCIAL_STRENGTHENING_SIGNAL"
    if deterioration_count and strengthening_count:
        return "MIXED_FINANCIAL_SIGNALS"
    if deterioration_count:
        return "LIMITED_DETERIORATION_INDICATORS"
    if strengthening_count:
        return "LIMITED_STRENGTHENING_INDICATORS"
    return "NO_THRESHOLD_SIGNAL_OR_INSUFFICIENT_DATA"


def build_trends(ratios: pd.DataFrame, definitions: dict):
    thresholds = definitions["research_signal_thresholds"]
    policy = definitions["signal_policy"]

    working = ratios.copy()
    for col in COMPARABILITY_COLUMNS:
        if col not in working.columns:
            raise RuntimeError(f"Ratio output missing comparability column: {col}")

    working["_sort_date"] = working.apply(parse_year_end, axis=1)
    trend_rows = []
    signal_rows = []

    for key, group in working.groupby(COMPARABILITY_COLUMNS, dropna=False, sort=True):
        group = group.sort_values(["_sort_date", "financial_year"], na_position="last").reset_index(drop=True)

        for idx, current in group.iterrows():
            base = {col: current.get(col, pd.NA) for col in BASE_COLUMNS if col in current.index}
            record = dict(base)
            record.update({
                "trend_engine_version": ENGINE_VERSION,
                "comparable_group_observations": int(len(group)),
                "previous_observation_id": "",
                "previous_financial_year": "",
                "period_gap_days": pd.NA,
            })

            for field in YOY_AMOUNT_FIELDS:
                record[field] = num(current.get(field))
                record[f"previous_{field}"] = None
                record[f"{field}_yoy"] = None
            for field in RATIO_CHANGE_FIELDS:
                record[field] = num(current.get(field))
                record[f"previous_{field}"] = None
                record[f"{field}_change"] = None

            if idx > 0:
                previous = group.iloc[idx - 1]
                record["previous_observation_id"] = clean(previous.get("observation_id"))
                record["previous_financial_year"] = clean(previous.get("financial_year"))
                current_date = current.get("_sort_date")
                previous_date = previous.get("_sort_date")
                if pd.notna(current_date) and pd.notna(previous_date):
                    record["period_gap_days"] = int((current_date - previous_date).days)

                for field in YOY_AMOUNT_FIELDS:
                    record[f"previous_{field}"] = num(previous.get(field))
                    record[f"{field}_yoy"] = pct_change(current.get(field), previous.get(field))
                for field in RATIO_CHANGE_FIELDS:
                    record[f"previous_{field}"] = num(previous.get(field))
                    record[f"{field}_change"] = absolute_change(current.get(field), previous.get(field))

            deterioration, strengthening, detailed = build_signal_flags(record, thresholds)
            record["deterioration_signal_count"] = len(deterioration)
            record["strengthening_signal_count"] = len(strengthening)
            record["deterioration_flags"] = ";".join(deterioration)
            record["strengthening_flags"] = ";".join(strengthening)
            record["financial_trend_signal"] = aggregate_signal(len(deterioration), len(strengthening), policy)
            record["cycle_pattern"] = classify_cycle(
                record.get("revenue_yoy"),
                record.get("net_profit_margin_change"),
                record.get("ocf_margin_change"),
            )
            record["trend_scope_note"] = (
                "PARENT_OR_GROUP_CONTEXT_ONLY"
                if clean(current.get("entity_scope")) in {"PARENT_LEVEL", "CONSOLIDATED_GROUP_LEVEL"}
                else "ENTITY_SCOPE_PRESERVED"
            )
            trend_rows.append(record)

            for metric, direction, value, threshold in detailed:
                signal_rows.append({
                    "observation_id": clean(current.get("observation_id")),
                    "project_company_name": clean(current.get("project_company_name")),
                    "financial_entity_id": clean(current.get("financial_entity_id")),
                    "financial_entity_name": clean(current.get("financial_entity_name")),
                    "entity_scope": clean(current.get("entity_scope")),
                    "financial_year": clean(current.get("financial_year")),
                    "currency": clean(current.get("currency")),
                    "unit": clean(current.get("unit")),
                    "signal_metric": metric,
                    "signal_direction": direction,
                    "observed_change_or_value": value,
                    "research_threshold": threshold,
                    "signal_status": "RESEARCH_EARLY_WARNING_INDICATOR",
                    "threshold_status": policy.get("threshold_status", "RESEARCH_HEURISTIC"),
                    "engine_version": ENGINE_VERSION,
                })

    return pd.DataFrame(trend_rows), pd.DataFrame(signal_rows)


def build_summary(trends: pd.DataFrame) -> pd.DataFrame:
    if trends.empty:
        return pd.DataFrame()

    temp = trends.copy()
    temp["_sort_date"] = temp.apply(parse_year_end, axis=1)
    rows = []

    for key, group in temp.groupby(COMPARABILITY_COLUMNS, dropna=False, sort=True):
        group = group.sort_values(["_sort_date", "financial_year"], na_position="last").reset_index(drop=True)
        first = group.iloc[0]
        latest = group.iloc[-1]

        revenue_valid = group[group["revenue"].notna()].copy() if "revenue" in group.columns else pd.DataFrame()
        revenue_cagr = None
        if len(revenue_valid) >= 3:
            first_rev = revenue_valid.iloc[0]
            last_rev = revenue_valid.iloc[-1]
            revenue_cagr = cagr(
                first_rev.get("revenue"),
                last_rev.get("revenue"),
                parse_year_end(first_rev),
                parse_year_end(last_rev),
            )

        revenue_growth = pd.to_numeric(group.get("revenue_yoy"), errors="coerce").dropna()
        npm = pd.to_numeric(group.get("net_profit_margin"), errors="coerce").dropna()
        ocf_margin = pd.to_numeric(group.get("ocf_margin"), errors="coerce").dropna()

        rows.append({
            "project_company_id": clean(latest.get("project_company_id")),
            "project_company_name": clean(latest.get("project_company_name")),
            "financial_entity_id": clean(latest.get("financial_entity_id")),
            "financial_entity_name": clean(latest.get("financial_entity_name")),
            "entity_scope": clean(latest.get("entity_scope")),
            "currency": clean(latest.get("currency")),
            "unit": clean(latest.get("unit")),
            "observations": int(len(group)),
            "first_financial_year": clean(first.get("financial_year")),
            "latest_financial_year": clean(latest.get("financial_year")),
            "revenue_cagr_available": revenue_cagr is not None,
            "revenue_cagr": revenue_cagr,
            "revenue_yoy_volatility": float(revenue_growth.std(ddof=1)) if len(revenue_growth) >= 3 else pd.NA,
            "net_profit_margin_volatility": float(npm.std(ddof=1)) if len(npm) >= 3 else pd.NA,
            "ocf_margin_volatility": float(ocf_margin.std(ddof=1)) if len(ocf_margin) >= 3 else pd.NA,
            "latest_revenue_yoy": latest.get("revenue_yoy", pd.NA),
            "latest_net_profit_margin_change": latest.get("net_profit_margin_change", pd.NA),
            "latest_ocf_margin_change": latest.get("ocf_margin_change", pd.NA),
            "latest_debt_to_equity_change": latest.get("debt_to_equity_change", pd.NA),
            "latest_current_ratio_change": latest.get("current_ratio_change", pd.NA),
            "latest_deterioration_signal_count": int(latest.get("deterioration_signal_count", 0)),
            "latest_strengthening_signal_count": int(latest.get("strengthening_signal_count", 0)),
            "latest_financial_trend_signal": clean(latest.get("financial_trend_signal")),
            "latest_cycle_pattern": clean(latest.get("cycle_pattern")),
            "latest_deterioration_flags": clean(latest.get("deterioration_flags")),
            "latest_strengthening_flags": clean(latest.get("strengthening_flags")),
            "trend_scope_note": clean(latest.get("trend_scope_note")),
            "engine_version": ENGINE_VERSION,
        })

    return pd.DataFrame(rows)


def main() -> int:
    definitions = json.loads(DEFINITIONS_FILE.read_text(encoding="utf-8"))
    if definitions.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError(
            f"Trend-definition version mismatch: {definitions.get('engine_version')} != {ENGINE_VERSION}"
        )

    ratios = read_csv(RATIO_FILE)
    if ratios.empty:
        raise RuntimeError(
            "Phase 14C ratio output is empty or missing. Run build_financial_ratio_engine.py before Phase 14D."
        )

    missing = [c for c in ["observation_id", *COMPARABILITY_COLUMNS, "financial_year"] if c not in ratios.columns]
    if missing:
        raise RuntimeError(f"Phase 14C ratio output missing required columns: {missing}")

    trends, signals = build_trends(ratios, definitions)
    summary = build_summary(trends)

    atomic_write(trends, TREND_OUT)
    atomic_write(summary, SUMMARY_OUT)
    atomic_write(signals, SIGNAL_OUT)

    comparable_groups = int(trends.groupby(COMPARABILITY_COLUMNS, dropna=False).ngroups) if not trends.empty else 0
    groups_with_history = int((summary["observations"] >= 2).sum()) if not summary.empty else 0
    deterioration_latest = int(summary["latest_financial_trend_signal"].eq("FINANCIAL_DETERIORATION_SIGNAL").sum()) if not summary.empty else 0
    strengthening_latest = int(summary["latest_financial_trend_signal"].eq("FINANCIAL_STRENGTHENING_SIGNAL").sum()) if not summary.empty else 0

    run_summary = {
        "phase": "14D",
        "run_at": utc_now(),
        "status": "SUCCESS_FINANCIAL_TREND_ENGINE",
        "engine_version": ENGINE_VERSION,
        "financial_observations": int(len(trends)),
        "comparable_groups": comparable_groups,
        "groups_with_at_least_two_periods": groups_with_history,
        "early_warning_signal_rows": int(len(signals)),
        "latest_deterioration_signals": deterioration_latest,
        "latest_strengthening_signals": strengthening_latest,
        "outputs": [
            str(TREND_OUT.relative_to(ROOT)),
            str(SUMMARY_OUT.relative_to(ROOT)),
            str(SIGNAL_OUT.relative_to(ROOT)),
        ],
        "guardrails": {
            "cross_currency_or_cross_unit_trends_performed": False,
            "different_entity_scopes_blended": False,
            "missing_values_imputed": False,
            "parent_or_group_financials_recast_as_project_financials": False,
            "signals_are_credit_ratings": False,
            "pd_lgd_ead_ecl_generated": False,
            "automatic_credit_decision_generated": False,
        },
    }
    append_jsonl(RUN_LOG, run_summary)

    print("PHASE 14D - FINANCIAL TREND & EARLY-WARNING ENGINE")
    print("=" * 72)
    print(f"Financial observations           : {run_summary['financial_observations']}")
    print(f"Comparable entity/scope groups   : {run_summary['comparable_groups']}")
    print(f"Groups with >=2 periods          : {run_summary['groups_with_at_least_two_periods']}")
    print(f"Signal detail rows               : {run_summary['early_warning_signal_rows']}")
    print(f"Latest deterioration signals     : {run_summary['latest_deterioration_signals']}")
    print(f"Latest strengthening signals     : {run_summary['latest_strengthening_signals']}")
    print(f"Trend observations               : {TREND_OUT.relative_to(ROOT)}")
    print(f"Entity trend summary             : {SUMMARY_OUT.relative_to(ROOT)}")
    print(f"Early-warning details            : {SIGNAL_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: trend flags are transparent research heuristics, not regulatory cutoffs, credit ratings, PD/LGD/EAD/ECL or automated lending decisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
