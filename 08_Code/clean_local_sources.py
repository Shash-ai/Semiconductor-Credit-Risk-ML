"""Clean local RBI, IIP, rates, semiconductor projects, and scraped files."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from config import (
    AS_OF_YEAR,
    ASSUMED_DEBT_SHARE,
    ASSUMED_TENOR_YEARS,
    CLEAN,
    PANEL_YEARS,
    RAW,
    WEB_RAW,
)

warnings.filterwarnings("ignore", category=UserWarning)


def _to_num(s):
    return pd.to_numeric(s, errors="coerce")


def clean_projects() -> pd.DataFrame:
    path = RAW / "Semiconductor/Semiconductor_Master/Semiconductor_Master_Canonical.csv"
    df = pd.read_csv(path)
    df["approval_date"] = pd.to_datetime(df["approval_date"], errors="coerce")
    df["approval_year"] = _to_num(df["approval_year"]).astype(int)
    df["investment_crore"] = _to_num(df["investment_crore"])
    df["capacity_value"] = _to_num(df["capacity_value"])
    df["has_technology_partner"] = df["technology_partner"].fillna("").str.strip().ne("").astype(int)
    df["commercial_production_flag"] = df["company"].map(
        lambda c: int(any(k in str(c) for k in ("Micron", "Kaynes", "CG Power")))
    )
    df["semicon_scheme"] = "ISM_1.0_approved_pipeline"
    df["policy_regime"] = np.where(df["approval_year"] >= 2026, "Semicon_2.0", "Semicon_India_1.0")
    out = CLEAN / "Industry" / "Semiconductor_Projects_Clean.csv"
    df.to_csv(out, index=False)
    return df


def clean_rbi_sectoral_credit() -> pd.DataFrame:
    long = pd.read_csv(CLEAN / "RBI_Sectoral_Credit_Long_2019_2026.csv")
    long["sector"] = long["sector"].astype(str).str.strip()
    long["year"] = _to_num(long["year"]).astype(int)
    long["credit_crore"] = _to_num(long["credit_crore"])
    focus = long[long["sector"].isin(["Electronics", "All Engineering", "Industries (2.1 to 2.19)"])].copy()
    wide = focus.pivot_table(index="year", columns="sector", values="credit_crore", aggfunc="first").reset_index()
    wide = wide.rename(
        columns={
            "Electronics": "electronics_credit_crore",
            "All Engineering": "engineering_credit_crore",
            "Industries (2.1 to 2.19)": "industry_credit_crore",
        }
    )
    wide = wide.sort_values("year")
    for col in ["electronics_credit_crore", "engineering_credit_crore", "industry_credit_crore"]:
        if col in wide:
            wide[f"{col.replace('_crore', '')}_yoy_pct"] = wide[col].pct_change() * 100
    wide["electronics_credit_share_of_industry"] = (
        wide["electronics_credit_crore"] / wide["industry_credit_crore"]
    )
    wide["electronics_credit_growth_vol_3y"] = (
        wide["electronics_credit_yoy_pct"].rolling(3, min_periods=2).std()
    )
    wide.to_csv(CLEAN / "Banking" / "RBI_Sectoral_Credit_Focus_Yearly.csv", index=False)
    long.to_csv(CLEAN / "Banking" / "RBI_Sectoral_Credit_Long_Clean.csv", index=False)
    return wide


def clean_npa() -> pd.DataFrame:
    npa = pd.read_csv(
        RAW / "Semiconductor/Semiconductor_Master/RBI_NPA_Year_Level_Stress_Features.csv"
    )
    npa["year"] = _to_num(npa["year"]).astype(int)
    npa = npa[npa["year"].between(min(PANEL_YEARS) - 1, AS_OF_YEAR)].copy()
    npa.to_csv(CLEAN / "Banking" / "RBI_NPA_Yearly_Clean.csv", index=False)
    return npa


def clean_repo_rates() -> pd.DataFrame:
    path = (
        RAW
        / "Interest_Rates"
        / "Major Monetary Policy Rates and Reserve Requirements - Bank Rate, LAF (Repo, Reverse Repo, SDF and MSF) Rates, CRR & SLR.xlsx"
    )
    raw = pd.read_excel(path, header=None)
    body = raw.iloc[8:, 1:9].copy()
    body.columns = [
        "effective_date",
        "bank_rate",
        "repo_rate",
        "reverse_repo_rate",
        "sdf_rate",
        "msf_rate",
        "crr",
        "slr",
    ]
    body["effective_date"] = pd.to_datetime(body["effective_date"], errors="coerce")
    for c in body.columns[1:]:
        body[c] = _to_num(body[c].replace("-", np.nan))
    body = body.dropna(subset=["effective_date"]).sort_values("effective_date")
    body.to_csv(CLEAN / "Macro" / "RBI_Policy_Rates_Daily.csv", index=False)

    cal = pd.DataFrame({"asof": pd.date_range("2019-01-01", f"{AS_OF_YEAR}-12-31", freq="D")})
    merged = pd.merge_asof(
        cal.sort_values("asof"),
        body.sort_values("effective_date"),
        left_on="asof",
        right_on="effective_date",
        direction="backward",
    )
    yearly = (
        merged.assign(year=merged["asof"].dt.year)
        .groupby("year", as_index=False)
        .agg(
            repo_rate=("repo_rate", "last"),
            bank_rate=("bank_rate", "last"),
            sdf_rate=("sdf_rate", "last"),
            msf_rate=("msf_rate", "last"),
            crr=("crr", "last"),
            slr=("slr", "last"),
            repo_rate_avg=("repo_rate", "mean"),
        )
    )
    yearly.to_csv(CLEAN / "Macro" / "RBI_Policy_Rates_Yearly.csv", index=False)
    return yearly


def clean_walr() -> pd.DataFrame:
    path = RAW / "Interest_Rates" / "Weighted Average Lending Rate.xlsx"
    raw = pd.read_excel(path, sheet_name="Sector Wise", header=None)
    body = raw.iloc[7:, 1:].copy()
    body = body.dropna(how="all")
    # Year, then share/WALR pairs
    recs = []
    for _, row in body.iterrows():
        year = pd.to_numeric(row.iloc[0], errors="coerce")
        if pd.isna(year):
            continue
        recs.append(
            {
                "year": int(year),
                "industry_credit_share_pct": pd.to_numeric(row.iloc[5], errors="coerce"),
                "industry_walr_pct": pd.to_numeric(row.iloc[6], errors="coerce"),
                "all_sector_walr_pct": pd.to_numeric(row.iloc[-1], errors="coerce"),
            }
        )
    df = pd.DataFrame(recs).drop_duplicates("year").sort_values("year")
    df.to_csv(CLEAN / "Banking" / "WALR_Industry_Yearly.csv", index=False)
    return df


def _melt_iip(sheet: str, name_col: str) -> pd.DataFrame:
    path = RAW / "Industrial_Production" / "IIP_Dashboard Data_Jun2026-28.07.2026.xlsx"
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    header = raw.iloc[0]
    cats = raw.iloc[1:].copy()
    cats.columns = header
    id_cols = [cats.columns[0], cats.columns[1]]
    long = cats.melt(id_vars=id_cols, var_name="period", value_name="yoy_growth_pct")
    long.columns = [name_col, "weight", "period", "yoy_growth_pct"]
    long["yoy_growth_pct"] = _to_num(long["yoy_growth_pct"])
    long["weight"] = _to_num(long["weight"])
    return long.dropna(subset=["period"])


def clean_iip() -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly = _melt_iip("UBC-Monthly", "use_based_category")
    monthly["period"] = pd.to_datetime(monthly["period"], errors="coerce")
    monthly["year"] = monthly["period"].dt.year
    monthly.to_csv(CLEAN / "Macro" / "IIP_UBC_Monthly_Clean.csv", index=False)

    yearly = (
        monthly.dropna(subset=["year"])
        .groupby(["year", "use_based_category"], as_index=False)
        .agg(iip_yoy_avg=("yoy_growth_pct", "mean"), iip_yoy_last=("yoy_growth_pct", "last"))
    )
    pivot = yearly.pivot_table(index="year", columns="use_based_category", values="iip_yoy_avg")
    pivot.columns = [
        "iip_" + str(c).lower().replace(" ", "_").replace("/", "_") + "_yoy_avg"
        for c in pivot.columns
    ]
    pivot = pivot.reset_index()

    annual = pd.read_excel(
        RAW / "Industrial_Production" / "IIP_Dashboard Data_Jun2026-28.07.2026.xlsx",
        sheet_name="Sectoral-Annual",
        header=0,
    )
    # columns: Description, Weights, 2023-24, ...
    recs = []
    for col in annual.columns[2:]:
        fy = str(col)
        end_year = int(str(fy).split("-")[0]) + 1 if "-" in str(fy) else None
        row = annual.set_index(annual.columns[0])[col]
        recs.append(
            {
                "year": end_year,
                "fiscal_year": fy,
                "iip_general_fy": pd.to_numeric(row.get("General"), errors="coerce"),
                "iip_manufacturing_fy": pd.to_numeric(row.get("Manufacturing"), errors="coerce"),
            }
        )
    fy_df = pd.DataFrame(recs)
    pivot = pivot.merge(fy_df, on="year", how="left")
    pivot.to_csv(CLEAN / "Macro" / "IIP_Yearly_Clean.csv", index=False)
    return monthly, pivot


def clean_world_bank() -> pd.DataFrame:
    path = WEB_RAW / "worldbank_india_macro_long.csv"
    if not path.exists():
        return pd.DataFrame({"year": PANEL_YEARS})
    long = pd.read_csv(path)
    wide = long.pivot_table(index="year", columns="indicator", values="value", aggfunc="last").reset_index()
    wide.to_csv(CLEAN / "Macro" / "WorldBank_India_Macro_Yearly.csv", index=False)
    return wide


def clean_imf() -> pd.DataFrame:
    path = WEB_RAW / "imf_india_gdp_growth.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path).rename(columns={"value": "gdp_growth_imf"})
    df.to_csv(CLEAN / "Macro" / "IMF_India_GDP_Growth.csv", index=False)
    return df[["year", "gdp_growth_imf"]]


def clean_comtrade() -> pd.DataFrame:
    path = WEB_RAW / "un_comtrade_semiconductor_trade_raw.csv"
    if not path.exists():
        return pd.DataFrame({"year": PANEL_YEARS})
    raw = pd.read_csv(path)
    year_col = next((c for c in raw.columns if c.lower() in {"period", "refyear", "year"}), None)
    val_col = next(
        (c for c in raw.columns if c.lower() in {"primaryvalue", "tradevalue", "tradevalueus", "cifvalue"}),
        None,
    )
    if year_col is None:
        return pd.DataFrame({"year": PANEL_YEARS})
    tmp = raw.copy()
    tmp["year"] = _to_num(tmp[year_col]).astype("Int64")
    if val_col:
        tmp["trade_usd"] = _to_num(tmp[val_col])
    else:
        tmp["trade_usd"] = np.nan
    flow_col = "flow" if "flow" in tmp.columns else None
    hs_col = "hs_code" if "hs_code" in tmp.columns else next((c for c in tmp.columns if "cmd" in c.lower()), None)
    grp = tmp.dropna(subset=["year"]).groupby(["year", flow_col or "flow", hs_col or "hs_code"], as_index=False)[
        "trade_usd"
    ].sum()
    if flow_col:
        wide = grp.pivot_table(
            index="year",
            columns=[flow_col, hs_col] if hs_col else flow_col,
            values="trade_usd",
            aggfunc="sum",
        )
        wide.columns = ["_".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in wide.columns]
        wide = wide.reset_index()
    else:
        wide = grp
    # convenient totals
    imp = [c for c in wide.columns if str(c).startswith("import")]
    exp = [c for c in wide.columns if str(c).startswith("export")]
    if imp:
        wide["semicon_imports_usd"] = wide[imp].sum(axis=1)
    if exp:
        wide["semicon_exports_usd"] = wide[exp].sum(axis=1)
    if "semicon_imports_usd" in wide and "semicon_exports_usd" in wide:
        wide["semicon_trade_balance_usd"] = wide["semicon_exports_usd"] - wide["semicon_imports_usd"]
        wide["import_dependence_ratio"] = wide["semicon_imports_usd"] / (
            wide["semicon_imports_usd"] + wide["semicon_exports_usd"]
        )
    wide.to_csv(CLEAN / "Industry" / "UN_Comtrade_Semiconductor_Yearly.csv", index=False)
    return wide


def clean_company_financials(projects: pd.DataFrame) -> pd.DataFrame:
    path = WEB_RAW / "listed_company_financials.csv"
    if path.exists() and path.stat().st_size > 0:
        fin = pd.read_csv(path)
    else:
        fin = pd.DataFrame(columns=["company"])
    base = projects[["project_id", "company"]].copy()
    merged = base.merge(fin, on="company", how="left")
    merged["listed_financials_available"] = merged.get("ticker", pd.Series(index=merged.index)).notna().astype(int)
    if "debt_equity" in merged:
        merged["debt_equity"] = _to_num(merged["debt_equity"])
        # Yahoo often stores D/E * 100
        merged["debt_equity_ratio"] = np.where(
            merged["debt_equity"] > 5, merged["debt_equity"] / 100.0, merged["debt_equity"]
        )
    else:
        merged["debt_equity_ratio"] = np.nan
    merged["assumed_project_debt_crore"] = projects.set_index("project_id").loc[
        merged["project_id"], "investment_crore"
    ].values * ASSUMED_DEBT_SHARE
    merged["assumed_loan_tenor_years"] = ASSUMED_TENOR_YEARS
    merged.to_csv(CLEAN / "Company_Financials" / "Project_Company_Financials_Clean.csv", index=False)
    return merged


def clean_market_anchors() -> pd.DataFrame:
    path = WEB_RAW / "india_semiconductor_market_anchors.csv"
    if not path.exists():
        return pd.DataFrame({"year": PANEL_YEARS})
    df = pd.read_csv(path)
    # interpolate 2019-2026 using 2023 and 2024/25 anchors
    years = pd.DataFrame({"year": PANEL_YEARS})
    known = df[df["year"] <= AS_OF_YEAR][["year", "india_semiconductor_market_usd_bn"]]
    years = years.merge(known, on="year", how="left")
    years["india_semiconductor_market_usd_bn"] = years["india_semiconductor_market_usd_bn"].interpolate(
        limit_direction="both"
    )
    years.to_csv(CLEAN / "Industry" / "India_Semiconductor_Market_Yearly.csv", index=False)
    return years


def build_year_panel() -> pd.DataFrame:
    credit = pd.read_csv(CLEAN / "Banking" / "RBI_Sectoral_Credit_Focus_Yearly.csv")
    npa = pd.read_csv(CLEAN / "Banking" / "RBI_NPA_Yearly_Clean.csv")
    repo = pd.read_csv(CLEAN / "Macro" / "RBI_Policy_Rates_Yearly.csv")
    iip = pd.read_csv(CLEAN / "Macro" / "IIP_Yearly_Clean.csv")
    wb = pd.read_csv(CLEAN / "Macro" / "WorldBank_India_Macro_Yearly.csv") if (
        CLEAN / "Macro" / "WorldBank_India_Macro_Yearly.csv"
    ).exists() else pd.DataFrame({"year": PANEL_YEARS})
    imf_path = CLEAN / "Macro" / "IMF_India_GDP_Growth.csv"
    imf = pd.read_csv(imf_path) if imf_path.exists() else pd.DataFrame({"year": PANEL_YEARS})
    walr = pd.read_csv(CLEAN / "Banking" / "WALR_Industry_Yearly.csv")
    mkt = pd.read_csv(CLEAN / "Industry" / "India_Semiconductor_Market_Yearly.csv")
    trade_path = CLEAN / "Industry" / "UN_Comtrade_Semiconductor_Yearly.csv"
    trade = pd.read_csv(trade_path) if trade_path.exists() else pd.DataFrame({"year": PANEL_YEARS})

    panel = pd.DataFrame({"year": PANEL_YEARS})
    for df in (credit, npa, repo, iip, wb, imf, walr, mkt, trade):
        if "year" not in df.columns:
            continue
        panel = panel.merge(df, on="year", how="left")

    if "gdp_growth" not in panel and "gdp_growth_imf" in panel:
        panel["gdp_growth"] = panel["gdp_growth_imf"]
    elif "gdp_growth" in panel and "gdp_growth_imf" in panel:
        panel["gdp_growth"] = panel["gdp_growth"].fillna(panel["gdp_growth_imf"])

    # last-observation carry-forward for lagging official releases
    panel = panel.sort_values("year")
    panel.to_csv(CLEAN / "Master" / "Yearly_Macro_Banking_Industry_Panel.csv", index=False)
    return panel


def run_cleaning() -> dict[str, pd.DataFrame]:
    projects = clean_projects()
    credit = clean_rbi_sectoral_credit()
    npa = clean_npa()
    repo = clean_repo_rates()
    walr = clean_walr()
    _, iip = clean_iip()
    wb = clean_world_bank()
    imf = clean_imf()
    trade = clean_comtrade()
    mkt = clean_market_anchors()
    fin = clean_company_financials(projects)
    panel = build_year_panel()
    print(
        f"Cleaned projects={len(projects)}, credit years={len(credit)}, "
        f"panel={panel.shape}, financials={fin['listed_financials_available'].sum()} listed"
    )
    return {
        "projects": projects,
        "credit": credit,
        "npa": npa,
        "repo": repo,
        "walr": walr,
        "iip": iip,
        "wb": wb,
        "imf": imf,
        "trade": trade,
        "market": mkt,
        "financials": fin,
        "panel": panel,
    }


if __name__ == "__main__":
    run_cleaning()
