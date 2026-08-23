"""EDA tables plus feature engineering and the master modelling datasets."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from config import AS_OF_YEAR, ASSUMED_DEBT_SHARE, ASSUMED_TENOR_YEARS, CLEAN, EDA_DIR, MASTER_DIR, PANEL_YEARS


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def run_eda(projects: pd.DataFrame, panel: pd.DataFrame) -> dict:
    EDA_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "n_projects": int(len(projects)),
        "total_investment_crore": float(projects["investment_crore"].sum()),
        "states": projects["state"].nunique(),
        "project_groups": projects["project_group"].value_counts().to_dict(),
        "investment_by_state": projects.groupby("state")["investment_crore"].sum().to_dict(),
        "investment_by_group": projects.groupby("project_group")["investment_crore"].sum().to_dict(),
        "panel_years": PANEL_YEARS,
        "electronics_credit_latest": float(panel.set_index("year")["electronics_credit_crore"].dropna().iloc[-1])
        if "electronics_credit_crore" in panel
        else None,
    }
    (EDA_DIR / "eda_headline_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    miss = panel.isna().mean().sort_values(ascending=False).rename("missing_share").reset_index()
    miss.columns = ["column", "missing_share"]
    miss.to_csv(EDA_DIR / "yearly_panel_missingness.csv", index=False)

    corr_cols = [
        c
        for c in [
            "electronics_credit_crore",
            "electronics_credit_yoy_pct",
            "total_gross_npa_closing_crore",
            "gross_npa_growth_pct",
            "repo_rate",
            "gdp_growth",
            "cpi_inflation",
            "iip_capital_goods_yoy_avg",
            "india_semiconductor_market_usd_bn",
        ]
        if c in panel.columns
    ]
    if corr_cols:
        panel[corr_cols].corr().to_csv(EDA_DIR / "yearly_panel_correlations.csv")

    projects.groupby(["state", "project_group"], as_index=False).agg(
        n=("project_id", "count"), investment_crore=("investment_crore", "sum")
    ).to_csv(EDA_DIR / "projects_by_state_group.csv", index=False)
    return summary


def engineer_project_features(projects: pd.DataFrame) -> pd.DataFrame:
    df = projects.copy()
    df["investment_log"] = np.log(df["investment_crore"].clip(lower=1))
    df["capacity_log"] = np.log(df["capacity_value"].clip(lower=0.01))
    df["investment_rank"] = df["investment_crore"].rank(ascending=False)
    df["is_fab"] = df["project_group"].eq("Fabrication").astype(int)
    df["is_osat"] = df["project_type_standardized"].eq("OSAT").astype(int)
    df["is_atmp"] = df["project_type_standardized"].eq("ATMP").astype(int)
    df["is_advanced_packaging"] = df["project_group"].eq("Advanced_Packaging").astype(int)
    df["is_sic"] = df["technology"].fillna("").str.contains("SiC|Silicon Carbide", case=False).astype(int)
    df["years_since_approval"] = AS_OF_YEAR - df["approval_year"]
    df["state_project_count"] = df.groupby("state")["project_id"].transform("count")
    df["state_total_investment"] = df.groupby("state")["investment_crore"].transform("sum")
    df["state_investment_share"] = df["state_total_investment"] / df["investment_crore"].sum()
    df["company_project_count"] = df.groupby("company")["project_id"].transform("count")
    df["project_complexity"] = (
        df["is_fab"] * 3 + df["is_sic"] * 2 + df["is_advanced_packaging"] * 2 + df["is_osat"] + df["is_atmp"]
    )
    df["capex_intensity"] = df["investment_crore"] / df["capacity_value"].replace(0, np.nan)
    df["mega_project_flag"] = df["investment_category"].eq("Mega").astype(int)
    df["cluster_gujarat_flag"] = df["state"].eq("Gujarat").astype(int)
    return df


def build_master_datasets(projects_feat: pd.DataFrame, panel: pd.DataFrame, financials: pd.DataFrame):
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    year_map = panel.set_index("year")

    def attach_year(df, year_col, prefix):
        out = df.copy()
        keys = year_map.columns
        pulled = year_map.reindex(out[year_col]).reset_index(drop=True)
        pulled.columns = [f"{prefix}{c}" if c != "year" else f"{prefix}year" for c in pulled.columns]
        return pd.concat([out.reset_index(drop=True), pulled], axis=1)

    project_level = attach_year(projects_feat, "approval_year", "ay_")
    project_level["latest_year"] = AS_OF_YEAR
    latest = year_map.reindex(project_level["latest_year"]).reset_index(drop=True)
    latest.columns = [f"lt_{c}" if c != "year" else "lt_year" for c in latest.columns]
    project_level = pd.concat([project_level.reset_index(drop=True), latest], axis=1)

    fin_cols = [
        c
        for c in financials.columns
        if c
        not in {
            "company",
        }
    ]
    project_level = project_level.merge(
        financials[["project_id"] + [c for c in fin_cols if c != "project_id"]],
        on="project_id",
        how="left",
        suffixes=("", "_fin"),
    )

    # Bank-exposure proxies (no loan-level RBI borrower file exists in public domain)
    elec = project_level.get("lt_electronics_credit_crore", project_level.get("ay_electronics_credit_crore"))
    project_level["rbi_electronics_credit_crore_latest"] = elec
    project_level["project_share_of_electronics_credit"] = project_level["investment_crore"] / elec
    project_level["implied_bank_exposure_crore"] = project_level["investment_crore"] * ASSUMED_DEBT_SHARE
    project_level["sector_exposure_proxy_crore"] = elec
    project_level["exposure_concentration_index"] = (
        project_level["implied_bank_exposure_crore"] / project_level["implied_bank_exposure_crore"].sum()
    )
    walr = project_level.get("lt_industry_walr_pct", project_level.get("ay_industry_walr_pct"))
    project_level["interest_rate_proxy_walr"] = walr
    project_level["loan_tenor_years_assumed"] = ASSUMED_TENOR_YEARS
    project_level["default_status"] = 0  # no ISM project default observed in public sources
    project_level["npa_status"] = 0
    gnpa = project_level.get("lt_net_to_gross_npa_ratio")
    project_level["banking_npa_stress"] = gnpa
    project_level["electronics_credit_stress"] = (
        (project_level.get("lt_electronics_credit_yoy_pct") < 0).astype(float)
        if "lt_electronics_credit_yoy_pct" in project_level
        else np.nan
    )
    # Composite banking-stress score 0-1 using latest NPA addition pressure + GNPA trend
    add_p = _num(project_level.get("lt_npa_addition_pressure"))
    npa_g = _num(project_level.get("lt_gross_npa_growth_pct"))
    project_level["banking_stress_score"] = (
        0.5 * add_p.clip(0, 1) + 0.5 * ((npa_g + 50) / 100).clip(0, 1)
    )

    project_level["target_investment_exposure"] = (
        project_level["investment_crore"] / project_level["investment_crore"].sum()
    )
    project_level["modelling_universe"] = "ISM_approved_projects"
    project_level["unit_of_analysis"] = "project"
    project_level["data_cutoff_year"] = AS_OF_YEAR

    project_level.to_csv(MASTER_DIR / "Master_Modelling_Dataset_Project_Level.csv", index=False)

    # Project-year panel for later stress testing (macros vary; project traits fixed)
    rows = []
    for _, proj in projects_feat.iterrows():
        for y in PANEL_YEARS:
            if y < proj["approval_year"]:
                continue
            rec = proj.to_dict()
            rec["year"] = y
            rec["years_on_book"] = y - proj["approval_year"]
            rows.append(rec)
    panel_py = pd.DataFrame(rows)
    panel_py = panel_py.merge(panel, on="year", how="left", suffixes=("", "_y"))
    panel_py = panel_py.merge(
        financials[["project_id"] + [c for c in fin_cols if c != "project_id"]],
        on="project_id",
        how="left",
    )
    panel_py["implied_bank_exposure_crore"] = panel_py["investment_crore"] * ASSUMED_DEBT_SHARE
    if "electronics_credit_crore" in panel_py:
        panel_py["project_share_of_electronics_credit"] = (
            panel_py["investment_crore"] / panel_py["electronics_credit_crore"]
        )
    panel_py.to_csv(MASTER_DIR / "Master_Modelling_Dataset_Project_Year_Panel.csv", index=False)

    # ML-ready numeric matrix (NO target leakage from future models; keep raw scale)
    id_cols = ["project_id", "company", "state", "project_group", "project_type", "approval_year"]
    numeric = project_level.select_dtypes(include=[np.number]).copy()
    ml = pd.concat([project_level[id_cols].reset_index(drop=True), numeric.reset_index(drop=True)], axis=1)
    ml = ml.loc[:, ~ml.columns.duplicated()]
    ml.to_csv(MASTER_DIR / "Master_ML_Ready_Unscaled.csv", index=False)

    dictionary = []
    for col in project_level.columns:
        dictionary.append(
            {
                "dataset": "Master_Modelling_Dataset_Project_Level",
                "column": col,
                "dtype": str(project_level[col].dtype),
                "non_null": int(project_level[col].notna().sum()),
                "missing_share": float(project_level[col].isna().mean()),
            }
        )
    pd.DataFrame(dictionary).to_csv(MASTER_DIR / "Master_Data_Dictionary.csv", index=False)

    coverage = pd.DataFrame(
        [
            {"domain": "Semiconductor Project", "status": "complete", "n_vars": int(projects_feat.shape[1])},
            {
                "domain": "Macroeconomic",
                "status": "complete_with_official_lag",
                "n_vars": int(sum(c.startswith("lt_") or c.startswith("ay_") for c in project_level.columns)),
            },
            {"domain": "RBI sectoral credit / NPA", "status": "complete", "n_vars": 8},
            {
                "domain": "Company Financials",
                "status": "listed_only_yahoo",
                "n_listed": int(project_level.get("listed_financials_available", pd.Series(dtype=int)).sum()),
            },
            {
                "domain": "Bank Exposure",
                "status": "public_proxy_only",
                "note": f"loan-level books not disclosed; debt share assumed {ASSUMED_DEBT_SHARE:.0%}",
            },
            {"domain": "Semiconductor industry / trade", "status": "comtrade_plus_pib_anchors", "n_vars": 4},
        ]
    )
    coverage.to_csv(MASTER_DIR / "Master_Domain_Coverage.csv", index=False)

    qa = pd.DataFrame(
        [
            {
                "file": "Master_Modelling_Dataset_Project_Level.csv",
                "rows": len(project_level),
                "columns": project_level.shape[1],
                "missing_cells": int(project_level.isna().sum().sum()),
                "duplicate_project_ids": int(project_level["project_id"].duplicated().sum()),
            },
            {
                "file": "Master_Modelling_Dataset_Project_Year_Panel.csv",
                "rows": len(panel_py),
                "columns": panel_py.shape[1],
                "missing_cells": int(panel_py.isna().sum().sum()),
                "duplicate_project_ids": int(panel_py.duplicated(["project_id", "year"]).sum()),
            },
        ]
    )
    qa.to_csv(MASTER_DIR / "Master_QA_Summary.csv", index=False)
    return project_level, panel_py, ml
