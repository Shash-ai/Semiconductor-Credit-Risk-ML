from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

BANK_CANDIDATES = [
    ROOT / "05_Final_Results" / "FINAL_BANK_CREDIT_FRAMEWORK" / "FINAL_Bank_Credit_Decision_Support_Full.csv",
    ROOT / "05_Final_Results" / "Phase_7A_Bank_Credit_Decision_Support" / "Bank_Credit_Decision_Support_Full.csv",
]
STRESS_FILE = ROOT / "03_Modeling" / "Phase_3E_Robust_Stress_Test" / "Robust_Stress_Test_Full.csv"
MC_FILE = ROOT / "03_Modeling" / "Phase_6B_Monte_Carlo_Stress" / "Monte_Carlo_Project_Risk_Summary.csv"
ALLOC_FILE = ROOT / "05_Final_Results" / "Final_Project_Allocation_Robustness.csv"

NAVY = "#0B1F33"
INK = "#111827"
MUTED = "#64748B"
BLUE = "#2563EB"
TEAL = "#0F766E"
AMBER = "#D97706"
RED = "#DC2626"
BORDER = "#E5E7EB"
GRID = "#EEF2F6"
SURFACE = "#FFFFFF"
EWS_COLORS = {"GREEN": TEAL, "AMBER": AMBER, "RED": RED}
GRADE_COLORS = {"A": TEAL, "B": "#3B82F6", "C": AMBER, "D": "#EA580C", "E": RED}

CSS = r"""
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.stApp { background: #F7F8FA; }
.block-container {
    max-width: 1500px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
h1, h2, h3, h4 { color: #111827 !important; letter-spacing: -0.02em; }
p, li, label, .stCaption, [data-testid="stMarkdownContainer"] { color: #334155; }
[data-testid="stSidebar"] {
    background: #0B1F33;
    border-right: 1px solid #16324A;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: #F8FAFC !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: .35rem .45rem;
    border-radius: 8px;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.06); }
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: .95rem 1rem;
    min-height: 108px;
    box-shadow: 0 1px 2px rgba(15,23,42,.03);
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-weight: 600; }
[data-testid="stMetricValue"] {
    color: #111827 !important;
    font-variant-numeric: tabular-nums;
    letter-spacing: -.035em;
}
[data-testid="stDataFrame"] {
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    overflow: hidden;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background: #FFFFFF !important;
    color: #111827 !important;
}
.stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 600; }
div[data-testid="stAlert"] { border-radius: 10px; }
hr { border-color: #E5E7EB !important; }
.sci-eyebrow {
    color: #2563EB;
    font-size: .72rem;
    font-weight: 750;
    letter-spacing: .10em;
    text-transform: uppercase;
    margin-bottom: .35rem;
}
.sci-title {
    color: #111827;
    font-size: clamp(1.85rem, 3vw, 2.55rem);
    font-weight: 760;
    letter-spacing: -.045em;
    line-height: 1.08;
    margin: 0;
}
.sci-subtitle {
    color: #64748B;
    font-size: .93rem;
    line-height: 1.55;
    max-width: 880px;
    margin-top: .55rem;
    margin-bottom: 1.25rem;
}
@media (max-width: 900px) {
    .block-container { padding-left: .9rem; padding-right: .9rem; }
}
</style>
"""

PLOTLY_CONFIG = {
    "displaylogo": False,
    "displayModeBar": "hover",
    "responsive": True,
    "scrollZoom": True,
    "doubleClick": "reset",
    "toImageButtonOptions": {
        "format": "png",
        "filename": "semiconductor_credit_chart",
        "height": 900,
        "width": 1500,
        "scale": 2,
    },
}

@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    return df

def first_existing(paths):
    return next((p for p in paths if p.exists()), None)

def load_bank():
    path = first_existing(BANK_CANDIDATES)
    if path is None:
        st.error("Bank decision-support output is missing from the repository.")
        st.stop()
    return read_csv(str(path)), path

def load_optional(path: Path):
    return read_csv(str(path)) if path.exists() else None

def text_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[col].fillna("").astype(str)

def num_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(float("nan"), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")

def money_cr(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    v = float(value)
    if abs(v) >= 100000:
        return f"₹{v/100000:.2f}L Cr"
    if abs(v) >= 1000:
        return f"₹{v/1000:.1f}K Cr"
    return f"₹{v:,.0f} Cr"

def apply_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

def header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="sci-eyebrow">SEMICONDUCTOR CREDIT INTELLIGENCE</div>'
        f'<div class="sci-title">{title}</div>'
        f'<div class="sci-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )

def style_fig(fig: go.Figure, height: int = 390) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif', color=INK, size=12),
        margin=dict(l=24, r=20, t=32, b=34),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, font_color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11, color=MUTED)),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED), automargin=True),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED), automargin=True),
        hovermode="closest",
        dragmode="pan",
        uirevision="sci-stable",
    )
    return fig

def chart(fig: go.Figure, key: str, height: int = 390) -> None:
    style_fig(fig, height)
    st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOTLY_CONFIG, key=key)

def filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### Semiconductor Intelligence")
        st.caption("Bank credit decision-support")
        page = st.radio(
            "Navigation",
            ["Overview", "Credit Committee", "Project Analysis", "Stress Testing", "Monte Carlo", "Portfolio Allocation", "Model Governance"],
            label_visibility="collapsed",
        )
        st.session_state["page"] = page
        st.divider()
        st.markdown("#### Portfolio filters")
        state_options = sorted(text_series(df, "state").replace("", pd.NA).dropna().unique().tolist())
        type_options = sorted(text_series(df, "project_type").replace("", pd.NA).dropna().unique().tolist())
        grade_options = [g for g in ["A", "B", "C", "D", "E"] if g in set(text_series(df, "indicative_model_risk_grade").str.upper())]
        ews_options = [s for s in ["GREEN", "AMBER", "RED"] if s in set(text_series(df, "early_warning_status").str.upper())]
        states = st.multiselect("State", state_options)
        project_types = st.multiselect("Project type", type_options)
        grades = st.multiselect("Indicative grade", grade_options)
        ews = st.multiselect("Early warning", ews_options)
        company_q = st.text_input("Company search", placeholder="Type a company name")
        st.divider()
        st.caption("Research / controlled pilot")
        st.caption("No automated credit approval")

    out = df.copy()
    if states:
        out = out[out["state"].isin(states)]
    if project_types:
        out = out[out["project_type"].isin(project_types)]
    if grades:
        out = out[text_series(out, "indicative_model_risk_grade").str.upper().isin(grades)]
    if ews:
        out = out[text_series(out, "early_warning_status").str.upper().isin(ews)]
    if company_q:
        out = out[text_series(out, "company").str.contains(company_q, case=False, na=False)]
    return out

def render_overview(df: pd.DataFrame) -> None:
    header("Portfolio Risk Overview", "Executive portfolio view with interactive vulnerability, concentration and monitoring signals.")
    inv = num_series(df, "investment_crore")
    stress = num_series(df, "project_stress_vulnerability_score")
    ews = text_series(df, "early_warning_status").str.upper()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projects in view", f"{len(df):,}")
    c2.metric("Project financial scale", money_cr(inv.sum()))
    c3.metric("Red EWS cases", int((ews == "RED").sum()))
    c4.metric("Avg stress vulnerability", f"{stress.mean():.1f}" if stress.notna().any() else "—")
    st.caption("Financial scale is project investment, not bank EAD.")

    left, right = st.columns([0.95, 1.25])
    with left:
        st.subheader("Indicative grade distribution")
        counts = text_series(df, "indicative_model_risk_grade").str.upper().replace("", "N/A").value_counts().reindex(["A","B","C","D","E","N/A"]).dropna().reset_index()
        counts.columns = ["Grade", "Projects"]
        fig = px.bar(counts, x="Grade", y="Projects", color="Grade", color_discrete_map=GRADE_COLORS, text="Projects")
        fig.update_traces(textposition="outside", hovertemplate="Grade %{x}<br>%{y} projects<extra></extra>")
        fig.update_layout(showlegend=False)
        chart(fig, "overview_grade", 330)

    with right:
        st.subheader("Stress × concentration map")
        plot = df.copy()
        plot["Stress"] = num_series(plot, "project_stress_vulnerability_score")
        plot["Concentration"] = num_series(plot, "portfolio_concentration_signal_score")
        plot["Investment"] = num_series(plot, "investment_crore").fillna(0).clip(lower=0)
        plot["EWS"] = text_series(plot, "early_warning_status").str.upper().replace("", "N/A")
        plot["Grade"] = text_series(plot, "indicative_model_risk_grade").str.upper()
        plot = plot.dropna(subset=["Stress", "Concentration"])
        size_col = "Investment" if plot["Investment"].gt(0).any() else None
        fig = px.scatter(
            plot,
            x="Concentration",
            y="Stress",
            color="EWS",
            size=size_col,
            hover_name="company",
            hover_data={"state": True, "Grade": True, "Investment": ":,.0f", "Concentration": ":.1f", "Stress": ":.1f"},
            color_discrete_map=EWS_COLORS,
            size_max=52,
        )
        fig.update_traces(marker=dict(line=dict(width=1, color="#FFFFFF"), opacity=.88))
        fig.update_xaxes(title="Portfolio concentration signal")
        fig.update_yaxes(title="Project stress vulnerability")
        chart(fig, "overview_map", 380)

    st.subheader("Project vulnerability ranking")
    rank = df.copy()
    rank["Stress"] = num_series(rank, "project_stress_vulnerability_score")
    rank["EWS"] = text_series(rank, "early_warning_status").str.upper()
    rank["Grade"] = text_series(rank, "indicative_model_risk_grade").str.upper()
    rank = rank.dropna(subset=["Stress"]).sort_values("Stress", ascending=True)
    fig = px.bar(rank, x="Stress", y="company", orientation="h", color="EWS", color_discrete_map=EWS_COLORS,
                 hover_data={"state": True, "Grade": True, "investment_crore": ":,.0f"})
    fig.update_layout(yaxis_title="", xaxis_title="Stress vulnerability score")
    chart(fig, "overview_rank", max(390, 32 * len(rank) + 90))

    a, b = st.columns(2)
    with a:
        st.subheader("Geographic concentration")
        geo = df.copy()
        geo["Investment"] = num_series(geo, "investment_crore")
        geo = geo.groupby("state", as_index=False)["Investment"].sum().sort_values("Investment", ascending=True)
        fig = px.bar(geo, x="Investment", y="state", orientation="h", hover_data={"Investment": ":,.0f"})
        fig.update_traces(marker_color=BLUE)
        fig.update_layout(yaxis_title="", xaxis_title="Project investment (₹ crore)")
        chart(fig, "overview_geo", 360)
    with b:
        st.subheader("Evidence coverage")
        ev = df.copy()
        ev["Evidence"] = num_series(ev, "credit_evidence_coverage_pct")
        ev = ev.dropna(subset=["Evidence"]).sort_values("Evidence", ascending=True)
        fig = px.bar(ev, x="Evidence", y="company", orientation="h", hover_data={"credit_information_quality": True})
        fig.update_traces(marker_color=TEAL)
        fig.update_xaxes(range=[0, 100], title="Evidence coverage (%)")
        fig.update_layout(yaxis_title="")
        chart(fig, "overview_evidence", 360)

def render_committee(df: pd.DataFrame) -> None:
    header("Credit Committee", "Prioritized review register with monitoring, exposure and evidence context.")
    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    view = df.copy()
    view["_priority"] = text_series(view, "early_warning_status").str.upper().map(order).fillna(3)
    view = view.sort_values(["_priority", "project_stress_vulnerability_score"], ascending=[True, False])
    cols = [c for c in [
        "project_id","company","state","indicative_model_risk_grade","early_warning_status",
        "project_stress_vulnerability_score","portfolio_concentration_signal_score",
        "credit_evidence_coverage_pct","monitoring_priority","credit_posture","exposure_posture"
    ] if c in view.columns]
    st.dataframe(
        view[cols],
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "project_stress_vulnerability_score": st.column_config.ProgressColumn("Stress", min_value=0, max_value=100, format="%.1f"),
            "portfolio_concentration_signal_score": st.column_config.ProgressColumn("Concentration", min_value=0, max_value=100, format="%.1f"),
            "credit_evidence_coverage_pct": st.column_config.ProgressColumn("Evidence %", min_value=0, max_value=100, format="%.0f%%"),
        },
    )
    st.download_button("Download current committee extract", view[cols].to_csv(index=False).encode(), "credit_committee_extract.csv", "text/csv")

    if "credit_posture" in view.columns:
        st.subheader("Credit posture")
        p = text_series(view, "credit_posture").replace("", "Not available").value_counts().reset_index()
        p.columns = ["Posture", "Projects"]
        fig = px.bar(p.sort_values("Projects"), x="Projects", y="Posture", orientation="h")
        fig.update_traces(marker_color=NAVY)
        chart(fig, "committee_posture", 380)

def render_project(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    header("Project Analysis", "Company-level analytical drill-down using existing decision-support evidence.")
    source = df_filtered if len(df_filtered) else df_all
    company = st.selectbox("Company", source["company"].astype(str).tolist())
    row = source[source["company"].astype(str).eq(company)].iloc[0]

    cols = st.columns(5)
    cols[0].metric("Grade", str(row.get("indicative_model_risk_grade", "—")))
    cols[1].metric("EWS", str(row.get("early_warning_status", "—")))
    stress_val = pd.to_numeric(pd.Series([row.get("project_stress_vulnerability_score")]), errors="coerce").iloc[0]
    conc_val = pd.to_numeric(pd.Series([row.get("portfolio_concentration_signal_score")]), errors="coerce").iloc[0]
    evidence_val = pd.to_numeric(pd.Series([row.get("credit_evidence_coverage_pct")]), errors="coerce").iloc[0]
    cols[2].metric("Stress", f"{stress_val:.1f}" if pd.notna(stress_val) else "—")
    cols[3].metric("Concentration", f"{conc_val:.1f}" if pd.notna(conc_val) else "—")
    cols[4].metric("Evidence", f"{evidence_val:.0f}%" if pd.notna(evidence_val) else "—")

    st.subheader("Decision-support interpretation")
    st.info(str(row.get("bank_decision_support_explanation", "Not available")))
    l, r = st.columns(2)
    with l:
        st.markdown("**Primary risk drivers**")
        st.write(str(row.get("primary_risk_drivers", "Not available")))
        st.markdown("**Credit posture**")
        st.write(str(row.get("credit_posture", "Not available")))
    with r:
        st.markdown("**Primary mitigants**")
        st.write(str(row.get("primary_risk_mitigants", "Not available")))
        st.markdown("**Exposure posture**")
        st.write(str(row.get("exposure_posture", "Not available")))

    stress_df = load_optional(STRESS_FILE)
    if stress_df is not None and "project_id" in stress_df.columns:
        s = stress_df[stress_df["project_id"].astype(str).eq(str(row.get("project_id")))]
        if not s.empty:
            vals = []
            for scenario, col in [("Baseline","baseline_score"),("Mild","mild_score"),("Moderate","moderate_score"),("Severe","severe_score")]:
                if col in s.columns:
                    vals.append({"Scenario": scenario, "Score": pd.to_numeric(s.iloc[0][col], errors="coerce")})
            if vals:
                st.subheader("Stress migration")
                fig = px.line(pd.DataFrame(vals), x="Scenario", y="Score", markers=True)
                fig.update_traces(line_color=BLUE, marker_size=9)
                chart(fig, "project_stress", 340)

    mc = load_optional(MC_FILE)
    if mc is not None and "project_id" in mc.columns:
        m = mc[mc["project_id"].astype(str).eq(str(row.get("project_id")))]
        if not m.empty:
            fields = [("Mean","mean_simulated_score"),("P90","p90_score"),("P95","p95_score"),("P99","p99_score")]
            vals = [{"Metric": label, "Score": pd.to_numeric(m.iloc[0][col], errors="coerce")} for label, col in fields if col in m.columns]
            if vals:
                st.subheader("Monte Carlo tail profile")
                fig = px.bar(pd.DataFrame(vals), x="Metric", y="Score", text_auto=".1f")
                fig.update_traces(marker_color=TEAL)
                chart(fig, "project_mc", 340)

def render_stress() -> None:
    header("Stress Testing", "Deterministic scenario progression from baseline through severe conditions.")
    df = load_optional(STRESS_FILE)
    if df is None:
        st.info("Stress-test output is unavailable in this deployment.")
        return
    scenario_cols = [("Baseline","baseline_score"),("Mild","mild_score"),("Moderate","moderate_score"),("Severe","severe_score")]
    available = [(s,c) for s,c in scenario_cols if c in df.columns]
    long = []
    for scenario, col in available:
        vals = pd.to_numeric(df[col], errors="coerce")
        for company, score in zip(df["company"].astype(str), vals):
            long.append({"Company": company, "Scenario": scenario, "Score": score})
    long_df = pd.DataFrame(long).dropna()
    fig = px.line(long_df, x="Scenario", y="Score", color="Company", markers=True, hover_name="Company")
    fig.update_layout(legend_title="")
    chart(fig, "stress_lines", 500)

    if {"baseline_score","severe_score"}.issubset(df.columns):
        st.subheader("Baseline vs severe")
        fig = px.scatter(df, x="baseline_score", y="severe_score", hover_name="company", color="state")
        mn = min(pd.to_numeric(df["baseline_score"], errors="coerce").min(), pd.to_numeric(df["severe_score"], errors="coerce").min())
        mx = max(pd.to_numeric(df["baseline_score"], errors="coerce").max(), pd.to_numeric(df["severe_score"], errors="coerce").max())
        fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx, line=dict(color="#94A3B8", dash="dash"))
        chart(fig, "stress_scatter", 420)
    st.caption("Constructed vulnerability indices — not observed defaults, losses or regulatory PD.")

def render_mc() -> None:
    header("Monte Carlo", "Interactive tail-risk view from the existing 10,000-simulation analytical stress exercise.")
    df = load_optional(MC_FILE)
    if df is None:
        st.info("Monte Carlo output is unavailable in this deployment.")
        return
    required = {"mean_simulated_score","p95_score"}
    if required.issubset(df.columns):
        plot = df.copy()
        plot["Investment"] = num_series(plot, "investment_crore").fillna(0)
        plot["P(top 3)"] = num_series(plot, "probability_top_3")
        fig = px.scatter(
            plot, x="mean_simulated_score", y="p95_score",
            size="Investment" if plot["Investment"].gt(0).any() else None,
            color="P(top 3)" if plot["P(top 3)"].notna().any() else None,
            hover_name="company",
            hover_data={"p99_score": ":.1f", "score_std": ":.2f", "investment_crore": ":,.0f"},
            color_continuous_scale="Blues",
            size_max=55,
        )
        fig.update_xaxes(title="Mean simulated vulnerability")
        fig.update_yaxes(title="P95 tail vulnerability")
        chart(fig, "mc_map", 470)

    rank = df.copy()
    rank["P95"] = num_series(rank, "p95_score")
    rank = rank.dropna(subset=["P95"]).sort_values("P95")
    fig = px.bar(rank, x="P95", y="company", orientation="h", hover_data={"probability_top_3": ":.3f", "monte_carlo_rank_stability": True})
    fig.update_traces(marker_color=BLUE)
    fig.update_layout(yaxis_title="", xaxis_title="P95 score")
    chart(fig, "mc_rank", max(390, 32*len(rank)+90))
    st.caption("Simulation shock distributions are analytical assumptions; they are not estimated default probabilities.")

def render_allocation() -> None:
    header("Portfolio Allocation", "Sensitivity-tested relative allocation shares with robustness ranges.")
    df = load_optional(ALLOC_FILE)
    if df is None:
        st.info("Allocation robustness output is unavailable in this deployment.")
        return
    if "mean_allocation_share" in df.columns:
        plot = df.copy()
        for c in ["mean_allocation_share","min_allocation_share","max_allocation_share"]:
            if c in plot.columns:
                plot[c] = pd.to_numeric(plot[c], errors="coerce") * 100
        plot = plot.sort_values("mean_allocation_share")
        err_plus = (plot["max_allocation_share"] - plot["mean_allocation_share"]) if "max_allocation_share" in plot.columns else None
        err_minus = (plot["mean_allocation_share"] - plot["min_allocation_share"]) if "min_allocation_share" in plot.columns else None
        fig = go.Figure(go.Bar(
            x=plot["mean_allocation_share"], y=plot["company"], orientation="h",
            marker_color=BLUE,
            error_x=dict(type="data", array=err_plus, arrayminus=err_minus, visible=err_plus is not None),
            hovertemplate="%{y}<br>Mean allocation: %{x:.2f}%<extra></extra>",
        ))
        fig.update_xaxes(title="Mean allocation share (%)")
        fig.update_yaxes(title="")
        chart(fig, "allocation", max(420, 34*len(plot)+100))
    st.info("Allocation output is a research portfolio-allocation signal, not an actual sanctioned bank facility.")

def render_governance(bank_path: Path, df: pd.DataFrame) -> None:
    header("Model Governance", "Scope, evidence boundaries and responsible-use controls for the decision-support prototype.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bank-layer projects", len(df))
    c2.metric("Observed default target", "No")
    c3.metric("Automated credit decision", "No")
    c4.metric("Deployment class", "Research pilot")
    st.warning("The framework does not estimate regulatory PD, LGD, EAD or ECL. Indicative A–E categories are research decision-support grades, not official bank or CRA ratings.")
    st.markdown("**Architecture**")
    st.write("Structural segmentation → deterministic stress testing → Monte Carlo tail analysis → borrower/external evidence → concentration/allocation → bank decision-support.")
    st.markdown("**Current deployment boundary**")
    st.write("Public Community Cloud demo. Do not upload confidential bank/customer data.")
    st.markdown("**Loaded banking result**")
    st.code(str(bank_path.relative_to(ROOT)))

def render_app() -> None:
    apply_css()
    bank, bank_path = load_bank()
    filtered = filters(bank)
    page = st.session_state.get("page", "Overview")

    if filtered.empty and page in {"Overview", "Credit Committee"}:
        st.warning("No projects match the current filters.")
        return

    if page == "Overview":
        render_overview(filtered)
    elif page == "Credit Committee":
        render_committee(filtered)
    elif page == "Project Analysis":
        render_project(bank, filtered)
    elif page == "Stress Testing":
        render_stress()
    elif page == "Monte Carlo":
        render_mc()
    elif page == "Portfolio Allocation":
        render_allocation()
    else:
        render_governance(bank_path, bank)

    st.divider()
    st.caption("Semiconductor Credit Intelligence · Research decision-support prototype · Human credit judgement required")
