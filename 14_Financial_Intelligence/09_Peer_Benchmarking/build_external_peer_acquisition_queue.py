from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "14_Financial_Intelligence"
PEER_DIR = PHASE_DIR / "09_Peer_Benchmarking"
CANDIDATE_FILE = PEER_DIR / "external_peer_candidate_registry.csv"
CONFIG_FILE = PEER_DIR / "peer_universe_acquisition_config.json"
ACTIVE_REGISTRY_FILE = PEER_DIR / "peer_group_registry.csv"
RATIO_FILE = PHASE_DIR / "07_Ratios" / "Company_Financial_Ratios_Wide.csv"
MASTER_FILE = PHASE_DIR / "03_Master" / "Company_Financials_Longitudinal.csv"
QUEUE_OUT = PEER_DIR / "External_Peer_Financial_Acquisition_Queue.csv"
READINESS_OUT = PEER_DIR / "External_Peer_Universe_Readiness.csv"
RUN_LOG = PEER_DIR / "Phase_14E1_Peer_Universe_Run_Log.jsonl"

VERSION = "SCI_EXTERNAL_PEER_UNIVERSE_V1"


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


def unique_names(df: pd.DataFrame, col: str) -> set[str]:
    if df.empty or col not in df.columns:
        return set()
    return {clean(v) for v in df[col].tolist() if clean(v)}


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("version") != VERSION:
        raise RuntimeError(f"Peer-universe config mismatch: {config.get('version')} != {VERSION}")

    candidates = read_csv(CANDIDATE_FILE)
    active = read_csv(ACTIVE_REGISTRY_FILE)
    ratios = read_csv(RATIO_FILE)
    master = read_csv(MASTER_FILE)

    if candidates.empty:
        raise RuntimeError("External peer candidate registry is empty")

    required = {
        "peer_group_id", "peer_group_name", "candidate_entity_name", "target_scope_class",
        "primary_source_type", "primary_source_authority", "primary_source_url",
        "source_discovery_status", "benchmark_activation_status"
    }
    missing = sorted(required - set(candidates.columns))
    if missing:
        raise RuntimeError(f"Candidate registry missing required columns: {missing}")

    allowed_source_status = set(config.get("source_statuses_allowed", []))
    allowed_activation_status = set(config.get("activation_statuses_allowed", []))

    active_names = unique_names(active, "financial_entity_name")
    ratio_names = unique_names(ratios, "financial_entity_name")
    master_names = unique_names(master, "financial_entity_name")

    queue_rows = []
    for _, row in candidates.iterrows():
        name = clean(row.get("candidate_entity_name"))
        source_status = clean(row.get("source_discovery_status"))
        declared_status = clean(row.get("benchmark_activation_status"))
        source_ok = source_status in allowed_source_status
        declared_ok = declared_status in allowed_activation_status
        url = clean(row.get("primary_source_url"))
        url_ok = url.startswith("https://") or url.startswith("http://")
        already_active = name in active_names
        master_available = name in master_names
        ratios_available = name in ratio_names

        if already_active:
            system_status = "ALREADY_ACTIVE"
            next_action = "NO_ACTION_ACTIVE_REGISTRY_MEMBER"
        elif not source_ok or not url_ok or not declared_ok:
            system_status = "REGISTRY_REVIEW_REQUIRED"
            next_action = "FIX_SOURCE_OR_STATUS_METADATA"
        elif not master_available:
            system_status = "FINANCIAL_DATA_ACQUISITION_REQUIRED"
            next_action = "COLLECT_AND_STAGE_AUDITED_FINANCIAL_STATEMENTS"
        elif not ratios_available:
            system_status = "RATIO_BUILD_REQUIRED"
            next_action = "RUN_PHASE_14C_AFTER_FINANCIAL_PROMOTION"
        else:
            system_status = "MANUAL_COMPARABILITY_REVIEW_REQUIRED"
            next_action = "REVIEW_SCOPE_PERIOD_ACCOUNTING_STANDARD_AND_ACTIVATE_EXPLICITLY"

        queue_rows.append({
            **row.to_dict(),
            "source_metadata_valid": bool(source_ok and url_ok and declared_ok),
            "already_active_in_peer_registry": already_active,
            "verified_master_observation_available": master_available,
            "ratio_observation_available": ratios_available,
            "system_activation_status": system_status,
            "next_action": next_action,
            "checked_at": utc_now(),
            "engine_version": VERSION,
        })

    queue = pd.DataFrame(queue_rows)
    atomic_write(queue, QUEUE_OUT)

    min_peers = int(config.get("activation_requirements", {}).get("minimum_peer_count_for_percentiles", 3))
    readiness_rows = []
    group_ids = sorted(set(candidates["peer_group_id"].astype(str).tolist()) | set(active.get("peer_group_id", pd.Series(dtype=str)).astype(str).tolist()))
    for group_id in group_ids:
        active_group = active[active.get("peer_group_id", pd.Series(dtype=str)).astype(str).eq(group_id)] if not active.empty else pd.DataFrame()
        candidate_group = queue[queue["peer_group_id"].astype(str).eq(group_id)]
        current_active = len(active_group)
        candidate_count = len(candidate_group)
        source_ready = int(candidate_group["source_metadata_valid"].astype(bool).sum()) if not candidate_group.empty else 0
        data_ready = int(candidate_group["ratio_observation_available"].astype(bool).sum()) if not candidate_group.empty else 0
        projected_after_all_candidates = current_active + candidate_count
        current_percentile_ready = current_active >= min_peers
        projected_universe_sufficient = projected_after_all_candidates >= min_peers
        readiness_rows.append({
            "peer_group_id": group_id,
            "peer_group_name": clean(candidate_group.iloc[0].get("peer_group_name")) if not candidate_group.empty else clean(active_group.iloc[0].get("peer_group_name")) if not active_group.empty else "",
            "current_active_members": current_active,
            "external_candidates": candidate_count,
            "candidates_with_verified_source_metadata": source_ready,
            "candidates_with_ratio_data_already_available": data_ready,
            "minimum_peer_count_for_percentiles": min_peers,
            "current_percentile_ready": current_percentile_ready,
            "projected_member_count_after_full_candidate_activation": projected_after_all_candidates,
            "projected_universe_sufficient_for_percentiles": projected_universe_sufficient,
            "activation_policy": "NO_EXTERNAL_CANDIDATE_AUTO_ACTIVATED",
            "engine_version": VERSION,
        })

    readiness = pd.DataFrame(readiness_rows)
    atomic_write(readiness, READINESS_OUT)

    summary = {
        "phase": "14E.1",
        "run_at": utc_now(),
        "status": "SUCCESS_EXTERNAL_PEER_ACQUISITION_QUEUE",
        "engine_version": VERSION,
        "external_candidates": int(len(queue)),
        "peer_groups": int(readiness["peer_group_id"].nunique()) if not readiness.empty else 0,
        "source_metadata_valid_candidates": int(queue["source_metadata_valid"].astype(bool).sum()),
        "candidates_requiring_financial_acquisition": int(queue["system_activation_status"].eq("FINANCIAL_DATA_ACQUISITION_REQUIRED").sum()),
        "candidates_ready_for_manual_comparability_review": int(queue["system_activation_status"].eq("MANUAL_COMPARABILITY_REVIEW_REQUIRED").sum()),
        "external_candidates_auto_activated": 0,
        "outputs": [str(QUEUE_OUT.relative_to(ROOT)), str(READINESS_OUT.relative_to(ROOT))],
        "guardrails": config.get("guardrails", {}),
    }
    append_jsonl(RUN_LOG, summary)

    print("PHASE 14E.1 - EXTERNAL PEER UNIVERSE ACQUISITION QUEUE")
    print("=" * 72)
    print(f"External peer candidates              : {summary['external_candidates']}")
    print(f"Peer groups                           : {summary['peer_groups']}")
    print(f"Valid primary-source metadata         : {summary['source_metadata_valid_candidates']}")
    print(f"Require audited financial acquisition : {summary['candidates_requiring_financial_acquisition']}")
    print(f"Ready for manual comparability review : {summary['candidates_ready_for_manual_comparability_review']}")
    print("External candidates auto-activated    : 0")
    print(f"Acquisition queue                     : {QUEUE_OUT.relative_to(ROOT)}")
    print(f"Readiness report                      : {READINESS_OUT.relative_to(ROOT)}")
    print()
    print("Guardrail: candidate registration is not peer activation. Percentiles remain blocked until verified ratios and explicit comparability review exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
