from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "13_Continuous_Ingestion" / "00_Config"
CONFIG_FILE = CONFIG_DIR / "source_monitor_config.json"
SOURCE_REGISTRY_FILE = CONFIG_DIR / "source_registry.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def keyword_hits(text: str, keywords: Iterable[str]) -> list[str]:
    lower = text.lower()
    return sorted({k for k in keywords if k.lower() in lower})


def candidate_score(text: str, config: dict) -> tuple[int, list[str], list[str], list[str]]:
    semiconductor = keyword_hits(text, config["semiconductor_keywords"])
    approvals = keyword_hits(text, config["approval_keywords"])
    negatives = keyword_hits(text, config["negative_keywords"])

    score = 0
    if semiconductor:
        score += 2
    if approvals:
        score += 3
    if "cabinet approves" in text.lower() or "cabinet approved" in text.lower():
        score += 2
    if "india semiconductor mission" in text.lower():
        score += 1
    score -= min(len(negatives), 2)

    return score, semiconductor, approvals, negatives


def request_session(config: dict) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": config["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def fetch_text(session: requests.Session, url: str, timeout: int) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_rss(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []

    for item in root.findall(".//item"):
        def get(tag: str) -> str:
            node = item.find(tag)
            return normalise_space(node.text if node is not None and node.text else "")

        title = get("title")
        link = get("link")
        description = get("description")
        pub_date = get("pubDate")

        if title and link:
            items.append({
                "title": title,
                "url": link,
                "description": description,
                "published_at": pub_date,
            })

    return items


def article_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    main = (
        soup.find("div", class_=re.compile("content", re.I))
        or soup.find("article")
        or soup.body
        or soup
    )

    return normalise_space(main.get_text(" ", strip=True))


def load_existing_candidates(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def canonical_project_count(config: dict) -> int | None:
    path = ROOT / config["canonical_master"]
    if not path.exists():
        return None
    try:
        return len(pd.read_csv(path))
    except Exception:
        return None


def append_audit(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    config = load_config()
    timeout = int(config.get("request_timeout_seconds", 30))
    threshold = int(config.get("minimum_candidate_score", 4))

    candidates_path = ROOT / config["candidate_register"]
    audit_path = ROOT / config["audit_log"]
    candidates_path.parent.mkdir(parents=True, exist_ok=True)

    sources = pd.read_csv(SOURCE_REGISTRY_FILE)
    sources = sources[
        sources["active"].astype(str).str.lower().isin({"true", "1", "yes"})
    ].copy()
    rss_sources = sources[sources["source_type"].astype(str).str.upper().eq("RSS")]

    existing = load_existing_candidates(candidates_path)
    existing_urls = set(existing.get("url", pd.Series(dtype=str)).dropna().astype(str))
    existing_hashes = set(existing.get("content_sha256", pd.Series(dtype=str)).dropna().astype(str))

    session = request_session(config)
    discovered_at = utc_now()
    new_rows: list[dict] = []
    errors: list[dict] = []
    rss_items_scanned = 0
    fetched_articles = 0

    for _, source in rss_sources.iterrows():
        source_id = str(source["source_id"])
        source_name = str(source["source_name"])
        feed_url = str(source["url"])

        try:
            feed_text = fetch_text(session, feed_url, timeout)
            items = parse_rss(feed_text)
        except Exception as exc:
            errors.append({"source_id": source_id, "stage": "feed", "error": str(exc)})
            continue

        for item in items:
            rss_items_scanned += 1
            seed_text = normalise_space(
                " ".join([item["title"], item["description"]])
            )

            seed_semiconductor_hits = keyword_hits(seed_text, config["semiconductor_keywords"])
            if not seed_semiconductor_hits:
                continue

            url = item["url"]
            try:
                html_text = fetch_text(session, url, timeout)
                fetched_articles += 1
                body = article_text(html_text)
            except Exception as exc:
                errors.append({"source_id": source_id, "stage": "article", "url": url, "error": str(exc)})
                body = seed_text

            combined = normalise_space(" ".join([seed_text, body]))
            score, semiconductor_hits, approval_hits, negative_hits = candidate_score(combined, config)

            if score < threshold or not semiconductor_hits or not approval_hits:
                continue

            content_hash = sha256_text(combined)
            if url in existing_urls or content_hash in existing_hashes:
                continue

            discovery_id = "DISC-" + sha256_text(url)[:12].upper()
            prid_match = re.search(r"PRID=(\d+)", url, flags=re.I)

            new_rows.append({
                "discovery_id": discovery_id,
                "source_id": source_id,
                "source_name": source_name,
                "title": item["title"],
                "url": url,
                "pib_release_id": prid_match.group(1) if prid_match else "",
                "published_at": item["published_at"],
                "discovered_at": discovered_at,
                "candidate_score": score,
                "semiconductor_keyword_hits": " | ".join(semiconductor_hits),
                "approval_keyword_hits": " | ".join(approval_hits),
                "negative_keyword_hits": " | ".join(negative_hits),
                "candidate_status": "NEW_REVIEW_REQUIRED",
                "verification_status": "UNVERIFIED_DISCOVERY",
                "canonicalization_status": "NOT_STARTED",
                "model_evaluation_status": "NOT_STARTED",
                "content_sha256": content_hash,
                "article_excerpt": combined[:1500],
            })
            existing_urls.add(url)
            existing_hashes.add(content_hash)

    columns = [
        "discovery_id",
        "source_id",
        "source_name",
        "title",
        "url",
        "pib_release_id",
        "published_at",
        "discovered_at",
        "candidate_score",
        "semiconductor_keyword_hits",
        "approval_keyword_hits",
        "negative_keyword_hits",
        "candidate_status",
        "verification_status",
        "canonicalization_status",
        "model_evaluation_status",
        "content_sha256",
        "article_excerpt",
    ]

    new_df = pd.DataFrame(new_rows, columns=columns)
    if existing.empty:
        combined_df = new_df
    elif new_df.empty:
        combined_df = existing
    else:
        combined_df = pd.concat([existing, new_df], ignore_index=True, sort=False)

    if combined_df.empty:
        pd.DataFrame(columns=columns).to_csv(candidates_path, index=False)
    else:
        combined_df.to_csv(candidates_path, index=False, quoting=csv.QUOTE_MINIMAL)

    audit = {
        "pipeline_version": config.get("pipeline_version"),
        "run_at": discovered_at,
        "rss_sources": int(len(rss_sources)),
        "rss_items_scanned": rss_items_scanned,
        "articles_fetched": fetched_articles,
        "new_candidates": int(len(new_df)),
        "total_candidates": int(len(combined_df)),
        "canonical_project_count": canonical_project_count(config),
        "errors": errors,
    }
    append_audit(audit_path, audit)

    print("SEMICONDUCTOR PROJECT DISCOVERY")
    print("=" * 60)
    print(f"RSS sources             : {len(rss_sources)}")
    print(f"RSS items scanned       : {rss_items_scanned}")
    print(f"Articles fetched        : {fetched_articles}")
    print(f"New candidates          : {len(new_df)}")
    print(f"Total candidate register: {len(combined_df)}")
    print(f"Canonical projects      : {audit['canonical_project_count']}")
    print(f"Errors                  : {len(errors)}")
    print(f"Candidate register      : {candidates_path.relative_to(ROOT)}")
    print(f"Audit log               : {audit_path.relative_to(ROOT)}")

    if not new_df.empty:
        print("\nNEW CANDIDATES")
        for _, row in new_df.iterrows():
            print(f"- {row['discovery_id']} | score={row['candidate_score']} | {row['title']}")

    if errors:
        print("\nNON-FATAL ERRORS")
        for err in errors:
            print(f"- {err}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
