from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.ui_theme import (
    AMBER,
    BLUE,
    EWS_COLORS,
    GRADE_COLORS,
    GREEN,
    MUTED,
    NAVY,
    RED,
    SLATE,
    apply_ui,
    page_header,
    section_header,
    show_plotly,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BANK_FILES = [
    PROJECT_ROOT / "05_Final_Results" / "FINAL_BANK_CREDIT_FRAMEWORK" / "FINAL_Bank_Credit_Decision_Support_Full.csv",
    PROJECT_ROOT / "05_Final_Results" / "Phase_7A_Bank_Credit_Decision_Support" / "Bank_Credit_Decision_Support_Full.csv",
]
STRESS_FILE = PROJECT_ROOT / "03_Modeling" / "Phase_3E_Robust_Stress_Test" / "Robust_Stress_Test_Full.csv"
MC_FILE = PROJECT_ROOT / "03_Modeling" / "Phase_6B_Monte_Carlo_Stress" / "Monte_Carlo_Project_Risk_Summary.csv"
ALLOC_FILE = PROJECT_ROOT / "05_Final_Results" / "Final_Project_Allocation_Robustness.csv"

C = {
    "project_id": ["project_id"],
    "company": ["company"],
    "project_type": ["project_type", "project_type_standardized"],
    "state": ["state"],
    "investment": ["investment_crore"],
    "grade": ["indicative_model_risk_grade", "indicative_internal_risk_grade", "indicative_grade", "risk_grade"],
    "baseline_grade": ["baseline_indicative_grade"],
    "severe_grade": ["severe_stress_indicative_grade"],
    "migration": ["stress_grade_migration"],
    "ews": ["early_warning_status", "ews_status"],
    "stress": ["project_stress_vulnerability_score", "severe_score"],
    "stress_class": ["project_stress_vulnerability_class"],
    "macro_pct": ["macro_vulnerability_percentile"],
    "borrower_strength": ["borrower_credit_strength_score"],
    "borrower_class": ["borrower_credit_strength_class"],
    "concentration": ["portfolio_concentration_signal_score"],
    "concentration_class": ["portfolio_concentration_class"],
    "evidence": ["credit_evidence_coverage_pct"],
    "evidence_quality": ["credit_information_quality"],
    "credit_posture": ["credit_posture"],
    "exposure_posture": ["exposure_posture"],
    "monitoring": ["monitoring_priority"],
    "drivers": ["primary_risk_drivers"],
    "mitigants": ["primary_risk_mitigants"],
    "explanation": ["bank_decision_support_explanation"],
    "enhanced_rank": ["enhanced_vulnerability_rank"],
    "robust_rank": ["robust_vulnerability_rank"],
    "p95": ["p95_score"],
    "prob_top3": ["probability_top_3"],
    "allocation_share": ["mean_allocation_share"],
    "allocation_rank": ["robust_allocation_rank"],
}


@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = df.columns.astype(str).str.strip()
    return df


def first_existing(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def col(df: pd.DataFrame, key: str) -> str | None:
    for name in C.get(key, [key]):
        if name in df.columns:
            return name
    return None


def num(df: pd.DataFrame, key: str) -> pd.Series:
    c = col(df, key)
    if c is None:
        return pd.Series(index=df.index, dtype=float)
    return pd.to_numeric(df[c], errors="coerce")


def text(df: pd.DataFrame, key: str, default: str = "Not available") -> pd.Series:
    c = col(df, key)
    if c is None:
        return pd.Series(default, index=df.index, dtype="object")
    return df[c].fillna(default).astype(str)


def fmt_cr(value) -> str:
    try:
        x = float(value)
    except Exception:
        return "—"
    if not np.isfinite(x):
        return "—"
    if abs(x) >= 100000:
        return f"₹{x/100000:.2f}L Cr"
    if abs(x) >= 1000:
        return f"₹{x/1000:.1f}K Cr"
    return f"₹{x:,.0f} Cr"


def fmt_score(value) -> str:
    try:
        x = float(value)
        return f"{x:.1f}"
    except Exception:
        return "—"


def load_bank() -> tuple[pd.DataFrame, Path]:
    path = first_existing(BANK_FILES)
    if path is None:
        st.error("The bank decision-support output is missing from the deployed repository.")
        st.stop()
    return read_csv(str(path)), path


def load_optional(path: Path) -> pd.DataFrame | None:
    return read_csv(str(path)) if path.exists() else None


def clean_display_name(value: str, max_len: int = 42) -> str:
    s = str(value)
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    state_c = col(out, "state")
    type_c = col(out, "project_type")
    grade_c = col(out, "grade")
    ews_c = col(out, "ews")
    company_c = col(out, "company")

    with st.sidebar:
        st.markdown("#### Portfolio filters")
        if state_c:
            values = sorted(out[state_c].dropna().astype(str).unique().tolist())
            chosen = st.multiselect("State", values, default=values, key="flt_state")
            if chosen:
                out = out[out[state_c].astype(str).isin(chosen)]
        if type_c:
            values = sorted(out[type_c].dropna().astype(str).unique().tolist())
            chosen = st.multiselect("Project type", values, default=values, key="flt_type")
            if chosen:
                out = out[out[type_c].astype(str).isin(chosen)]
        if grade_c:
            order = ["A", "B", "C", "D", "E"]
            present = out[grade_c].dropna().astype(str).unique().tolist()
            values = [g for g in order if g in present] + [g for g in sorted(present) if g not in order]
            chosen = st.multiselect("Indicative grade", values, default=values, key="flt_grade")
            if chosen:
                out = out[out[grade_c].astype(str).isin(chosen)]
        if ews_c:
            order = ["GREEN", "AMBER", "RED"]
            present = out[ews_c].dropna().astype(str).str.upper().unique().tolist()
            values = [e for e in order if e in present] + [e for e in sorted(present) if e not in order]
            chosen = st.multiselect("Early warning", values, default=values, key="flt_ews")
            if chosen:
                out = out[out[ews_c].astype(str).str.upper().isin(chosen)]
        if company_c:
            q = st.text_input("Search company", placeholder="Type a company name…", key="flt_search")
            if q.strip():
                out = out[out[company_c].astype(str).str.contains(q.strip(), case=False, na=False)]

        st.caption(f"{len(out)} of {len(df)} projects shown")
    return out


def nav() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="font-size:.68rem;font-weight:750;letter-spacing:.11em;color:#93C5FD;margin-bottom:.35rem">
            SEMICONDUCTOR CREDIT
            </div>
            <div style="font-size:1.08rem;font-weight:700;color:#F8FAFC;margin-bottom:1rem">
            Intelligence Platform
            </div>
            """,
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Credit Committee",
                "Project Analysis",
                "Stress Testing",
                "Monte Carlo",
                "Portfolio Allocation",
                "Model Governance",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Research / controlled-pilot decision support")
        st.caption("No automated lending decisions")
    return page


def overview(df: pd.DataFrame) -> None:
    page_header(
        "Portfolio risk overview",
        "A concise view of project vulnerability, early-warning signals, concentration, and evidence quality. Filters in the sidebar update every visual.",
    )

    inv = num(df, "investment")
    stress = num(df, "stress")
    ews = text(df, "ews").str.upper()
    evidence = num(df, "evidence")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Projects in view", f"{len(df):,}", help="Projects remaining after the active sidebar filters.")
    k2.metric("Project financial scale", fmt_cr(inv.sum()), help="Investment/project scale in the source data. This is not bank EAD.")
    k3.metric("Red early-warning", f"{int((ews == 'RED').sum()):,}", help="Research monitoring signal, not a default classification.")
    k4.metric("Average stress score", fmt_score(stress.mean()), help="Constructed relative vulnerability score; not probability of default.")

    st.write("")
    left, right = st.columns([1.05, 1.35])

    with left:
        with st.container(border=True):
            section_header("Indicative grade distribution", "Research grades only — not official bank or CRA ratings.")
            grade_c = col(df, "grade")
            if grade_c:
                counts = (
                    df[grade_c].fillna("N/A").astype(str)
                    .value_counts()
                    .reindex(["A", "B", "C", "D", "E", "N/A"], fill_value=0)
                    .reset_index()
                )
                counts.columns = ["Grade", "Projects"]
                counts = counts[counts["Projects"] > 0]
                fig = px.bar(
                    counts,
                    x="Grade",
                    y="Projects",
                    text="Projects",
                    color="Grade",
                    color_discrete_map=GRADE_COLORS | {"N/A": SLATE},
                )
                fig.update_traces(textposition="outside", hovertemplate="Grade %{x}<br>%{y} projects<extra></extra>")
                fig.update_layout(showlegend=False)
                show_plotly(fig, key="overview_grade", height=330, selectable=True)
            else:
                st.info("Indicative grade is unavailable in the loaded file.")

    with right:
        with st.container(border=True):
            section_header("Stress–concentration map", "Hover, pan, zoom, and select points. Bubble size reflects project investment scale.")
            plot = pd.DataFrame({
                "Concentration": num(df, "concentration"),
                "Stress vulnerability": num(df, "stress"),
                "Company": text(df, "company"),
                "Grade": text(df, "grade"),
                "State": text(df, "state"),
                "EWS": text(df, "ews").str.upper(),
                "Investment": num(df, "investment").clip(lower=0),
            }).dropna(subset=["Concentration", "Stress vulnerability"])
            if not plot.empty:
                max_inv = plot["Investment"].max()
                plot["Bubble size"] = 18 if not max_inv or not np.isfinite(max_inv) else 14 + 34 * np.sqrt(plot["Investment"] / max_inv)
                fig = px.scatter(
                    plot,
                    x="Concentration",
                    y="Stress vulnerability",
                    color="EWS",
                    size="Bubble size",
                    size_max=48,
                    hover_name="Company",
                    hover_data={"State": True, "Grade": True, "Investment": ":,.0f", "Bubble size": False},
                    color_discrete_map=EWS_COLORS,
                )
                fig.update_traces(marker=dict(line=dict(width=1, color="#FFFFFF"), opacity=0.88))
                fig.update_layout(xaxis_title="Portfolio concentration signal", yaxis_title="Project stress vulnerability")
                show_plotly(fig, key="overview_risk_map", height=330, selectable=True)
            else:
                st.info("Stress/concentration fields are unavailable.")

    with st.container(border=True):
        section_header("Project vulnerability ranking", "Sorted by the current project stress vulnerability score.")
        company_c = col(df, "company")
        if company_c and col(df, "stress"):
            rank = pd.DataFrame({
                "Company": df[company_c].astype(str).map(clean_display_name),
                "Stress": num(df, "stress"),
                "EWS": text(df, "ews").str.upper(),
                "Grade": text(df, "grade"),
                "State": text(df, "state"),
            }).dropna(subset=["Stress"]).sort_values("Stress", ascending=True)
            fig = px.bar(
                rank,
                x="Stress",
                y="Company",
                orientation="h",
                color="EWS",
                hover_data={"Grade": True, "State": True},
                color_discrete_map=EWS_COLORS,
            )
            fig.update_layout(xaxis_title="Stress vulnerability score", yaxis_title="", showlegend=True)
            show_plotly(fig, key="overview_ranking", height=max(380, 34 * len(rank) + 80), selectable=True)

    left2, right2 = st.columns([1, 1])
    with left2:
        with st.container(border=True):
            section_header("State concentration", "Aggregate project financial scale by state.")
            state_c = col(df, "state")
            if state_c and col(df, "investment"):
                tmp = pd.DataFrame({"State": df[state_c].astype(str), "Investment": inv}).dropna()
                state_sum = tmp.groupby("State", as_index=False)["Investment"].sum().sort_values("Investment")
                fig = px.bar(state_sum, x="Investment", y="State", orientation="h", text_auto=".3s")
                fig.update_traces(marker_color=BLUE, hovertemplate="%{y}<br>₹%{x:,.0f} Cr<extra></extra>")
                fig.update_layout(xaxis_title="Project financial scale (₹ Cr)", yaxis_title="")
                show_plotly(fig, key="overview_state", height=340)
    with right2:
        with st.container(border=True):
            section_header("Evidence quality", "Coverage of verified evidence layers used in the decision-support framework.")
            if evidence.notna().any():
                ev = evidence.dropna()
                fig = go.Figure(
                    go.Histogram(
                        x=ev,
                        nbinsx=8,
                        marker_color=NAVY,
                        hovertemplate="Coverage %{x:.0f}%<br>%{y} projects<extra></extra>",
                    )
                )
                fig.update_layout(xaxis_title="Evidence coverage (%)", yaxis_title="Projects")
                show_plotly(fig, key="overview_evidence", height=340)
            else:
                st.info("Evidence coverage is unavailable.")


def committee(df: pd.DataFrame) -> None:
    page_header(
        "Credit committee workspace",
        "A review-first register prioritizing warning signals, vulnerability, evidence quality, and proposed analyst posture.",
    )
    ews_c = col(df, "ews")
    work = df.copy()
    if ews_c:
        order = {"RED": 0, "AMBER": 1, "GREEN": 2}
        work["_ews_order"] = work[ews_c].fillna("").astype(str).str.upper().map(order).fillna(3)
    else:
        work["_ews_order"] = 3
    work["_stress"] = num(work, "stress")
    work = work.sort_values(["_ews_order", "_stress"], ascending=[True, False])

    ews = text(work, "ews").str.upper()
    c1, c2, c3 = st.columns(3)
    c1.metric("Red cases", int((ews == "RED").sum()))
    c2.metric("Amber cases", int((ews == "AMBER").sum()))
    c3.metric("High monitoring priority", int(text(work, "monitoring").str.upper().eq("HIGH").sum()))

    with st.container(border=True):
        section_header("Prioritized review register", "Click column headers to sort. Use the download button for a committee-ready extract.")
        fields = [
            ("project_id", "Project ID"),
            ("company", "Company"),
            ("state", "State"),
            ("grade", "Grade"),
            ("ews", "EWS"),
            ("stress", "Stress"),
            ("concentration", "Concentration"),
            ("evidence", "Evidence %"),
            ("monitoring", "Monitoring"),
            ("credit_posture", "Credit posture"),
        ]
        out = pd.DataFrame()
        for key, label in fields:
            c = col(work, key)
            if c:
                out[label] = work[c]
        for name in ["Stress", "Concentration", "Evidence %"]:
            if name in out:
                out[name] = pd.to_numeric(out[name], errors="coerce")
        config = {}
        if "Stress" in out:
            config["Stress"] = st.column_config.ProgressColumn("Stress", min_value=0, max_value=100, format="%.1f")
        if "Concentration" in out:
            config["Concentration"] = st.column_config.ProgressColumn("Concentration", min_value=0, max_value=100, format="%.1f")
        if "Evidence %" in out:
            config["Evidence %"] = st.column_config.ProgressColumn("Evidence %", min_value=0, max_value=100, format="%.0f%%")
        st.dataframe(out, width="stretch", height=480, hide_index=True, column_config=config)
        st.download_button(
            "Download committee extract",
            data=out.to_csv(index=False).encode("utf-8"),
            file_name="credit_committee_extract.csv",
            mime="text/csv",
        )

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            section_header("Credit posture", "Distribution of model-generated analyst review posture.")
            c = col(df, "credit_posture")
            if c:
                counts = df[c].fillna("Not available").astype(str).value_counts().reset_index()
                counts.columns = ["Posture", "Projects"]
                counts = counts.sort_values("Projects")
                fig = px.bar(counts, x="Projects", y="Posture", orientation="h")
                fig.update_traces(marker_color=BLUE)
                show_plotly(fig, key="committee_posture", height=380)
    with right:
        with st.container(border=True):
            section_header("Exposure posture", "Portfolio-limit posture produced by the banking layer.")
            c = col(df, "exposure_posture")
            if c:
                counts = df[c].fillna("Not available").astype(str).value_counts().reset_index()
                counts.columns = ["Posture", "Projects"]
                counts = counts.sort_values("Projects")
                fig = px.bar(counts, x="Projects", y="Posture", orientation="h")
                fig.update_traces(marker_color=NAVY)
                show_plotly(fig, key="committee_exposure", height=380)


def project_analysis(df: pd.DataFrame, stress_df: pd.DataFrame | None, mc_df: pd.DataFrame | None) -> None:
    page_header(
        "Project analysis",
        "Drill into one project and trace the evidence from vulnerability and concentration to stress migration and Monte Carlo tail risk.",
    )
    company_c = col(df, "company")
    id_c = col(df, "project_id")
    if not company_c:
        st.error("Company field is unavailable.")
        return
    options = df[[company_c] + ([id_c] if id_c else [])].copy()
    options["_label"] = options[company_c].astype(str)
    if id_c:
        options["_label"] += " · " + options[id_c].astype(str)
    selected = st.selectbox("Project", options["_label"].tolist())
    row = df.loc[options["_label"].eq(selected)].iloc[0]
    pid = str(row[id_c]) if id_c else None

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Indicative grade", str(row[col(df, "grade")]) if col(df, "grade") else "—")
    k2.metric("Early warning", str(row[col(df, "ews")]) if col(df, "ews") else "—")
    k3.metric("Stress score", fmt_score(row[col(df, "stress")]) if col(df, "stress") else "—")
    k4.metric("Concentration", fmt_score(row[col(df, "concentration")]) if col(df, "concentration") else "—")
    k5.metric("Evidence coverage", f"{fmt_score(row[col(df, 'evidence')])}%" if col(df, "evidence") else "—")

    left, right = st.columns([1.05, 0.95])
    with left:
        with st.container(border=True):
            section_header("Decision-support explanation", "The framework's consolidated rationale for this project.")
            c = col(df, "explanation")
            st.write(str(row[c]) if c and pd.notna(row[c]) else "No consolidated explanation available.")
            section_header("Primary risk drivers")
            c = col(df, "drivers")
            st.write(str(row[c]) if c and pd.notna(row[c]) else "No dominant elevated signal identified.")
            section_header("Primary mitigants")
            c = col(df, "mitigants")
            st.write(str(row[c]) if c and pd.notna(row[c]) else "No verified mitigant recorded.")
    with right:
        with st.container(border=True):
            section_header("Project facts")
            facts = []
            for key, label in [("state", "State"), ("project_type", "Project type"), ("investment", "Investment"), ("borrower_class", "Borrower strength class"), ("concentration_class", "Concentration class"), ("evidence_quality", "Information quality"), ("monitoring", "Monitoring priority")]:
                c = col(df, key)
                if c:
                    value = row[c]
                    if key == "investment":
                        value = fmt_cr(value)
                    facts.append({"Field": label, "Value": value})
            st.dataframe(pd.DataFrame(facts), hide_index=True, width="stretch")

    if stress_df is not None and pid and "project_id" in stress_df.columns:
        s = stress_df[stress_df["project_id"].astype(str).eq(pid)]
        if not s.empty:
            r = s.iloc[0]
            scenarios = []
            for label, c in [("Baseline", "baseline_score"), ("Mild", "mild_score"), ("Moderate", "moderate_score"), ("Severe", "severe_score")]:
                if c in s.columns:
                    scenarios.append({"Scenario": label, "Score": pd.to_numeric(pd.Series([r[c]]), errors="coerce").iloc[0]})
            if scenarios:
                with st.container(border=True):
                    section_header("Stress migration", "Interactive scenario path for the selected project.")
                    sc = pd.DataFrame(scenarios).dropna()
                    fig = px.line(sc, x="Scenario", y="Score", markers=True)
                    fig.update_traces(line=dict(color=RED, width=3), marker=dict(size=10))
                    fig.update_layout(yaxis_range=[0, 100])
                    show_plotly(fig, key="project_stress", height=340)

    if mc_df is not None and pid and "project_id" in mc_df.columns:
        m = mc_df[mc_df["project_id"].astype(str).eq(pid)]
        if not m.empty:
            r = m.iloc[0]
            pcs = []
            for label, c in [("Median", "median_simulated_score"), ("P75", "p75_score"), ("P90", "p90_score"), ("P95", "p95_score"), ("P99", "p99_score")]:
                if c in m.columns:
                    pcs.append({"Percentile": label, "Score": pd.to_numeric(pd.Series([r[c]]), errors="coerce").iloc[0]})
            if pcs:
                with st.container(border=True):
                    section_header("Monte Carlo tail profile", "Selected percentiles from the simulated vulnerability distribution.")
                    pc = pd.DataFrame(pcs).dropna()
                    fig = px.line(pc, x="Percentile", y="Score", markers=True)
                    fig.update_traces(line=dict(color=BLUE, width=3), marker=dict(size=9))
                    fig.update_layout(yaxis_range=[0, 100])
                    show_plotly(fig, key="project_mc", height=340)


def stress_page(df: pd.DataFrame, stress_df: pd.DataFrame | None) -> None:
    page_header(
        "Stress testing",
        "Scenario migration from baseline to severe conditions. Scores are relative analytical vulnerability indices, not observed losses or probabilities of default.",
    )
    if stress_df is None:
        st.info("The Phase 3E stress-test output is not available in the deployed repository.")
        return

    scenario_cols = [c for c in ["baseline_score", "mild_score", "moderate_score", "severe_score"] if c in stress_df.columns]
    if not scenario_cols:
        st.info("Scenario-score columns are unavailable.")
        return

    means = [{"Scenario": c.replace("_score", "").title(), "Mean": pd.to_numeric(stress_df[c], errors="coerce").mean()} for c in scenario_cols]
    with st.container(border=True):
        section_header("Portfolio scenario path", "Mean project vulnerability across progressively more adverse scenarios.")
        fig = px.line(pd.DataFrame(means), x="Scenario", y="Mean", markers=True)
        fig.update_traces(line=dict(color=RED, width=3), marker=dict(size=10))
        fig.update_layout(yaxis_title="Mean vulnerability score", yaxis_range=[0, 100])
        show_plotly(fig, key="stress_portfolio", height=350)

    if "company" in stress_df.columns and "baseline_score" in stress_df.columns and "severe_score" in stress_df.columns:
        with st.container(border=True):
            section_header("Baseline vs severe stress", "Distance above the diagonal shows the magnitude of modelled stress migration.")
            plot = stress_df[["company", "baseline_score", "severe_score"]].copy()
            plot["baseline_score"] = pd.to_numeric(plot["baseline_score"], errors="coerce")
            plot["severe_score"] = pd.to_numeric(plot["severe_score"], errors="coerce")
            plot = plot.dropna()
            fig = px.scatter(plot, x="baseline_score", y="severe_score", hover_name="company")
            lo = float(min(plot["baseline_score"].min(), plot["severe_score"].min()))
            hi = float(max(plot["baseline_score"].max(), plot["severe_score"].max()))
            fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="No migration", line=dict(color="#CBD5E1", dash="dash")))
            fig.update_traces(selector=dict(type="scatter", mode="markers"), marker=dict(size=11, color=BLUE))
            fig.update_layout(xaxis_title="Baseline score", yaxis_title="Severe score")
            show_plotly(fig, key="stress_scatter", height=430, selectable=True)

    if "company" in stress_df.columns and "severe_score" in stress_df.columns:
        with st.container(border=True):
            section_header("Severe-scenario ranking")
            plot = stress_df[["company", "severe_score"]].copy()
            plot["severe_score"] = pd.to_numeric(plot["severe_score"], errors="coerce")
            plot = plot.dropna().sort_values("severe_score")
            plot["company"] = plot["company"].astype(str).map(clean_display_name)
            fig = px.bar(plot, x="severe_score", y="company", orientation="h")
            fig.update_traces(marker_color=NAVY)
            fig.update_layout(xaxis_title="Severe vulnerability score", yaxis_title="")
            show_plotly(fig, key="stress_rank", height=max(380, 34 * len(plot) + 80))


def monte_carlo_page(mc_df: pd.DataFrame | None) -> None:
    page_header(
        "Monte Carlo tail risk",
        "10,000-simulation analytical stress output. Shock distributions are modelling assumptions; these scores are not default probabilities.",
    )
    if mc_df is None:
        st.info("Monte Carlo project summary is not available.")
        return

    required = {"company", "mean_simulated_score", "p95_score"}
    if required.issubset(mc_df.columns):
        with st.container(border=True):
            section_header("Mean vs P95 tail vulnerability", "Hover over a point for project detail; use box/lasso selection for comparison.")
            plot = mc_df.copy()
            plot["mean_simulated_score"] = pd.to_numeric(plot["mean_simulated_score"], errors="coerce")
            plot["p95_score"] = pd.to_numeric(plot["p95_score"], errors="coerce")
            plot["probability_top_3"] = pd.to_numeric(plot.get("probability_top_3"), errors="coerce").fillna(0)
            plot["investment_crore"] = pd.to_numeric(plot.get("investment_crore"), errors="coerce").fillna(1).clip(lower=1)
            fig = px.scatter(
                plot,
                x="mean_simulated_score",
                y="p95_score",
                hover_name="company",
                color="probability_top_3",
                size="investment_crore",
                size_max=44,
                color_continuous_scale=["#DBEAFE", BLUE, RED],
                hover_data={"state": True if "state" in plot.columns else False, "probability_top_3": ":.3f", "investment_crore": ":,.0f"},
            )
            fig.update_layout(xaxis_title="Mean simulated score", yaxis_title="P95 tail score", coloraxis_colorbar_title="Top-3 freq.")
            show_plotly(fig, key="mc_scatter", height=440, selectable=True)

    if "company" in mc_df.columns and "p95_score" in mc_df.columns:
        with st.container(border=True):
            section_header("P95 tail-risk ranking")
            plot = mc_df[["company", "p95_score"]].copy()
            plot["p95_score"] = pd.to_numeric(plot["p95_score"], errors="coerce")
            plot = plot.dropna().sort_values("p95_score")
            plot["company"] = plot["company"].astype(str).map(clean_display_name)
            fig = px.bar(plot, x="p95_score", y="company", orientation="h")
            fig.update_traces(marker_color=RED)
            fig.update_layout(xaxis_title="P95 score", yaxis_title="")
            show_plotly(fig, key="mc_rank", height=max(380, 34 * len(plot) + 80))


def allocation_page(alloc_df: pd.DataFrame | None) -> None:
    page_header(
        "Portfolio allocation",
        "Sensitivity-tested allocation shares under project and state concentration constraints. These are modelled portfolio shares, not sanctioned bank facilities.",
    )
    if alloc_df is None:
        st.info("Allocation robustness output is not available.")
        return
    needed = {"company", "mean_allocation_share"}
    if needed.issubset(alloc_df.columns):
        plot = alloc_df.copy()
        for c in ["mean_allocation_share", "min_allocation_share", "max_allocation_share"]:
            if c in plot:
                plot[c] = pd.to_numeric(plot[c], errors="coerce") * 100
        plot = plot.dropna(subset=["mean_allocation_share"]).sort_values("mean_allocation_share")
        plot["company_short"] = plot["company"].astype(str).map(clean_display_name)
        with st.container(border=True):
            section_header("Mean allocation share", "Error bars show the observed min–max range across sensitivity scenarios.")
            error_plus = plot["max_allocation_share"] - plot["mean_allocation_share"] if "max_allocation_share" in plot else None
            error_minus = plot["mean_allocation_share"] - plot["min_allocation_share"] if "min_allocation_share" in plot else None
            fig = go.Figure(go.Bar(
                x=plot["mean_allocation_share"],
                y=plot["company_short"],
                orientation="h",
                marker_color=BLUE,
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=error_plus if error_plus is not None else [],
                    arrayminus=error_minus if error_minus is not None else [],
                    color=SLATE,
                    thickness=1.2,
                ) if error_plus is not None else None,
                customdata=np.stack([plot["company"]], axis=-1),
                hovertemplate="%{customdata[0]}<br>Mean share %{x:.2f}%<extra></extra>",
            ))
            fig.update_layout(xaxis_title="Mean allocation share (%)", yaxis_title="")
            show_plotly(fig, key="alloc_project", height=max(390, 34 * len(plot) + 80))

        if "state" in plot.columns:
            with st.container(border=True):
                section_header("Allocation by state", "Aggregate mean modelled allocation share.")
                state = plot.groupby("state", as_index=False)["mean_allocation_share"].sum().sort_values("mean_allocation_share")
                fig = px.bar(state, x="mean_allocation_share", y="state", orientation="h", text_auto=".2f")
                fig.update_traces(marker_color=NAVY, hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>")
                fig.update_layout(xaxis_title="Allocation share (%)", yaxis_title="")
                show_plotly(fig, key="alloc_state", height=340)

        if "allocation_stability" in plot.columns:
            with st.container(border=True):
                section_header("Allocation stability")
                counts = plot["allocation_stability"].fillna("Not available").astype(str).value_counts().reset_index()
                counts.columns = ["Stability", "Projects"]
                fig = px.bar(counts, x="Stability", y="Projects", text="Projects")
                fig.update_traces(marker_color=GREEN, textposition="outside")
                show_plotly(fig, key="alloc_stability", height=320)


def governance_page(df: pd.DataFrame, source_path: Path) -> None:
    page_header(
        "Model governance",
        "Methodological boundaries, evidence coverage, and deployment status for responsible interpretation.",
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Projects", len(df))
    k2.metric("Observed default target", "No")
    k3.metric("Automated lending", "Disabled")
    k4.metric("Deployment", "Research pilot")

    with st.container(border=True):
        section_header("Framework architecture")
        st.markdown(
            "**Structural segmentation → macro-prudential stress testing → Monte Carlo tail analysis → "
            "borrower/external evidence → concentration/allocation → bank decision-support layer**"
        )
    with st.container(border=True):
        section_header("Interpretation boundaries")
        st.warning(
            "The framework does not estimate regulatory PD, LGD, EAD or ECL. "
            "A–E categories are research decision-support grades and not official bank or credit-rating-agency ratings."
        )
        st.info(
            "Current Streamlit Community Cloud deployment is suitable for academic/pilot demonstration only. "
            "Do not upload confidential bank or customer data."
        )
    with st.container(border=True):
        section_header("Evidence coverage")
        ev = num(df, "evidence")
        if ev.notna().any():
            k1, k2, k3 = st.columns(3)
            k1.metric("Average evidence coverage", f"{ev.mean():.0f}%")
            k2.metric("High-quality information", int(text(df, "evidence_quality").str.upper().eq("HIGH").sum()))
            k3.metric("Projects with borrower strength", int(num(df, "borrower_strength").notna().sum()))
        st.caption(f"Decision-support source: {source_path.relative_to(PROJECT_ROOT)}")


def render_app() -> None:
    apply_ui()
    page = nav()

    bank, bank_path = load_bank()
    filtered = apply_filters(bank)

    if filtered.empty:
        st.warning("No projects match the current filters. Adjust the sidebar filters.")
        return

    stress_df = load_optional(STRESS_FILE)
    mc_df = load_optional(MC_FILE)
    alloc_df = load_optional(ALLOC_FILE)

    if page == "Overview":
        overview(filtered)
    elif page == "Credit Committee":
        committee(filtered)
    elif page == "Project Analysis":
        project_analysis(filtered, stress_df, mc_df)
    elif page == "Stress Testing":
        stress_page(filtered, stress_df)
    elif page == "Monte Carlo":
        monte_carlo_page(mc_df)
    elif page == "Portfolio Allocation":
        allocation_page(alloc_df)
    else:
        governance_page(filtered, bank_path)

    st.divider()
    st.caption(
        "Semiconductor Credit Intelligence · Research decision-support prototype · "
        "Human credit judgement required."
    )
