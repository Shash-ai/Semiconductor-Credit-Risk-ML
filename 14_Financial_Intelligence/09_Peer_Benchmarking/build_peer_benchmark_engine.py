from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
PROJECT_RATIO_FILE = PHASE_DIR / "07_Ratios" / "Company_Financial_Ratios_Wide.csv"
EXTERNAL_RATIO_FILE = PHASE_DIR / "09_Peer_Benchmarking" / "External_Peer_Financials" / "External_Peer_Financial_Ratios_Wide.csv"
REGISTRY_FILE = PHASE_DIR / "09_Peer_Benchmarking" / "peer_group_registry.csv"
CONFIG_FILE = PHASE_DIR / "09_Peer_Benchmarking" / "peer_benchmark_config.json"
OUT_DIR = PHASE_DIR / "09_Peer_Benchmarking"
LATEST_OUT = OUT_DIR / "Peer_Group_Latest_Observations.csv"
RESULT_OUT = OUT_DIR / "Peer_Benchmark_Results.csv"
READINESS_OUT = OUT_DIR / "Peer_Benchmark_Readiness.csv"
RUN_LOG = OUT_DIR / "Phase_14E_Peer_Benchmark_Run_Log.jsonl"

ENGINE_VERSION = "SCI_PEER_BENCHMARK_ENGINE_V2"


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


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def year_sort_key(row: pd.Series) -> tuple:
    date = pd.to_datetime(row.get("financial_year_end"), errors="coerce")
    if pd.notna(date):
        return (1, date)
    text = clean(row.get("financial_year"))
    digits = "".join(ch for ch in text if ch.isdigit())
    year = int(digits[-4:]) if len(digits) >= 4 else -1
    return (0, year)


def scope_class(scope: str, mapping: dict) -> str:
    return clean(mapping.get(clean(scope), "UNMAPPED"))


def load_ratio_universe() -> pd.DataFrame:
    frames = []
    project = read_csv(PROJECT_RATIO_FILE)
    if not project.empty:
        project = project.copy()
        project["peer_ratio_source_dataset"] = "PROJECT_FINANCIAL_RATIO_MASTER"
        frames.append(project)

    external = read_csv(EXTERNAL_RATIO_FILE)
    if not external.empty:
        external = external.copy()
        external["peer_ratio_source_dataset"] = "EXTERNAL_AUDITED_PEER_RATIO_MASTER"
        frames.append(external)

    if not frames:
        return pd.DataFrame()
    all_columns = list(dict.fromkeys(col for frame in frames for col in frame.columns))
    return pd.concat([frame.reindex(columns=all_columns) for frame in frames], ignore_index=True)


def select_ratio_rows(ratios: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, reg in registry.iterrows():
        peer_group_id = clean(reg.get("peer_group_id"))
        entity_id = clean(reg.get("financial_entity_id"))
        requested_year = clean(reg.get("benchmark_financial_year"))
        candidates = ratios[ratios["financial_entity_id"].astype(str).eq(entity_id)].copy()

        if requested_year:
            candidates = candidates[candidates["financial_year"].astype(str).eq(requested_year)].copy()
            selection_status = "EXACT_BENCHMARK_PERIOD_MATCH" if not candidates.empty else "REQUESTED_BENCHMARK_PERIOD_UNAVAILABLE"
        else:
            selection_status = "LATEST_OBSERVATION_FALLBACK" if not candidates.empty else "NO_RATIO_OBSERVATION_AVAILABLE"

        if candidates.empty:
            continue

        ordered = sorted((row for _, row in candidates.iterrows()), key=year_sort_key)
        chosen = ordered[-1].copy()
        chosen["_selection_peer_group_id"] = peer_group_id
        chosen["_requested_benchmark_financial_year"] = requested_year
        chosen["_period_selection_status"] = selection_status
        rows.append(chosen)

    if not rows:
        cols = list(ratios.columns) + [
            "_selection_peer_group_id", "_requested_benchmark_financial_year", "_period_selection_status"
        ]
        return pd.DataFrame(columns=list(dict.fromkeys(cols)))
    return pd.DataFrame(rows).reset_index(drop=True)


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("engine_version") != ENGINE_VERSION:
        raise RuntimeError(f"Peer benchmark config mismatch: {config.get('engine_version')} != {ENGINE_VERSION}")

    ratios = load_ratio_universe()
    registry = read_csv(REGISTRY_FILE)
    if ratios.empty:
        raise RuntimeError("No ratio universe is available. Run Phase 14C and the external-peer ratio builder first.")
    if registry.empty:
        raise RuntimeError("Peer-group registry is empty or missing.")

    required_ratio_cols = {"financial_entity_id", "financial_entity_name", "entity_scope", "financial_year"}
    missing = required_ratio_cols - set(ratios.columns)
    if missing:
        raise RuntimeError(f"Ratio universe missing required columns: {sorted(missing)}")

    required_registry_cols = {
        "peer_group_id", "peer_group_name", "financial_entity_id", "financial_entity_name",
        "entity_scope_class", "benchmark_role", "benchmark_financial_year", "peer_group_status",
    }
    missing = required_registry_cols - set(registry.columns)
    if missing:
        raise RuntimeError(f"Peer registry missing required columns: {sorted(missing)}")

    scope_mapping = config.get("scope_class_mapping", {})
    metrics = config.get("metrics", {})
    min_peers = int(config.get("minimum_peer_count_for_percentiles", 3))

    selected = select_ratio_rows(ratios, registry)
    selected["derived_entity_scope_class"] = selected.get("entity_scope", pd.Series(dtype=str)).astype(str).map(
        lambda x: scope_class(x, scope_mapping)
    )

    merged = registry.merge(
        selected,
        left_on=["peer_group_id", "financial_entity_id"],
        right_on=["_selection_peer_group_id", "financial_entity_id"],
        how="left",
        suffixes=("_registry", "_ratio"),
    )

    ratio_name_col = "financial_entity_name_ratio" if "financial_entity_name_ratio" in merged.columns else "financial_entity_name"
    registry_name_col = "financial_entity_name_registry" if "financial_entity_name_registry" in merged.columns else "financial_entity_name"
    merged["entity_name_match"] = (
        merged[registry_name_col].astype(str).str.strip() == merged[ratio_name_col].astype(str).str.strip()
    )
    merged["scope_class_match"] = (
        merged["entity_scope_class"].astype(str).str.strip()
        == merged.get("derived_entity_scope_class", pd.Series(index=merged.index, dtype=object)).astype(str).str.strip()
    )
    merged["ratio_observation_available"] = merged.get("observation_id", pd.Series(index=merged.index, dtype=object)).notna()
    merged["period_match"] = (
        merged["benchmark_financial_year"].fillna("").astype(str).str.strip().eq("")
        | merged.get("financial_year", pd.Series(index=merged.index, dtype=object)).astype(str).eq(
            merged["benchmark_financial_year"].astype(str)
        )
    )
    merged["eligible_for_peer_benchmark"] = (
        merged["ratio_observation_available"]
        & merged["entity_name_match"]
        & merged["scope_class_match"]
        & merged["period_match"]
    )
    merged["peer_engine_version"] = ENGINE_VERSION
    merged["evaluated_at"] = utc_now()
    atomic_write(merged, LATEST_OUT)

    result_rows = []
    readiness_rows = []

    for peer_group_id, group_registry in registry.groupby("peer_group_id", sort=True):
        group_name = clean(group_registry.iloc[0].get("peer_group_name"))
        group_latest = merged[merged["peer_group_id"].astype(str).eq(str(peer_group_id))].copy()
        eligible = group_latest[group_latest["eligible_for_peer_benchmark"].astype(bool)].copy()

        metric_peer_counts = []
        percentile_ready_metrics = 0
        for metric_name, meta in metrics.items():
            category = clean(meta.get("category"))
            direction = clean(meta.get("direction"))
            values = pd.to_numeric(eligible.get(metric_name, pd.Series(index=eligible.index, dtype=float)), errors="coerce")
            valid_mask = values.notna()
            valid = eligible.loc[valid_mask].copy()
            valid_values = values.loc[valid_mask].astype(float)
            n = int(len(valid))
            metric_peer_counts.append(n)

            if n >= min_peers:
                percentile_ready_metrics += 1
                q25 = float(valid_values.quantile(0.25))
                median = float(valid_values.median())
                q75 = float(valid_values.quantile(0.75))
                mean = float(valid_values.mean())
                if direction == "LOWER_IS_STRONGER":
                    strength_percentile = valid_values.rank(method="average", pct=True, ascending=False)
                else:
                    strength_percentile = valid_values.rank(method="average", pct=True, ascending=True)

                for idx, row in valid.iterrows():
                    value = float(pd.to_numeric(row.get(metric_name), errors="coerce"))
                    result_rows.append({
                        "peer_group_id": peer_group_id,
                        "peer_group_name": group_name,
                        "benchmark_financial_year": clean(row.get("benchmark_financial_year")),
                        "financial_entity_id": clean(row.get("financial_entity_id")),
                        "financial_entity_name": clean(row.get(ratio_name_col)) or clean(row.get(registry_name_col)),
                        "entity_scope": clean(row.get("entity_scope")),
                        "financial_year": clean(row.get("financial_year")),
                        "peer_ratio_source_dataset": clean(row.get("peer_ratio_source_dataset")),
                        "metric_name": metric_name,
                        "metric_category": category,
                        "metric_direction": direction,
                        "metric_value": value,
                        "peer_count": n,
                        "peer_q25": q25,
                        "peer_median": median,
                        "peer_q75": q75,
                        "peer_mean": mean,
                        "strength_percentile": float(strength_percentile.loc[idx]),
                        "benchmark_status": "PERCENTILE_CALCULATED",
                        "engine_version": ENGINE_VERSION,
                    })
            else:
                for _, row in valid.iterrows():
                    value = pd.to_numeric(row.get(metric_name), errors="coerce")
                    if pd.isna(value):
                        continue
                    result_rows.append({
                        "peer_group_id": peer_group_id,
                        "peer_group_name": group_name,
                        "benchmark_financial_year": clean(row.get("benchmark_financial_year")),
                        "financial_entity_id": clean(row.get("financial_entity_id")),
                        "financial_entity_name": clean(row.get(ratio_name_col)) or clean(row.get(registry_name_col)),
                        "entity_scope": clean(row.get("entity_scope")),
                        "financial_year": clean(row.get("financial_year")),
                        "peer_ratio_source_dataset": clean(row.get("peer_ratio_source_dataset")),
                        "metric_name": metric_name,
                        "metric_category": category,
                        "metric_direction": direction,
                        "metric_value": float(value),
                        "peer_count": n,
                        "peer_q25": pd.NA,
                        "peer_median": pd.NA,
                        "peer_q75": pd.NA,
                        "peer_mean": pd.NA,
                        "strength_percentile": pd.NA,
                        "benchmark_status": "INSUFFICIENT_PEER_COUNT",
                        "engine_version": ENGINE_VERSION,
                    })

        matched_members = int(group_latest["eligible_for_peer_benchmark"].sum())
        registered_members = int(len(group_latest))
        period_mismatches = int((group_latest["ratio_observation_available"] & ~group_latest["period_match"]).sum())
        readiness_status = "READY_FOR_PEER_PERCENTILES" if percentile_ready_metrics > 0 else "EXPAND_OR_ALIGN_PEER_UNIVERSE_REQUIRED"
        readiness_rows.append({
            "peer_group_id": peer_group_id,
            "peer_group_name": group_name,
            "benchmark_financial_year": ";".join(sorted(set(group_registry["benchmark_financial_year"].astype(str)))),
            "registered_members": registered_members,
            "matched_period_aligned_ratio_members": matched_members,
            "period_mismatches": period_mismatches,
            "minimum_peer_count": min_peers,
            "metrics_configured": len(metrics),
            "metrics_ready_for_percentiles": percentile_ready_metrics,
            "minimum_available_metric_peer_count": min(metric_peer_counts) if metric_peer_counts else 0,
            "maximum_available_metric_peer_count": max(metric_peer_counts) if metric_peer_counts else 0,
            "peer_group_readiness": readiness_status,
            "registry_status": ";".join(sorted(set(group_registry["peer_group_status"].astype(str)))),
            "engine_version": ENGINE_VERSION,
        })

    results = pd.DataFrame(result_rows)
    readiness = pd.DataFrame(readiness_rows)
    atomic_write(results, RESULT_OUT)
    atomic_write(readiness, READINESS_OUT)

    percentile_rows = int((results.get("benchmark_status", pd.Series(dtype=str)) == "PERCENTILE_CALCULATED").sum()) if not results.empty else 0
    insufficient_rows = int((results.get("benchmark_status", pd.Series(dtype=str)) == "INSUFFICIENT_PEER_COUNT").sum()) if not results.empty else 0
    ready_groups = int((readiness.get("peer_group_readiness", pd.Series(dtype=str)) == "READY_FOR_PEER_PERCENTILES").sum()) if not readiness.empty else 0

    summary = {
        "phase": "14E",
        "run_at": utc_now(),
        "status": "SUCCESS_PEER_BENCHMARK_ENGINE" if ready_groups else "SUCCESS_PEER_ENGINE_WITH_INSUFFICIENT_OR_UNALIGNED_PEER_UNIVERSE",
        "engine_version": ENGINE_VERSION,
        "registered_peer_groups": int(registry["peer_group_id"].nunique()),
        "registered_entities": int(registry["financial_entity_id"].nunique()),
        "project_ratio_rows_available": int(len(read_csv(PROJECT_RATIO_FILE))),
        "external_ratio_rows_available": int(len(read_csv(EXTERNAL_RATIO_FILE))),
        "ready_peer_groups": ready_groups,
        "percentile_result_rows": percentile_rows,
        "insufficient_peer_result_rows": insufficient_rows,
        "minimum_peer_count": min_peers,
        "guardrails": config.get("guardrails", {}),
        "outputs": [str(LATEST_OUT.relative_to(ROOT)), str(RESULT_OUT.relative_to(ROOT)), str(READINESS_OUT.relative_to(ROOT))],
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14E - PERIOD-ALIGNED PEER BENCHMARKING ENGINE")
    print("=" * 72)
    print(f"Registered peer groups           : {summary['registered_peer_groups']}")
    print(f"Registered entities              : {summary['registered_entities']}")
    print(f"External ratio rows              : {summary['external_ratio_rows_available']}")
    print(f"Minimum peers for percentiles    : {min_peers}")
    print(f"Peer groups ready                : {ready_groups}")
    print(f"Percentile result rows           : {percentile_rows}")
    print(f"Insufficient-peer rows           : {insufficient_rows}")
    print(f"Status                           : {summary['status']}")
    print(f"Readiness output                 : {READINESS_OUT.relative_to(ROOT)}")
    print(f"Benchmark output                 : {RESULT_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: peer comparisons are ratio-only, period-aligned and separate from structural ML clusters, credit ratings and lending decisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
