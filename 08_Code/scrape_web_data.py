"""Download public macro, trade, policy, and listed-company data.

Sources are official APIs or public pages. Failures are logged and do not
stop the rest of the pipeline.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from config import COMTRADE_HS, LISTED_TICKERS, WEB_RAW, WORLD_BANK_INDICATORS

HEADERS = {
    "User-Agent": (
        "SemiconductorCreditRiskResearch/1.0 "
        "(academic; contact: local-research)"
    )
}
TIMEOUT = 45


def _save_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _get(url: str, **kwargs) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as exc:
        print(f"  [skip] {url[:90]} ... ({exc})")
        return None


def scrape_world_bank() -> pd.DataFrame:
    rows = []
    for name, code in WORLD_BANK_INDICATORS.items():
        url = (
            f"https://api.worldbank.org/v2/country/IND/indicator/{code}"
            "?format=json&per_page=80"
        )
        r = _get(url)
        if r is None:
            continue
        payload = r.json()
        _save_json(payload, WEB_RAW / "worldbank" / f"{code}.json")
        if not isinstance(payload, list) or len(payload) < 2:
            continue
        for rec in payload[1] or []:
            if rec.get("value") is None:
                continue
            rows.append(
                {
                    "source": "World Bank Open Data",
                    "indicator": name,
                    "indicator_code": code,
                    "year": int(rec["date"]),
                    "value": float(rec["value"]),
                    "country": rec.get("countryiso3code", "IND"),
                }
            )
        time.sleep(0.2)
    df = pd.DataFrame(rows)
    df.to_csv(WEB_RAW / "worldbank_india_macro_long.csv", index=False)
    return df


def scrape_imf_gdp() -> pd.DataFrame:
    url = "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/IND"
    r = _get(url)
    if r is None:
        return pd.DataFrame()
    payload = r.json()
    _save_json(payload, WEB_RAW / "imf_ngdp_rpch_ind.json")
    values = payload.get("values", {}).get("NGDP_RPCH", {}).get("IND", {})
    df = pd.DataFrame(
        [
            {"source": "IMF DataMapper", "indicator": "gdp_growth_imf", "year": int(y), "value": float(v)}
            for y, v in values.items()
            if v not in (None, "")
        ]
    )
    df.to_csv(WEB_RAW / "imf_india_gdp_growth.csv", index=False)
    return df


def scrape_fred_india_policy_rate() -> pd.DataFrame:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=INTGSTINM193N"
    r = _get(url)
    if r is None:
        return pd.DataFrame()
    path = WEB_RAW / "fred_india_policy_rate.csv"
    path.write_bytes(r.content)
    df = pd.read_csv(path)
    df.to_csv(path, index=False)
    return df


def scrape_un_comtrade() -> pd.DataFrame:
    """India annual imports/exports of diodes/transistors (8541) and ICs (8542)."""
    frames = []
    for hs in COMTRADE_HS:
        for flow in ("M", "X"):
            url = (
                "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
                f"?reporterCode=699&period=2019,2020,2021,2022,2023,2024,2025"
                f"&partnerCode=0&cmdCode={hs}&flowCode={flow}&motCode=0"
            )
            r = _get(url)
            if r is None:
                continue
            payload = r.json()
            _save_json(payload, WEB_RAW / "comtrade" / f"{hs}_{flow}.json")
            data = payload.get("data") or payload.get("dataset") or []
            if isinstance(data, dict):
                data = [data]
            tmp = pd.DataFrame(data)
            if not tmp.empty:
                tmp["hs_code"] = hs
                tmp["flow"] = "import" if flow == "M" else "export"
                frames.append(tmp)
            time.sleep(0.4)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(WEB_RAW / "un_comtrade_semiconductor_trade_raw.csv", index=False)
    return df


def scrape_yahoo_fundamentals() -> pd.DataFrame:
    rows = []
    for company, ticker in LISTED_TICKERS.items():
        url = (
            "https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
            f"{ticker}?modules=financialData,defaultKeyStatistics,price,summaryDetail"
        )
        r = _get(url)
        if r is None:
            continue
        payload = r.json()
        _save_json(payload, WEB_RAW / "yahoo" / f"{ticker.replace('.', '_')}.json")
        try:
            res = payload["quoteSummary"]["result"][0]
        except (KeyError, IndexError, TypeError):
            continue
        fd = (res.get("financialData") or {})
        ks = (res.get("defaultKeyStatistics") or {})
        px = (res.get("price") or {})
        sd = (res.get("summaryDetail") or {})

        def num(block, key):
            node = (block or {}).get(key) or {}
            return node.get("raw") if isinstance(node, dict) else None

        rows.append(
            {
                "company": company,
                "ticker": ticker,
                "currency": px.get("currency"),
                "market_cap": num(px, "marketCap") or num(sd, "marketCap"),
                "enterprise_value": num(ks, "enterpriseValue"),
                "total_revenue": num(fd, "totalRevenue"),
                "ebitda": num(fd, "ebitda"),
                "total_debt": num(fd, "totalDebt"),
                "total_cash": num(fd, "totalCash"),
                "debt_equity": num(fd, "debtToEquity"),
                "current_ratio": num(fd, "currentRatio"),
                "interest_coverage": num(fd, "interestCoverage"),
                "return_on_assets": num(fd, "returnOnAssets"),
                "return_on_equity": num(fd, "returnOnEquity"),
                "operating_cashflow": num(fd, "operatingCashflow"),
                "free_cashflow": num(fd, "freeCashflow"),
                "profit_margins": num(fd, "profitMargins"),
                "asof_utc": datetime.now(timezone.utc).isoformat(),
                "source": "Yahoo Finance quoteSummary",
            }
        )
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df.to_csv(WEB_RAW / "listed_company_financials.csv", index=False)
    return df


def scrape_policy_pages() -> pd.DataFrame:
    urls = [
        "https://ism.gov.in/",
        "https://www.meity.gov.in/semiconindia",
        "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc202627782101.pdf",
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2083707",
        "https://sansad.in/getFile/lsapps/loksabhaquestions/annex/188/AU483_2k5xlV.pdf",
    ]
    rows = []
    for url in urls:
        r = _get(url)
        status = None if r is None else r.status_code
        n = 0 if r is None else len(r.content)
        slug = url.split("//", 1)[-1].replace("/", "_")[:80]
        if r is not None:
            (WEB_RAW / "policy").mkdir(parents=True, exist_ok=True)
            (WEB_RAW / "policy" / slug).write_bytes(r.content)
        rows.append({"url": url, "http_status": status, "bytes": n, "ok": r is not None})
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df.to_csv(WEB_RAW / "policy_page_fetch_log.csv", index=False)
    return df


def scrape_india_semiconductor_market_notes() -> pd.DataFrame:
    """Public market-size anchors cited in PIB / MeitY (USD billion)."""
    df = pd.DataFrame(
        [
            {"year": 2023, "india_semiconductor_market_usd_bn": 38.0, "source": "PIB ISM 2.0 note Feb 2026 citing industry estimates"},
            {"year": 2024, "india_semiconductor_market_usd_bn": 47.5, "source": "PIB range $45-50bn for 2024-25 (midpoint)"},
            {"year": 2025, "india_semiconductor_market_usd_bn": 47.5, "source": "PIB range $45-50bn for 2024-25 (midpoint)"},
            {"year": 2030, "india_semiconductor_market_usd_bn": 105.0, "source": "PIB $100-110bn by 2030 (midpoint)"},
        ]
    )
    df.to_csv(WEB_RAW / "india_semiconductor_market_anchors.csv", index=False)
    return df


def run_all_scrapers() -> dict[str, pd.DataFrame]:
    print("Scraping World Bank...")
    wb = scrape_world_bank()
    print("Scraping IMF DataMapper...")
    imf = scrape_imf_gdp()
    print("Scraping FRED India policy rate...")
    fred = scrape_fred_india_policy_rate()
    print("Scraping UN Comtrade HS 8541/8542...")
    trade = scrape_un_comtrade()
    print("Scraping Yahoo Finance listed-company financials...")
    yf = scrape_yahoo_fundamentals()
    print("Fetching ISM / MeitY / PIB / Sansad pages...")
    policy = scrape_policy_pages()
    mkt = scrape_india_semiconductor_market_notes()
    print(
        f"Done scrape: WB rows={len(wb)}, IMF={len(imf)}, FRED={len(fred)}, "
        f"Comtrade={len(trade)}, Yahoo={len(yf)}, policy={len(policy)}"
    )
    return {
        "world_bank": wb,
        "imf": imf,
        "fred": fred,
        "comtrade": trade,
        "yahoo": yf,
        "policy": policy,
        "market": mkt,
    }


if __name__ == "__main__":
    run_all_scrapers()
