from __future__ import annotations

import html
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import banking_dashboard_v2 as core


# -----------------------------------------------------------------------------
# Institutional design system
# -----------------------------------------------------------------------------

CSS = r"""
<style>
:root {
    --navy-950:#081522;
    --navy-900:#0B1F33;
    --navy-800:#12324F;
    --ink:#101828;
    --text:#344054;
    --muted:#667085;
    --line:#E4E7EC;
    --line-soft:#EEF2F6;
    --surface:#FFFFFF;
    --canvas:#F7F9FC;
    --blue:#175CD3;
    --teal:#067647;
    --amber:#B54708;
    --red:#B42318;
}

html, body, [class*="css"] {
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
}

.stApp { background:var(--canvas); color:var(--ink); }

.block-container {
    max-width:1480px;
    padding-top:1.15rem;
    padding-bottom:3rem;
    padding-left:2rem;
    padding-right:2rem;
}

/* Hide Streamlit visual clutter while preserving app controls. */
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
[data-testid="stToolbar"] { right:.6rem; }

h1,h2,h3,h4 {
    color:var(--ink)!important;
    letter-spacing:-.025em;
}

h2 { margin-top:1.15rem!important; }
h3 { margin-top:1rem!important; }

/* Header */
.sci-topline {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    margin-bottom:.75rem;
}
.sci-brandline {
    display:flex;
    align-items:center;
    gap:.55rem;
    color:#475467;
    font-size:.76rem;
    font-weight:700;
    letter-spacing:.06em;
    text-transform:uppercase;
}
.sci-dot {
    width:8px;height:8px;border-radius:50%;background:#175CD3;display:inline-block;
}
.sci-status {
    border:1px solid #D0D5DD;
    background:#FFF;
    border-radius:999px;
    padding:.28rem .58rem;
    color:#475467;
    font-size:.72rem;
    font-weight:700;
    white-space:nowrap;
}
.sci-title {
    color:var(--ink);
    font-size:clamp(1.75rem,2.8vw,2.45rem);
    line-height:1.06;
    font-weight:780;
    letter-spacing:-.045em;
    margin:0;
}
.sci-subtitle {
    color:var(--muted);
    font-size:.92rem;
    line-height:1.55;
    max-width:980px;
    margin-top:.48rem;
    margin-bottom:1.15rem;
}
.sci-rule { border-top:1px solid var(--line); margin-bottom:1rem; }

/* Sidebar */
[data-testid="stSidebar"] {
    background:var(--navy-950);
    border-right:1px solid #16324A;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top:1rem;
}
[data-testid="stSidebar"] * { color:#F8FAFC!important; }
[data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.11)!important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] input {
    background:#10283D!important;
    border-color:#28465F!important;
    color:#FFF!important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    border-radius:8px;
    padding:.38rem .5rem;
    margin:.08rem 0;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background:rgba(255,255,255,.065);
}
.sidebar-brand {
    padding:.25rem .15rem .85rem .15rem;
}
.sidebar-kicker {
    color:#9FB4C8!important;
    font-size:.68rem;
    font-weight:750;
    letter-spacing:.10em;
    text-transform:uppercase;
}
.sidebar-title {
    color:#FFF!important;
    font-size:1.08rem;
    font-weight:750;
    line-height:1.25;
    margin-top:.25rem;
}
.sidebar-note {
    color:#A8BBCB!important;
    font-size:.76rem;
    line-height:1.45;
    margin-top:.35rem;
}
.sidebar-model {
    border:1px solid rgba(255,255,255,.12);
    background:rgba(255,255,255,.035);
    border-radius:10px;
    padding:.72rem .78rem;
    margin-top:.35rem;
}
.sidebar-model strong { font-size:.78rem; }
.sidebar-model div { color:#A8BBCB!important; font-size:.72rem; margin-top:.2rem; }

/* Metrics */
[data-testid="stMetric"] {
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:10px;
    padding:.9rem .95rem;
    min-height:103px;
    box-shadow:0 1px 2px rgba(16,24,40,.025);
}
[data-testid="stMetricLabel"] { color:var(--muted)!important; font-weight:650; }
[data-testid="stMetricValue"] {
    color:var(--ink)!important;
    font-variant-numeric:tabular-nums;
    letter-spacing:-.025em;
}
[data-testid="stMetricDelta"] { font-size:.74rem; }

/* Cards */
.sci-card {
    background:#FFF;
    border:1px solid var(--line);
    border-radius:10px;
    padding:.95rem 1rem;
    margin-bottom:.7rem;
    min-height:92px;
    box-shadow:0 1px 2px rgba(16,24,40,.02);
}
.sci-card-label {
    color:var(--muted);
    font-size:.70rem;
    font-weight:720;
    text-transform:uppercase;
    letter-spacing:.055em;
}
.sci-card-value {
    color:var(--ink);
    font-size:1rem;
    font-weight:720;
    margin-top:.28rem;
    overflow-wrap:anywhere;
}
.sci-note { color:var(--muted); font-size:.78rem; line-height:1.45; margin-top:.28rem; }

/* Status chips */
.sci-chip {
    display:inline-flex;align-items:center;
    border-radius:999px;
    padding:.22rem .5rem;
    font-size:.71rem;
    font-weight:750;
    border:1px solid #D0D5DD;
    background:#FFF;
    color:#475467;
}
.sci-chip.red { color:#B42318; border-color:#FECDCA; background:#FEF3F2; }
.sci-chip.amber { color:#B54708; border-color:#FEDF89; background:#FFFAEB; }
.sci-chip.green { color:#067647; border-color:#ABEFC6; background:#ECFDF3; }
.sci-chip.blue { color:#175CD3; border-color:#B2CCFF; background:#EFF4FF; }

/* Tables */
[data-testid="stDataFrame"] {
    border:1px solid var(--line);
    border-radius:10px;
    overflow:hidden;
    background:#FFF;
}
[data-testid="stDataFrame"] * { font-size:.80rem; }

/* Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background:#FFF!important;
    color:var(--ink)!important;
    border-color:#D0D5DD!important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-size:.82rem!important;
    font-weight:650!important;
    padding-left:.8rem!important;
    padding-right:.8rem!important;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius:9px;
    border-width:1px;
}

/* Buttons */
.stButton > button,.stDownloadButton > button {
    border-radius:8px;
    font-weight:650;
}

/* Plotly containers */
[data-testid="stPlotlyChart"] {
    background:#FFF;
    border:1px solid var(--line);
    border-radius:10px;
    padding:.18rem;
}

hr { border-color:var(--line)!important; }

@media(max-width:900px){
    .block-container{padding-left:.85rem;padding-right:.85rem;}
    .sci-topline{align-items:flex-start;flex-direction:column;gap:.45rem;}
}
</style>
"""


GROUPS = {
    "Executive": [
        "Portfolio Overview",
        "Credit Committee",
    ],
    "Project Review": [
        "Project Dossier",
        "Borrower Financials",
        "Project Finance",
        "Execution Risk",
    ],
    "Risk Analytics": [
        "Stress & Tail Risk",
        "Security & Recovery",
        "Early Warning System",
    ],
    "Portfolio & Evidence": [
        "Evidence & Data Gaps",
        "Portfolio Allocation",
    ],
    "Governance": [
        "Governance",
    ],
}


PAGE_LABELS = {
    "Portfolio Overview": "Portfolio overview",
    "Credit Committee": "Credit committee",
    "Project Dossier": "Project dossier",
    "Borrower Financials": "Borrower financials",
    "Project Finance": "Project finance",
    "Execution Risk": "Execution risk",
    "Stress & Tail Risk": "Stress & tail risk",
    "Security & Recovery": "Security & recovery",
    "Early Warning System": "Early warning",
    "Evidence & Data Gaps": "Evidence & gaps",
    "Portfolio Allocation": "Portfolio allocation",
    "Governance": "Governance",
}


def esc(value: Any) -> str:
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    return html.escape(str(value))


def header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="sci-topline">
          <div class="sci-brandline"><span class="sci-dot"></span>Semiconductor Credit Intelligence</div>
          <div class="sci-status">RESEARCH · CONTROLLED PILOT</div>
        </div>
        <div class="sci-title">{esc(title)}</div>
        <div class="sci-subtitle">{esc(subtitle)}</div>
        <div class="sci-rule"></div>
        """,
        unsafe_allow_html=True,
    )


def card(label: str, value: Any, note: Any | None = None):
    note_html = f'<div class="sci-note">{esc(note)}</div>' if note else ""
    st.markdown(
        f"""
        <div class="sci-card">
          <div class="sci-card-label">{esc(label)}</div>
          <div class="sci-card-value">{esc(value)}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = 390):
    fig.update_layout(
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
            color="#344054",
            size=12,
        ),
        title_font=dict(color="#101828", size=15),
        margin=dict(l=28, r=20, t=46, b=42),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#D0D5DD", font_color="#101828"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, zeroline=False, linecolor="#E4E7EC", automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#EEF2F6", zeroline=False, automargin=True),
        hovermode="closest",
        dragmode="pan",
        uirevision="sci-banking-v3",
    )
    return fig


def project_selector(df: pd.DataFrame, key: str):
    options = df[["project_id", "company"]].drop_duplicates().copy()
    options["label"] = options["company"].astype(str) + "  ·  " + options["project_id"].astype(str)
    selected = st.selectbox("Project", options["label"].tolist(), key=key)
    return options.loc[options["label"].eq(selected), "project_id"].iloc[0]


def sidebar(master: pd.DataFrame):
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <div class="sidebar-kicker">Credit risk workspace</div>
              <div class="sidebar-title">Semiconductor Credit Intelligence</div>
              <div class="sidebar-note">Institutional research decision-support for analyst and committee review.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        group = st.selectbox("Workspace", list(GROUPS.keys()), index=0)
        pages = GROUPS[group]
        if len(pages) == 1:
            page = pages[0]
            st.caption(PAGE_LABELS[page])
        else:
            page = st.radio(
                "View",
                pages,
                format_func=lambda x: PAGE_LABELS.get(x, x),
                label_visibility="collapsed",
            )

        st.divider()

        with st.expander("Portfolio filters", expanded=False):
            states = []
            if "state" in master.columns:
                state_values = sorted(
                    core.text(master, "state").replace("", pd.NA).dropna().unique().tolist()
                )
                states = st.multiselect("State", state_values)

            risk_classes = []
            if "integrated_banking_risk_class" in master.columns:
                risk_values = sorted(
                    core.text(master, "integrated_banking_risk_class")
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )
                risk_classes = st.multiselect("Integrated risk", risk_values)

            ews_filter = []
            if "final_ews_status" in master.columns:
                ews_values = sorted(
                    core.text(master, "final_ews_status")
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )
                ews_filter = st.multiselect("EWS", ews_values)

            company_search = st.text_input("Company", placeholder="Search company")

        filtered = master.copy()
        if states:
            filtered = filtered[filtered["state"].isin(states)]
        if risk_classes:
            filtered = filtered[
                core.text(filtered, "integrated_banking_risk_class").isin(risk_classes)
            ]
        if ews_filter:
            filtered = filtered[core.text(filtered, "final_ews_status").isin(ews_filter)]
        if company_search:
            filtered = filtered[
                core.text(filtered, "company").str.contains(company_search, case=False, na=False)
            ]

        st.divider()
        st.markdown(
            """
            <div class="sidebar-model">
              <strong>Model status</strong>
              <div>Research / controlled pilot</div>
              <div>Human review required</div>
              <div>No automated lending decision</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"{len(filtered)} of {len(master)} projects in view")

    return page, filtered


def install_overrides():
    core.CSS = CSS
    core.header = header
    core.card = card
    core.style_fig = style_fig
    core.sidebar = sidebar
    core.project_selector = project_selector

    # Neutral institutional palette; colors encode status only.
    core.NAVY = "#0B1F33"
    core.NAVY_2 = "#12324F"
    core.INK = "#101828"
    core.TEXT = "#344054"
    core.MUTED = "#667085"
    core.BLUE = "#175CD3"
    core.TEAL = "#067647"
    core.AMBER = "#B54708"
    core.ORANGE = "#B54708"
    core.RED = "#B42318"
    core.BORDER = "#E4E7EC"
    core.GRID = "#EEF2F6"
    core.SURFACE = "#FFFFFF"
    core.BACKGROUND = "#F7F9FC"

    core.RISK_COLORS = {
        "LOW": "#067647",
        "MODERATE_LOW": "#175CD3",
        "MODERATE": "#B54708",
        "ELEVATED": "#C4320A",
        "HIGH": "#B42318",
        "INSUFFICIENT_EVIDENCE": "#98A2B3",
        "NOT_OBSERVABLE": "#98A2B3",
        "NOT_AVAILABLE": "#98A2B3",
    }
    core.EWS_COLORS = {
        "GREEN": "#067647",
        "AMBER": "#B54708",
        "RED": "#B42318",
        "INSUFFICIENT_EVIDENCE": "#98A2B3",
        "NOT_OBSERVABLE": "#98A2B3",
        "NOT_AVAILABLE": "#98A2B3",
    }


def render_app():
    install_overrides()
    core.render_app()
