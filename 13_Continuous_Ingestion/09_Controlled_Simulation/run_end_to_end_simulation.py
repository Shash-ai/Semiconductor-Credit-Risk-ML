from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "09_Controlled_Simulation"
RESULT_FILE = OUT_DIR / "Phase_13J_Simulation_Result.json"
RUN_LOG = OUT_DIR / "Phase_13J_Run_Log.jsonl"

REAL_CANONICAL = ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"

SYNTHETIC_COMPANY = "Phase13J Synthetic Semiconductor Test Private Limited"
SYNTHETIC_APPROVAL_DATE = "2026-08-25"
SYNTHETIC_INVESTMENT_CRORE = 1234.0
SYNTHETIC_SOURCE_NAME = "PHASE_13J_CONTROLLED_SIMULATION_ONLY"

COPY_PATHS = [
    "01_Raw_Data/Semiconductor/Semiconductor_Master",
    "03_Modeling/Phase_3A_PCA_KMeans",
    "03_Modeling/Phase_3B_Cluster_Validation",
    "03_Modeling/Phase_3E_Robust_Stress_Test",
    "03_Modeling/Phase_6B_Monte_Carlo_Stress",
    "13_Continuous_Ingestion/00_Config",
    "13_Continuous_Ingestion/01_Discovery",
    "13_Continuous_Ingestion/04_Verification",
    "13_Continuous_Ingestion/05_Canonicalization",
    "13_Continuous_Ingestion/06_Frozen_Model",
    "13_Continuous_Ingestion/07_Automated_Evaluation",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def copy_required_tree(sandbox: Path) -> None:
    for rel in COPY_PATHS:
        source = ROOT / rel
        target = sandbox / rel
        if not source.exists():
            raise FileNotFoundError(f"Required simulation source path is missing: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)

    # Runtime records from the real pipeline are deliberately not carried into the
    # synthetic sandbox. Only source code, frozen reference inputs, and method
    # reference artifacts are retained.
    clear_patterns = {
        "13_Continuous_Ingestion/04_Verification": ["*.csv", "*.jsonl"],
        "13_Continuous_Ingestion/05_Canonicalization": ["*.csv", "*.jsonl"],
        "13_Continuous_Ingestion/06_Frozen_Model": ["Frozen_Model_New_Project_Inference.csv", "*.jsonl"],
        "13_Continuous_Ingestion/07_Automated_Evaluation": ["*.csv", "*.json", "*.jsonl"],
    }
    for rel, patterns in clear_patterns.items():
        directory = sandbox / rel
        for pattern in patterns:
            for path in directory.glob(pattern):
                if path.name.endswith(".py"):
                    continue
                if path.is_file():
                    path.unlink()

    artifact_dir = sandbox / "13_Continuous_Ingestion/06_Frozen_Model/artifacts"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)

    candidate_dir = sandbox / "13_Continuous_Ingestion/02_Candidates"
    audit_dir = sandbox / "13_Continuous_Ingestion/03_Audit"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    # No real banking outputs are copied. Phase 13F must therefore report that the
    # synthetic project has no verified project-specific banking evidence.
    (sandbox / "04_Banking_Alignment/04_Outputs").mkdir(parents=True, exist_ok=True)


def run_python(sandbox: Path, rel_script: str, *args: str, timeout: int = 180) -> dict:
    command = ["python", str(sandbox / rel_script), *args]
    completed = subprocess.run(
        command,
        cwd=sandbox,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    result = {
        "command": ["python", rel_script, *args],
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode != 0:
        raise RuntimeError(
            f"Sandbox command failed: {' '.join(result['command'])}\n"
            f"STDOUT:\n{result['stdout']}\nSTDERR:\n{result['stderr']}"
        )
    return result


class SyntheticSourceServer:
    def __init__(self) -> None:
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "SyntheticSourceServer":
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
                assert outer.server is not None
                base = f"http://127.0.0.1:{outer.server.server_port}"

                if self.path == "/feed.xml":
                    body = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\"><channel>
<title>Phase 13J Controlled Simulation Feed</title>
<item>
<title>Cabinet approves semiconductor manufacturing unit for controlled Phase 13J test</title>
<link>{base}/article.html</link>
<description>Approved semiconductor OSAT manufacturing facility in Gujarat for a controlled synthetic pipeline test.</description>
<pubDate>Tue, 25 Aug 2026 06:00:00 GMT</pubDate>
</item>
</channel></rss>"""
                    payload = body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if self.path == "/article.html":
                    body = f"""<!doctype html><html><body><article>
<h1>Cabinet approves semiconductor manufacturing unit for controlled Phase 13J test</h1>
<p>This is an explicitly synthetic test fixture. It is not a real government announcement and must never be promoted to the real canonical dataset.</p>
<p>The approved test proposal is for {SYNTHETIC_COMPANY}, an OSAT semiconductor manufacturing facility in Gujarat with a synthetic investment value of Rs. {SYNTHETIC_INVESTMENT_CRORE:.0f} crore.</p>
<p>India Semiconductor Mission controlled pipeline validation fixture.</p>
</article></body></html>"""
                    payload = body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format: str, *args) -> None:  # noqa: A002
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def feed_url(self) -> str:
        assert self.server is not None
        return f"http://127.0.0.1:{self.server.server_port}/feed.xml"

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)


def configure_synthetic_source(sandbox: Path, feed_url: str) -> None:
    registry = pd.DataFrame([
        {
            "source_id": "SIM-PHASE13J-RSS",
            "source_name": "Phase 13J Controlled Synthetic Source",
            "source_type": "RSS",
            "url": feed_url,
            "authority": "TEST_HARNESS_NOT_REAL_SOURCE",
            "active": True,
            "notes": "Synthetic fixture used only inside a temporary sandbox; never canonical evidence.",
        }
    ])
    registry.to_csv(
        sandbox / "13_Continuous_Ingestion/00_Config/source_registry.csv",
        index=False,
    )


def prepare_human_review(sandbox: Path) -> dict:
    review_path = sandbox / "13_Continuous_Ingestion/05_Canonicalization/Canonicalization_Review.csv"
    canonical_path = sandbox / "01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Master_Canonical.csv"
    review = read_csv(review_path)
    canonical = read_csv(canonical_path)

    if len(review) != 1:
        raise RuntimeError(f"Expected exactly one synthetic canonicalization review row, found {len(review)}")

    type_mask = canonical.get("project_type_standardized", pd.Series(dtype=str)).astype(str).str.upper().eq("OSAT")
    template = canonical.loc[type_mask].iloc[0] if type_mask.any() else canonical.iloc[0]

    idx = review.index[0]
    review.loc[idx, "review_decision"] = "APPROVE_NEW_PROJECT"
    review.loc[idx, "confirmed_company"] = SYNTHETIC_COMPANY
    review.loc[idx, "confirmed_state"] = "Gujarat"
    review.loc[idx, "confirmed_project_type"] = str(template.get("project_type", "OSAT"))
    review.loc[idx, "confirmed_project_type_standardized"] = str(template.get("project_type_standardized", "OSAT"))
    review.loc[idx, "confirmed_project_group"] = str(template.get("project_group", "OSAT"))
    review.loc[idx, "confirmed_approval_date"] = SYNTHETIC_APPROVAL_DATE
    review.loc[idx, "confirmed_investment_crore"] = SYNTHETIC_INVESTMENT_CRORE
    review.loc[idx, "confirmed_investment_category"] = str(template.get("investment_category", "TEST"))
    review.loc[idx, "confirmed_capacity_value"] = ""
    review.loc[idx, "confirmed_capacity_unit"] = ""
    review.loc[idx, "confirmed_capacity_category"] = ""
    review.loc[idx, "confirmed_technology"] = "Synthetic OSAT test technology"
    review.loc[idx, "confirmed_technology_partner"] = ""
    review.loc[idx, "confirmed_source_document"] = "PHASE_13J_SYNTHETIC_FIXTURE"
    review.loc[idx, "confirmed_source_page"] = "TEST_ONLY"
    review.loc[idx, "confirmed_source_name"] = SYNTHETIC_SOURCE_NAME
    review.loc[idx, "confirmed_data_quality_flag"] = "OK"
    review.loc[idx, "confirmed_state_verified"] = True
    review.loc[idx, "reviewer_notes"] = "Controlled synthetic fixture. Temporary sandbox only. Not real project evidence."
    review.loc[idx, "reviewed_by"] = "PHASE_13J_TEST_HARNESS"
    review.loc[idx, "reviewed_at"] = utc_now()
    review.to_csv(review_path, index=False)

    return {
        "template_project_id": str(template.get("project_id", "")),
        "template_project_type": str(template.get("project_type", "")),
        "template_project_type_standardized": str(template.get("project_type_standardized", "")),
        "template_project_group": str(template.get("project_group", "")),
    }


def execute_simulation(keep_sandbox: bool = False) -> dict:
    started = utc_now()
    real_hash_before = sha256_file(REAL_CANONICAL)
    real_rows_before = len(read_csv(REAL_CANONICAL))

    temp_ctx = tempfile.TemporaryDirectory(prefix="phase13j_")
    sandbox = Path(temp_ctx.name) / "Semiconductor_Credit_Risk_ML_Sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    commands: list[dict] = []
    try:
        copy_required_tree(sandbox)
        sandbox_canonical = sandbox / "01_Raw_Data/Semiconductor/Semiconductor_Master/Semiconductor_Master_Canonical.csv"
        sandbox_rows_before = len(read_csv(sandbox_canonical))

        with SyntheticSourceServer() as source:
            configure_synthetic_source(sandbox, source.feed_url)
            commands.append(run_python(
                sandbox,
                "13_Continuous_Ingestion/01_Discovery/discover_new_projects.py",
            ))
            commands.append(run_python(
                sandbox,
                "13_Continuous_Ingestion/04_Verification/verify_candidates.py",
            ))

        candidates = read_csv(sandbox / "13_Continuous_Ingestion/02_Candidates/Project_Discovery_Candidates.csv")
        structured = read_csv(sandbox / "13_Continuous_Ingestion/04_Verification/Structured_Project_Candidates.csv")
        queue = read_csv(sandbox / "13_Continuous_Ingestion/04_Verification/Verification_Queue.csv")
        if len(candidates) != 1 or len(structured) != 1 or len(queue) != 1:
            raise RuntimeError(
                f"Synthetic intake expected one candidate/structured/queue row; got "
                f"{len(candidates)}/{len(structured)}/{len(queue)}"
            )

        # First 13D pass must only create/refresh the review gate. No real or sandbox
        # canonical data may be changed by the stage-only run.
        commands.append(run_python(
            sandbox,
            "13_Continuous_Ingestion/05_Canonicalization/canonicalize_reviewed_candidates.py",
        ))
        if len(read_csv(sandbox_canonical)) != sandbox_rows_before:
            raise RuntimeError("Stage-only canonicalization changed the sandbox canonical master")

        template = prepare_human_review(sandbox)

        # Re-stage after the explicit simulated human review, then apply only inside
        # the disposable sandbox with the real confirmation token.
        commands.append(run_python(
            sandbox,
            "13_Continuous_Ingestion/05_Canonicalization/canonicalize_reviewed_candidates.py",
        ))
        staging = read_csv(sandbox / "13_Continuous_Ingestion/05_Canonicalization/Canonical_Staging.csv")
        conflicts = read_csv(sandbox / "13_Continuous_Ingestion/05_Canonicalization/Canonicalization_Conflicts.csv")
        if len(staging) != 1:
            raise RuntimeError(f"Expected one staged synthetic project, found {len(staging)}")
        if not conflicts.empty:
            raise RuntimeError(f"Synthetic review produced unexpected canonicalization conflicts: {len(conflicts)}")

        commands.append(run_python(
            sandbox,
            "13_Continuous_Ingestion/05_Canonicalization/canonicalize_reviewed_candidates.py",
            "--apply",
            "--confirmation",
            "APPLY_REVIEWED_CANONICAL_ROWS",
        ))

        sandbox_after_apply = read_csv(sandbox_canonical)
        if len(sandbox_after_apply) != sandbox_rows_before + 1:
            raise RuntimeError("Sandbox canonical apply did not add exactly one project")
        synthetic_rows = sandbox_after_apply[
            sandbox_after_apply["company"].astype(str).eq(SYNTHETIC_COMPANY)
        ]
        if len(synthetic_rows) != 1:
            raise RuntimeError("Synthetic canonical project was not found exactly once after sandbox apply")
        synthetic_project_id = str(synthetic_rows.iloc[0]["project_id"])

        commands.append(run_python(
            sandbox,
            "13_Continuous_Ingestion/06_Frozen_Model/freeze_and_infer.py",
        ))
        inference = read_csv(sandbox / "13_Continuous_Ingestion/06_Frozen_Model/Frozen_Model_New_Project_Inference.csv")
        inferred = inference[inference["project_id"].astype(str).eq(synthetic_project_id)]
        if len(inferred) != 1:
            raise RuntimeError(f"Expected one structural inference row for {synthetic_project_id}, found {len(inferred)}")

        validation = json.loads(
            (sandbox / "13_Continuous_Ingestion/06_Frozen_Model/artifacts/Frozen_Model_Validation.json").read_text(encoding="utf-8")
        )
        if validation.get("status") != "PASS_FROZEN_REFERENCE_REPRODUCED":
            raise RuntimeError(f"Frozen reference reproduction failed in simulation: {validation.get('status')}")

        commands.append(run_python(
            sandbox,
            "13_Continuous_Ingestion/07_Automated_Evaluation/evaluate_new_projects.py",
        ))

        deterministic = read_csv(sandbox / "13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Deterministic_Stress.csv")
        mc = read_csv(sandbox / "13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Monte_Carlo_Status.csv")
        banking = read_csv(sandbox / "13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Banking_Evidence_Status.csv")
        register = read_csv(sandbox / "13_Continuous_Ingestion/07_Automated_Evaluation/New_Project_Evaluation_Register.csv")

        det_row = deterministic[deterministic["project_id"].astype(str).eq(synthetic_project_id)]
        mc_row = mc[mc["project_id"].astype(str).eq(synthetic_project_id)]
        bank_row = banking[banking["project_id"].astype(str).eq(synthetic_project_id)]
        reg_row = register[register["project_id"].astype(str).eq(synthetic_project_id)]

        if len(det_row) != 1 or len(mc_row) != 1 or len(bank_row) != 1 or len(reg_row) != 1:
            raise RuntimeError("Phase 13F did not produce exactly one result row in every synthetic output")
        if str(det_row.iloc[0]["deterministic_evaluation_status"]) != "DETERMINISTIC_STRESS_EVALUATED":
            raise RuntimeError("Synthetic 2026 project was not deterministically stress-evaluated")
        if str(mc_row.iloc[0]["monte_carlo_status"]) != "MC_METHOD_REPRODUCTION_REQUIRED":
            raise RuntimeError("Monte Carlo reproducibility guardrail was not preserved")
        if str(bank_row.iloc[0]["banking_evidence_status"]) != "INSUFFICIENT_VERIFIED_BANKING_EVIDENCE":
            raise RuntimeError("Synthetic project unexpectedly received project-specific banking evidence")

        real_hash_after = sha256_file(REAL_CANONICAL)
        real_rows_after = len(read_csv(REAL_CANONICAL))
        if real_hash_before != real_hash_after or real_rows_before != real_rows_after:
            raise RuntimeError("REAL CANONICAL MASTER CHANGED DURING QUARANTINED SIMULATION")

        result = {
            "phase": "13J",
            "simulation_version": "SCI_PHASE13_QUARANTINED_E2E_V1",
            "started_at": started,
            "completed_at": utc_now(),
            "status": "PASS",
            "quarantine": {
                "temporary_sandbox_used": True,
                "real_canonical_sha256_before": real_hash_before,
                "real_canonical_sha256_after": real_hash_after,
                "real_canonical_rows_before": real_rows_before,
                "real_canonical_rows_after": real_rows_after,
                "real_canonical_unchanged": True,
                "synthetic_fixture_persisted_to_real_canonical": False,
            },
            "synthetic_fixture": {
                "company": SYNTHETIC_COMPANY,
                "approval_date": SYNTHETIC_APPROVAL_DATE,
                "investment_crore": SYNTHETIC_INVESTMENT_CRORE,
                "sandbox_project_id": synthetic_project_id,
                "source_label": SYNTHETIC_SOURCE_NAME,
                "is_real_project": False,
            },
            "stage_results": {
                "discovery_candidates": int(len(candidates)),
                "structured_candidates": int(len(structured)),
                "verification_queue_rows": int(len(queue)),
                "canonical_staging_rows": int(len(staging)),
                "canonical_conflicts": int(len(conflicts)),
                "sandbox_canonical_rows_before": int(sandbox_rows_before),
                "sandbox_canonical_rows_after": int(len(sandbox_after_apply)),
                "frozen_reference_status": validation.get("status"),
                "new_project_inference_rows": int(len(inferred)),
                "predicted_validated_cluster": int(pd.to_numeric(inferred.iloc[0]["predicted_validated_cluster"])),
                "structural_extrapolation_signal": str(inferred.iloc[0]["structural_extrapolation_signal"]),
                "deterministic_evaluation_status": str(det_row.iloc[0]["deterministic_evaluation_status"]),
                "baseline_score": float(pd.to_numeric(det_row.iloc[0]["baseline_score"])),
                "severe_score": float(pd.to_numeric(det_row.iloc[0]["severe_score"])),
                "monte_carlo_status": str(mc_row.iloc[0]["monte_carlo_status"]),
                "banking_evidence_status": str(bank_row.iloc[0]["banking_evidence_status"]),
                "overall_evaluation_status": str(reg_row.iloc[0]["overall_automated_evaluation_status"]),
            },
            "template_contract": template,
            "guardrails": {
                "automatic_real_canonical_apply": False,
                "synthetic_banking_data_created": False,
                "pd_lgd_ead_ecl_generated": False,
                "automatic_credit_decision_generated": False,
                "monte_carlo_method_invented": False,
            },
            "commands": commands,
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        append_jsonl(RUN_LOG, {
            "run_at": result["completed_at"],
            "phase": "13J",
            "status": result["status"],
            "synthetic_project_id": synthetic_project_id,
            "real_canonical_unchanged": True,
        })

        if keep_sandbox:
            keep_path = OUT_DIR / "sandbox_snapshot"
            if keep_path.exists():
                shutil.rmtree(keep_path)
            shutil.copytree(sandbox, keep_path)
            result["sandbox_snapshot"] = str(keep_path.relative_to(ROOT))
            RESULT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        return result

    finally:
        if not keep_sandbox:
            temp_ctx.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 13J quarantined end-to-end simulation")
    parser.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Persist a copy of the temporary sandbox under 09_Controlled_Simulation for debugging. Never use this in scheduled production runs.",
    )
    args = parser.parse_args()

    try:
        result = execute_simulation(keep_sandbox=args.keep_sandbox)
    except Exception as exc:
        failure = {
            "phase": "13J",
            "simulation_version": "SCI_PHASE13_QUARANTINED_E2E_V1",
            "completed_at": utc_now(),
            "status": "FAILED_SAFE",
            "error": str(exc),
            "real_canonical_sha256_current": sha256_file(REAL_CANONICAL) if REAL_CANONICAL.exists() else None,
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_FILE.write_text(json.dumps(failure, indent=2, ensure_ascii=False), encoding="utf-8")
        append_jsonl(RUN_LOG, failure)
        print("PHASE 13J - FAILED SAFE")
        print("=" * 72)
        print(str(exc))
        print("No synthetic fixture is permitted to survive in the real canonical master.")
        return 1

    stage = result["stage_results"]
    print("PHASE 13J - QUARANTINED END-TO-END SIMULATION")
    print("=" * 72)
    print(f"Status                         : {result['status']}")
    print(f"Synthetic project ID           : {result['synthetic_fixture']['sandbox_project_id']}")
    print(f"Discovery candidates           : {stage['discovery_candidates']}")
    print(f"Verification queue rows        : {stage['verification_queue_rows']}")
    print(f"Canonical staging rows         : {stage['canonical_staging_rows']}")
    print(f"Sandbox canonical rows         : {stage['sandbox_canonical_rows_before']} -> {stage['sandbox_canonical_rows_after']}")
    print(f"Frozen reference reproduction  : {stage['frozen_reference_status']}")
    print(f"New-project inference rows     : {stage['new_project_inference_rows']}")
    print(f"Deterministic evaluation       : {stage['deterministic_evaluation_status']}")
    print(f"Monte Carlo guardrail          : {stage['monte_carlo_status']}")
    print(f"Banking evidence treatment     : {stage['banking_evidence_status']}")
    print(f"Real canonical unchanged       : {result['quarantine']['real_canonical_unchanged']}")
    print()
    print(f"Result                         : {RESULT_FILE.relative_to(ROOT)}")
    print("Synthetic fixture: TEST ONLY. It is not a real semiconductor project or banking record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
