from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "15_Validation_and_Evidence"
CONFIG_FILE = PHASE_DIR / "00_Config" / "validation_evidence_protocol.json"
OUT_DIR = PHASE_DIR / "01_Audit"
REGISTER_OUT = OUT_DIR / "Validation_Evidence_Register.csv"
SUMMARY_OUT = OUT_DIR / "Validation_Workstream_Summary.csv"
GAPS_OUT = OUT_DIR / "Critical_Validation_Gaps.csv"
HASH_OUT = OUT_DIR / "Evidence_File_Hash_Manifest.csv"
RUN_LOG = OUT_DIR / "Phase_15A_Run_Log.jsonl"

PROTOCOL_VERSION = "SCI_VALIDATION_EVIDENCE_PROTOCOL_V1"
PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def resolve_glob(pattern: str) -> list[Path]:
    matches = []
    for path in ROOT.glob(pattern):
        if path.is_file():
            matches.append(path)
    return sorted(set(matches), key=lambda p: str(p))


def status_for(match_count: int, minimum: int, method_gate: str) -> str:
    if match_count == 0:
        return "MISSING_EVIDENCE"
    if match_count < minimum:
        return "PARTIAL_EVIDENCE"
    if method_gate == "OPEN_METHOD_REPRODUCTION_GATE":
        return "OPEN_METHOD_REPRODUCTION_GATE"
    if method_gate == "OPEN_EXTERNAL_VALIDATION_GATE":
        return "OPEN_EXTERNAL_VALIDATION_GATE"
    return "EVIDENCE_PRESENT_METHOD_REVIEW_REQUIRED"


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError(
            f"Validation protocol mismatch: {config.get('protocol_version')} != {PROTOCOL_VERSION}"
        )

    register_rows: list[dict] = []
    hash_rows: list[dict] = []

    for ws in config.get("workstreams", []):
        workstream_id = str(ws["workstream_id"])
        workstream_name = str(ws["name"])
        priority = str(ws.get("priority", "MEDIUM"))
        minimum = int(ws.get("minimum_matches", 1))
        method_gate = str(ws.get("method_gate", "REVIEW_REQUIRED"))
        next_phase = str(ws.get("next_validation_phase", ""))

        all_matches: list[Path] = []
        pattern_rows = []
        for pattern in ws.get("evidence_globs", []):
            matches = resolve_glob(pattern)
            all_matches.extend(matches)
            pattern_rows.append((pattern, matches))

        unique_matches = sorted(set(all_matches), key=lambda p: str(p))
        status = status_for(len(unique_matches), minimum, method_gate)

        register_rows.append({
            "workstream_id": workstream_id,
            "workstream_name": workstream_name,
            "priority": priority,
            "minimum_required_matches": minimum,
            "matched_files": len(unique_matches),
            "evidence_status": status,
            "method_gate": method_gate,
            "next_validation_phase": next_phase,
            "artifact_presence_is_method_validation": False,
            "matched_file_paths": ";".join(str(p.relative_to(ROOT)) for p in unique_matches),
            "evaluated_at": utc_now(),
            "protocol_version": PROTOCOL_VERSION,
        })

        for pattern, matches in pattern_rows:
            if not matches:
                hash_rows.append({
                    "workstream_id": workstream_id,
                    "workstream_name": workstream_name,
                    "evidence_glob": pattern,
                    "file_path": "",
                    "file_size_bytes": pd.NA,
                    "sha256": "",
                    "file_status": "NO_FILE_MATCH",
                })
                continue
            for path in matches:
                hash_rows.append({
                    "workstream_id": workstream_id,
                    "workstream_name": workstream_name,
                    "evidence_glob": pattern,
                    "file_path": str(path.relative_to(ROOT)),
                    "file_size_bytes": int(path.stat().st_size),
                    "sha256": sha256_file(path),
                    "file_status": "HASHED_EVIDENCE_ARTIFACT",
                })

    register = pd.DataFrame(register_rows)
    if register.empty:
        raise RuntimeError("Validation protocol contains no workstreams")

    register["priority_rank"] = register["priority"].map(PRIORITY_ORDER).fillna(99)
    register = register.sort_values(
        ["priority_rank", "workstream_id"], ascending=[True, True]
    ).drop(columns=["priority_rank"])

    hashes = pd.DataFrame(hash_rows)

    summary = (
        register.groupby(["priority", "evidence_status"], dropna=False)
        .size()
        .reset_index(name="workstream_count")
    )
    summary["priority_rank"] = summary["priority"].map(PRIORITY_ORDER).fillna(99)
    summary = summary.sort_values(["priority_rank", "evidence_status"]).drop(columns=["priority_rank"])

    gap_statuses = {
        "MISSING_EVIDENCE",
        "PARTIAL_EVIDENCE",
        "OPEN_METHOD_REPRODUCTION_GATE",
        "OPEN_EXTERNAL_VALIDATION_GATE",
    }
    gaps = register[
        register["evidence_status"].isin(gap_statuses)
        | register["priority"].eq("CRITICAL")
    ].copy()
    gaps["priority_rank"] = gaps["priority"].map(PRIORITY_ORDER).fillna(99)
    gaps = gaps.sort_values(["priority_rank", "workstream_id"]).drop(columns=["priority_rank"])

    atomic_write(register, REGISTER_OUT)
    atomic_write(summary, SUMMARY_OUT)
    atomic_write(gaps, GAPS_OUT)
    atomic_write(hashes, HASH_OUT)

    counts = register["evidence_status"].value_counts().to_dict()
    critical_open = int(
        register[
            register["priority"].eq("CRITICAL")
            & ~register["evidence_status"].eq("EVIDENCE_PRESENT_METHOD_REVIEW_REQUIRED")
        ].shape[0]
    )

    run = {
        "phase": "15A",
        "run_at": utc_now(),
        "status": "SUCCESS_VALIDATION_EVIDENCE_INVENTORY",
        "protocol_version": PROTOCOL_VERSION,
        "workstreams": int(len(register)),
        "status_counts": counts,
        "critical_open_or_missing_workstreams": critical_open,
        "hashed_file_rows": int((hashes.get("file_status", pd.Series(dtype=str)) == "HASHED_EVIDENCE_ARTIFACT").sum()),
        "guardrails": config.get("guardrails", {}),
        "outputs": [
            str(REGISTER_OUT.relative_to(ROOT)),
            str(SUMMARY_OUT.relative_to(ROOT)),
            str(GAPS_OUT.relative_to(ROOT)),
            str(HASH_OUT.relative_to(ROOT)),
        ],
    }
    append_jsonl(RUN_LOG, run)

    print("PHASE 15A - VALIDATION & EVIDENCE INVENTORY")
    print("=" * 76)
    print(f"Validation workstreams             : {len(register)}")
    for status_name in [
        "EVIDENCE_PRESENT_METHOD_REVIEW_REQUIRED",
        "PARTIAL_EVIDENCE",
        "MISSING_EVIDENCE",
        "OPEN_METHOD_REPRODUCTION_GATE",
        "OPEN_EXTERNAL_VALIDATION_GATE",
    ]:
        print(f"{status_name:<34}: {int(counts.get(status_name, 0))}")
    print(f"Critical open/missing workstreams  : {critical_open}")
    print(f"Evidence files hashed              : {run['hashed_file_rows']}")
    print(f"Evidence register                  : {REGISTER_OUT.relative_to(ROOT)}")
    print(f"Critical gaps                      : {GAPS_OUT.relative_to(ROOT)}")
    print(f"Hash manifest                      : {HASH_OUT.relative_to(ROOT)}")
    print()
    print("Important: file presence is evidence inventory only. It does not self-certify methodological validity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
