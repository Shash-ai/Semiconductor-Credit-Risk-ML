from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "13_Continuous_Ingestion" / "00_Config" / "source_monitor_config.json"
CANDIDATE_FILE = ROOT / "13_Continuous_Ingestion" / "02_Candidates" / "Project_Discovery_Candidates.csv"
CANONICAL_FILE = ROOT / "01_Raw_Data" / "Semiconductor" / "Semiconductor_Master" / "Semiconductor_Master_Canonical.csv"
OUT_DIR = ROOT / "13_Continuous_Ingestion" / "04_Verification"
STRUCTURED_FILE = OUT_DIR / "Structured_Project_Candidates.csv"
FIELD_EVIDENCE_FILE = OUT_DIR / "Candidate_Field_Evidence.csv"
QUEUE_FILE = OUT_DIR / "Verification_Queue.csv"
AUDIT_FILE = OUT_DIR / "Verification_Run_Log.jsonl"


STRUCTURED_COLUMNS = [
    "discovery_id",
    "source_name",
    "title",
    "url",
    "published_at",
    "source_fetch_status",
    "source_domain",
    "primary_source_accessible",
    "approval_language_detected",
    "proposed_company",
    "proposed_state",
    "proposed_project_type",
    "proposed_investment_crore",
    "proposed_capacity_text",
    "proposed_technology_text",
    "matched_canonical_project_ids",
    "matched_canonical_companies",
    "duplicate_signal",
    "multi_project_article_signal",
    "extraction_confidence",
    "verification_decision",
    "verification_notes",
    "article_sha256",
    "verified_at",
]

FIELD_EVIDENCE_COLUMNS = [
    "discovery_id",
    "field",
    "extracted_value",
    "evidence_snippet",
    "source_url",
    "evidence_status",
]

QUEUE_COLUMNS = [
    "discovery_id",
    "title",
    "url",
    "verification_decision",
    "duplicate_signal",
    "multi_project_article_signal",
    "proposed_company",
    "proposed_state",
    "proposed_project_type",
    "proposed_investment_crore",
    "review_required",
    "review_reason",
]


STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry",
]

PROJECT_TYPE_RULES = [
    ("FAB", ["semiconductor fab", "wafer fab", "fabrication facility", "fabrication unit", "foundry"]),
    ("OSAT", ["osat", "outsourced semiconductor assembly and test"]),
    ("ATMP", ["atmp", "assembly testing marking and packaging", "assembly and test facility"]),
    ("Advanced Packaging", ["advanced packaging", "heterogeneous integration", "3d packaging"]),
    ("Compound Semiconductor Fab + ATMP", ["compound semiconductor", "silicon carbide", "sic fab", "gan fab"]),
    ("Semiconductor Manufacturing", ["semiconductor manufacturing unit", "semiconductor manufacturing facility"]),
]

COMPANY_SUFFIXES = (
    "limited", "ltd", "private limited", "pvt ltd", "inc", "corporation", "corp",
    "technologies", "technology", "electronics", "semicon", "semiconductor",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value: str) -> str:
    value = normalise_space(str(value)).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalise_space(value)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def fetch_article(session: requests.Session, url: str, timeout: int) -> tuple[str, str]:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = normalise_space(main.get_text(" ", strip=True))
    return response.url, text


def source_is_primary(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith("pib.gov.in") or host.endswith("meity.gov.in") or host.endswith("ism.gov.in")


def detect_approval_language(text: str, config: dict) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in config.get("approval_keywords", []))


def detect_states(text: str) -> list[str]:
    lower = text.lower()
    return [state for state in STATES if re.search(rf"\b{re.escape(state.lower())}\b", lower)]


def detect_project_types(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    for label, phrases in PROJECT_TYPE_RULES:
        if any(p in lower for p in phrases):
            hits.append(label)
    return list(dict.fromkeys(hits))


def investment_matches(text: str) -> list[tuple[float, str]]:
    patterns = [
        r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.\d+)?)\s*(?:crore|cr\b)",
        r"investment(?:\s+of|\s+worth|\s+is|\s+of around|\s+of approximately)?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(?:crore|cr\b)",
        r"project\s+cost(?:\s+of|\s+is)?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(?:crore|cr\b)",
    ]
    found: list[tuple[float, str]] = []
    lower = text.lower()
    for pattern in patterns:
        for m in re.finditer(pattern, lower, flags=re.I):
            try:
                value = float(m.group(1).replace(",", ""))
            except Exception:
                continue
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 120)
            snippet = normalise_space(text[start:end])
            if not any(abs(value - x[0]) < 0.01 for x in found):
                found.append((value, snippet))
    return found


def likely_company_candidates(title: str, text: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    combined = f"{title}. {text[:7000]}"

    patterns = [
        r"(?:by|of|for)\s+([A-Z][A-Za-z0-9&().,'\- ]{2,100}?(?:Private Limited|Pvt\.? Ltd\.?|Limited|Ltd\.?|Inc\.?|Corporation|Corp\.?))",
        r"([A-Z][A-Za-z0-9&().,'\- ]{2,100}?(?:Semicon|Semiconductor|Electronics|Technologies|Technology)\s+(?:Private Limited|Pvt\.? Ltd\.?|Limited|Ltd\.?|Inc\.?))",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, combined):
            value = normalise_space(m.group(1)).strip(" ,.;:-")
            if 3 <= len(value) <= 120:
                snippet = normalise_space(combined[max(0, m.start()-80):m.end()+100])
                if norm(value) not in {norm(x[0]) for x in candidates}:
                    candidates.append((value, snippet))
    return candidates[:8]


def canonical_matches(article_text: str, canonical: pd.DataFrame) -> tuple[list[str], list[str]]:
    article_norm = norm(article_text)
    ids: list[str] = []
    companies: list[str] = []

    for _, row in canonical.iterrows():
        company = str(row.get("company", "")).strip()
        if not company:
            continue
        company_norm = norm(company)
        tokens = [t for t in company_norm.split() if len(t) >= 4 and t not in COMPANY_SUFFIXES]
        phrase_hit = company_norm and company_norm in article_norm
        token_hit = len(tokens) >= 2 and sum(t in article_norm for t in tokens[:5]) >= 2
        if phrase_hit or token_hit:
            ids.append(str(row.get("project_id", "")))
            companies.append(company)

    return ids, companies


def excerpt_around(text: str, needle: str, radius: int = 140) -> str:
    if not needle:
        return ""
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return ""
    return normalise_space(text[max(0, idx-radius):min(len(text), idx+len(needle)+radius)])


def confidence_score(company_count: int, state_count: int, type_count: int, investment_count: int, approval: bool, primary: bool) -> int:
    score = 0
    score += 20 if primary else 0
    score += 20 if approval else 0
    score += 20 if company_count == 1 else (8 if company_count > 1 else 0)
    score += 15 if state_count == 1 else (5 if state_count > 1 else 0)
    score += 15 if type_count == 1 else (5 if type_count > 1 else 0)
    score += 10 if investment_count == 1 else (3 if investment_count > 1 else 0)
    return min(score, 100)


def ensure_empty_outputs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not STRUCTURED_FILE.exists():
        pd.DataFrame(columns=STRUCTURED_COLUMNS).to_csv(STRUCTURED_FILE, index=False)
    if not FIELD_EVIDENCE_FILE.exists():
        pd.DataFrame(columns=FIELD_EVIDENCE_COLUMNS).to_csv(FIELD_EVIDENCE_FILE, index=False)
    if not QUEUE_FILE.exists():
        pd.DataFrame(columns=QUEUE_COLUMNS).to_csv(QUEUE_FILE, index=False)


def append_audit(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    config = load_config()
    ensure_empty_outputs()

    candidates = pd.read_csv(CANDIDATE_FILE) if CANDIDATE_FILE.exists() else pd.DataFrame()
    canonical = pd.read_csv(CANONICAL_FILE) if CANONICAL_FILE.exists() else pd.DataFrame()

    if candidates.empty:
        summary = {
            "run_at": utc_now(),
            "phase": "13C",
            "status": "SUCCESS_NO_CANDIDATES",
            "candidates_seen": 0,
            "candidates_processed": 0,
            "manual_review_required": 0,
        }
        append_audit(summary)
        print("PHASE 13C - SOURCE VERIFICATION & STRUCTURED EXTRACTION")
        print("=" * 64)
        print("Candidate register is currently empty.")
        print("Nothing was promoted or inferred.")
        print(f"Structured output : {STRUCTURED_FILE.relative_to(ROOT)}")
        print(f"Verification queue: {QUEUE_FILE.relative_to(ROOT)}")
        return 0

    previous = pd.read_csv(STRUCTURED_FILE) if STRUCTURED_FILE.exists() else pd.DataFrame(columns=STRUCTURED_COLUMNS)
    processed_ids = set(previous.get("discovery_id", pd.Series(dtype=str)).astype(str))

    session = requests.Session()
    session.headers.update({
        "User-Agent": config.get("user_agent", "Semiconductor-Credit-Intelligence-Research-Monitor/1.0"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    structured_rows = []
    evidence_rows = []
    queue_rows = []
    errors = []

    for _, candidate in candidates.iterrows():
        discovery_id = str(candidate.get("discovery_id", "")).strip()
        if not discovery_id or discovery_id in processed_ids:
            continue

        title = str(candidate.get("title", "") or "")
        original_url = str(candidate.get("url", "") or "")
        source_name = str(candidate.get("source_name", "") or "")
        published_at = str(candidate.get("published_at", "") or "")

        try:
            final_url, text = fetch_article(session, original_url, int(config.get("request_timeout_seconds", 30)))
            fetch_status = "FETCHED"
        except Exception as exc:
            final_url, text = original_url, ""
            fetch_status = "FETCH_FAILED"
            errors.append(f"{discovery_id}: {type(exc).__name__}: {exc}")

        primary = source_is_primary(final_url) if final_url else False
        approval = detect_approval_language(text, config) if text else False
        states = detect_states(text) if text else []
        project_types = detect_project_types(text) if text else []
        investments = investment_matches(text) if text else []
        companies = likely_company_candidates(title, text) if text else []
        matched_ids, matched_companies = canonical_matches(text, canonical) if text and not canonical.empty else ([], [])

        proposed_company = companies[0][0] if len(companies) == 1 else ""
        proposed_state = states[0] if len(states) == 1 else ""
        proposed_type = project_types[0] if len(project_types) == 1 else ""
        proposed_investment = investments[0][0] if len(investments) == 1 else pd.NA

        multi_project = any([
            len(companies) > 1,
            len(states) > 1 and len(investments) > 1,
            len(investments) > 2,
            text.lower().count("semiconductor unit") > 2 if text else False,
            text.lower().count("semiconductor project") > 2 if text else False,
        ])

        duplicate_signal = "NONE"
        if matched_ids:
            duplicate_signal = "POSSIBLE_EXISTING_CANONICAL"
        if len(matched_ids) > 1:
            duplicate_signal = "MULTIPLE_CANONICAL_PROJECTS_REFERENCED"

        confidence = confidence_score(
            len(companies), len(states), len(project_types), len(investments), approval, primary
        )

        reasons = []
        if fetch_status != "FETCHED":
            reasons.append("SOURCE_FETCH_FAILED")
        if not primary:
            reasons.append("PRIMARY_SOURCE_NOT_CONFIRMED")
        if not approval:
            reasons.append("APPROVAL_LANGUAGE_NOT_CONFIRMED")
        if multi_project:
            reasons.append("MULTI_PROJECT_ARTICLE")
        if matched_ids:
            reasons.append("POSSIBLE_EXISTING_CANONICAL_PROJECT")
        if not proposed_company:
            reasons.append("COMPANY_REQUIRES_REVIEW")
        if not proposed_state:
            reasons.append("STATE_REQUIRES_REVIEW")
        if not proposed_type:
            reasons.append("PROJECT_TYPE_REQUIRES_REVIEW")
        if pd.isna(proposed_investment):
            reasons.append("INVESTMENT_REQUIRES_REVIEW")

        if fetch_status != "FETCHED" or not primary or not approval:
            decision = "MANUAL_REVIEW_REQUIRED"
        elif matched_ids:
            decision = "LIKELY_EXISTING_CANONICAL_REVIEW_REQUIRED"
        elif multi_project:
            decision = "MULTI_PROJECT_SPLIT_REQUIRED"
        elif proposed_company and proposed_state and proposed_type and pd.notna(proposed_investment):
            decision = "STRUCTURED_CANDIDATE_READY_FOR_REVIEW"
        else:
            decision = "MANUAL_REVIEW_REQUIRED"

        notes = ";".join(reasons) if reasons else "NO_AUTOMATIC_PROMOTION"
        structured_rows.append({
            "discovery_id": discovery_id,
            "source_name": source_name,
            "title": title,
            "url": final_url,
            "published_at": published_at,
            "source_fetch_status": fetch_status,
            "source_domain": urlparse(final_url).netloc.lower() if final_url else "",
            "primary_source_accessible": primary,
            "approval_language_detected": approval,
            "proposed_company": proposed_company,
            "proposed_state": proposed_state,
            "proposed_project_type": proposed_type,
            "proposed_investment_crore": proposed_investment,
            "proposed_capacity_text": "",
            "proposed_technology_text": "",
            "matched_canonical_project_ids": "|".join(matched_ids),
            "matched_canonical_companies": "|".join(matched_companies),
            "duplicate_signal": duplicate_signal,
            "multi_project_article_signal": bool(multi_project),
            "extraction_confidence": confidence,
            "verification_decision": decision,
            "verification_notes": notes,
            "article_sha256": sha256_text(text) if text else "",
            "verified_at": utc_now(),
        })

        for company, snippet in companies:
            evidence_rows.append({
                "discovery_id": discovery_id,
                "field": "company_candidate",
                "extracted_value": company,
                "evidence_snippet": snippet,
                "source_url": final_url,
                "evidence_status": "EXTRACTED_NOT_VERIFIED",
            })
        for state in states:
            evidence_rows.append({
                "discovery_id": discovery_id,
                "field": "state_candidate",
                "extracted_value": state,
                "evidence_snippet": excerpt_around(text, state),
                "source_url": final_url,
                "evidence_status": "EXTRACTED_NOT_VERIFIED",
            })
        for project_type in project_types:
            evidence_rows.append({
                "discovery_id": discovery_id,
                "field": "project_type_candidate",
                "extracted_value": project_type,
                "evidence_snippet": excerpt_around(text, project_type.split()[0]),
                "source_url": final_url,
                "evidence_status": "EXTRACTED_NOT_VERIFIED",
            })
        for investment, snippet in investments:
            evidence_rows.append({
                "discovery_id": discovery_id,
                "field": "investment_crore_candidate",
                "extracted_value": investment,
                "evidence_snippet": snippet,
                "source_url": final_url,
                "evidence_status": "EXTRACTED_NOT_VERIFIED",
            })

        queue_rows.append({
            "discovery_id": discovery_id,
            "title": title,
            "url": final_url,
            "verification_decision": decision,
            "duplicate_signal": duplicate_signal,
            "multi_project_article_signal": bool(multi_project),
            "proposed_company": proposed_company,
            "proposed_state": proposed_state,
            "proposed_project_type": proposed_type,
            "proposed_investment_crore": proposed_investment,
            "review_required": True,
            "review_reason": notes,
        })

    if structured_rows:
        new_structured = pd.DataFrame(structured_rows, columns=STRUCTURED_COLUMNS)
        combined = pd.concat([previous, new_structured], ignore_index=True)
        combined.to_csv(STRUCTURED_FILE, index=False)

    if evidence_rows:
        existing = pd.read_csv(FIELD_EVIDENCE_FILE) if FIELD_EVIDENCE_FILE.exists() else pd.DataFrame(columns=FIELD_EVIDENCE_COLUMNS)
        pd.concat([existing, pd.DataFrame(evidence_rows)], ignore_index=True).to_csv(FIELD_EVIDENCE_FILE, index=False)

    if queue_rows:
        existing_queue = pd.read_csv(QUEUE_FILE) if QUEUE_FILE.exists() else pd.DataFrame(columns=QUEUE_COLUMNS)
        pd.concat([existing_queue, pd.DataFrame(queue_rows)], ignore_index=True).to_csv(QUEUE_FILE, index=False)

    summary = {
        "run_at": utc_now(),
        "phase": "13C",
        "status": "SUCCESS" if not errors else "SUCCESS_WITH_FETCH_ERRORS",
        "candidates_seen": int(len(candidates)),
        "candidates_processed": int(len(structured_rows)),
        "manual_review_required": int(sum(r["review_required"] for r in queue_rows)),
        "ready_for_structured_review": int(sum(r["verification_decision"] == "STRUCTURED_CANDIDATE_READY_FOR_REVIEW" for r in queue_rows)),
        "possible_existing": int(sum("EXISTING_CANONICAL" in r["verification_decision"] for r in queue_rows)),
        "multi_project_split_required": int(sum(r["verification_decision"] == "MULTI_PROJECT_SPLIT_REQUIRED" for r in queue_rows)),
        "errors": errors,
    }
    append_audit(summary)

    print("PHASE 13C - SOURCE VERIFICATION & STRUCTURED EXTRACTION")
    print("=" * 64)
    print(f"Candidates seen              : {summary['candidates_seen']}")
    print(f"Candidates processed         : {summary['candidates_processed']}")
    print(f"Ready for structured review  : {summary['ready_for_structured_review']}")
    print(f"Possible existing projects   : {summary['possible_existing']}")
    print(f"Multi-project split required : {summary['multi_project_split_required']}")
    print(f"Manual review required       : {summary['manual_review_required']}")
    print(f"Fetch errors                 : {len(errors)}")
    print()
    print(f"Structured output : {STRUCTURED_FILE.relative_to(ROOT)}")
    print(f"Field evidence    : {FIELD_EVIDENCE_FILE.relative_to(ROOT)}")
    print(f"Verification queue: {QUEUE_FILE.relative_to(ROOT)}")
    print(f"Audit log         : {AUDIT_FILE.relative_to(ROOT)}")

    if queue_rows:
        print("\nREVIEW QUEUE")
        for row in queue_rows:
            print(f"- {row['discovery_id']} | {row['verification_decision']} | {row['title']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
