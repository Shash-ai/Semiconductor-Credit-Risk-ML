from __future__ import annotations

import html
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import banking_dashboard_v2 as core


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

#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
[data-testid="stToolbar"] { right:.6rem; }

h1,h2,h3,h4 {
    color:var(--ink)!important;
    letter-spacing:-.025em;
    overflow-wrap:anywhere;
    white-space:normal!important;
}

p, li, span, label, div[data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"],
[data-testid="stAlert"] p,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    overflow-wrap:anywhere!important;
    word-break:normal!important;
    white-space:normal!important;
    text-overflow:clip!important;
}

h2 { margin-top:1.15rem!important; }
h3 { margin-top:1rem!important; }

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
    flex-wrap:wrap;
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
    white-space:normal;
    text-align:center;
}
.sci-title {
    color:var(--ink);
    font-size:clamp(1.75rem,2.8vw,2.45rem);
    line-height:1.06;
    font-weight:780;
    letter-spacing:-.045em;
    margin:0;
    overflow-wrap:anywhere;
}
.sci-subtitle {
    color:var(--muted);
    font-size:.92rem;
    line-height:1.55;
    max-width:980px;
    margin-top:.48rem;
    margin-bottom:1.15rem;
    overflow-wrap:anywhere;
    white-space:normal;
}
.sci-rule { border-top:1px solid var(--line); margin-bottom:1rem; }

[data-testid="stSidebar"] {
    background:var(--navy-950);
    border-right:1px solid #16324A;
}
[data-testid="stSidebar"] > div:first-child { padding-top:1rem; }
[data-testid="stSidebar"] * {
    color:#F8FAFC!important;
    overflow-wrap:anywhere!important;
    white-space:normal!important;
    text-overflow:clip!important;
}
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
.sidebar-brand { padding:.25rem .15rem .85rem .15rem; }
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

[data-testid="stMetric"] {
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:10px;
    padding:.9rem .95rem;
    min-height:108px;
    box-shadow:0 1px 2px rgba(16,24,40,.025);
    overflow:visible!important;
}
[data-testid="stMetricLabel"] { color:var(--muted)!important; font-weight:650; }
[data-testid="stMetricValue"] {
    color:var(--ink)!important;
    font-variant-numeric:tabular-nums;
    letter-spacing:-.025em;
    line-height:1.18!important;
}
[data-testid="stMetricDelta"] { font-size:.74rem; line-height:1.28!important; }

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
    overflow-wrap:anywhere;
}
.sci-card-value {
    color:var(--ink);
    font-size:1rem;
    font-weight:720;
    margin-top:.28rem;
    overflow-wrap:anywhere;
    white-space:normal;
}
.sci-note {
    color:var(--muted);
    font-size:.78rem;
    line-height:1.45;
    margin-top:.28rem;
    overflow-wrap:anywhere;
    white-space:normal;
}

.sci-state {
    background:#FFF;
    border:1px solid var(--line);
    border-left:4px solid #98A2B3;
    border-radius:10px;
    padding:1rem 1.05rem;
    margin:.25rem 0 1rem 0;
}
.sci-state.info { border-left-color:#175CD3; }
.sci-state.warn { border-left-color:#B54708; }
.sci-state.good { border-left-color:#067647; }
.sci-state-title {
    color:var(--ink);
    font-size:.94rem;
    font-weight:750;
    margin-bottom:.28rem;
    overflow-wrap:anywhere;
}
.sci-state-body {
    color:var(--text);
    font-size:.82rem;
    line-height:1.5;
    overflow-wrap:anywhere;
    white-space:normal;
}
.sci-state-foot {
    color:var(--muted);
    font-size:.76rem;
    line-height:1.45;
    margin-top:.45rem;
    overflow-wrap:anywhere;
}

.sci-kv-grid {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:.7rem;
    margin:.35rem 0 1rem 0;
}
.sci-kv {
    background:#FFF;
    border:1px solid var(--line);
    border-radius:9px;
    padding:.72rem .82rem;
    min-width:0;
}
.sci-kv-label {
    color:var(--muted);
    font-size:.68rem;
    font-weight:720;
    letter-spacing:.045em;
    text-transform:uppercase;
    overflow-wrap:anywhere;
}
.sci-kv-value {
    color:var(--ink);
    font-size:.86rem;
    font-weight:650;
    line-height:1.4;
    margin-top:.22rem;
    overflow-wrap:anywhere;
    white-space:normal;
}

.sci-table-wrap {
    width:100%;
    overflow-x:auto;
    border:1px solid var(--line);
    border-radius:10px;
    background:#FFF;
    margin:.35rem 0 1rem 0;
}
.sci-table {
    width:100%;
    border-collapse:collapse;
    table-layout:auto;
    font-size:.78rem;
}
.sci-table th {
    text-align:left;
    vertical-align:top;
    color:#475467;
    background:#F9FAFB;
    border-bottom:1px solid var(--line);
    padding:.62rem .68rem;
    font-weight:720;
    white-space:normal;
    overflow-wrap:anywhere;
    min-width:120px;
    max-width:260px;
}
.sci-table td {
    vertical-align:top;
    color:#344054;
    border-bottom:1px solid #F0F2F5;
    padding:.62rem .68rem;
    line-height:1.42;
    white-space:normal;
    overflow-wrap:anywhere;
    word-break:break-word;
    min-width:120px;
    max-width:360px;
}
.sci-table tr:last-child td { border-bottom:none; }

[data-testid="stDataFrame"] {
    border:1px solid var(--line);
    border-radius:10px;
    overflow:hidden;
    background:#FFF;
}
[data-testid="stDataFrame"] * { font-size:.80rem; }

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background:#FFF!important;
    color:var(--ink)!important;
    border-color:#D0D5DD!important;
}
div[data-baseweb="select"] span,
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li {
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    text-overflow:clip!important;
    line-height:1.35!important;
}

button[data-baseweb="tab"] {
    font-size:.82rem!important;
    font-weight:650!important;
    padding-left:.8rem!important;
    padding-right:.8rem!important;
    white-space:normal!important;
    height:auto!important;
    line-height:1.3!important;
}

div[data-testid="stAlert"] {
    border-radius:9px;
    border-width:1px;
    overflow-wrap:anywhere;
}

.stButton > button,.stDownloadButton > button {
    border-radius:8px;
    font-weight:650;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
}

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
    .sci-kv-grid{grid-template-columns:1fr;}
}
</style>
"""


GROUPS = {
    "Executive": ["Portfolio Overview", "Credit Committee"],
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
    "Governance": ["Governance"],
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


def readable_label(name: str) -> str:
    return str(name).replace("_", " ").strip().title()


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


def state_panel(title: str, body: str, foot: str | None = None, tone: str = "info"):
    foot_html = f'<div class="sci-state-foot">{esc(foot)}</div>' if foot else ""
    st.markdown(
        f"""
        <div class="sci-state {esc(tone)}">
          <div class="sci-state-title">{esc(title)}</div>
          <div class="sci-state-body">{esc(body)}</div>
          {foot_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def detail_grid(items: list[tuple[str, Any]]):
    cells = []
    for label, value in items:
        cells.append(
            f"""
            <div class="sci-kv">
              <div class="sci-kv-label">{esc(label)}</div>
              <div class="sci-kv-value">{esc(value)}</div>
            </div>
            """
        )
    st.markdown(
        '<div class="sci-kv-grid">' + "".join(cells) + "</div>",
        unsafe_allow_html=True,
    )


def wrapped_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 50):
    if df is None or df.empty:
        st.caption("No records available.")
        return

    work = df.copy()
    if columns is not None:
        cols = [c for c in columns if c in work.columns]
        if not cols:
            st.caption("No displayable fields are available.")
            return
        work = work[cols]

    work = work.head(max_rows)
    head = "".join(f"<th>{esc(readable_label(c))}</th>" for c in work.columns)

    body_rows = []
    for _, row in work.iterrows():
        cells = []
        for col in work.columns:
            val = row[col]
            text = esc(val)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                text = f'<a href="{html.escape(val, quote=True)}" target="_blank" rel="noopener">Open source</a>'
            cells.append(f"<td>{text}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    st.markdown(
        f"""
        <div class="sci-table-wrap">
          <table class="sci-table">
            <thead><tr>{head}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df)} records.")


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
        xaxis=dict(showgrid=False, zeroline=False, linecolor="#E4E7EC", automargin=True, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#EEF2F6", zeroline=False, automargin=True, tickfont=dict(size=11)),
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
                state_values = sorted(core.text(master, "state").replace("", pd.NA).dropna().unique().tolist())
                states = st.multiselect("State", state_values)

            risk_classes = []
            if "integrated_banking_risk_class" in master.columns:
                risk_values = sorted(core.text(master, "integrated_banking_risk_class").replace("", pd.NA).dropna().unique().tolist())
                risk_classes = st.multiselect("Integrated risk", risk_values)

            ews_filter = []
            if "final_ews_status" in master.columns:
                ews_values = sorted(core.text(master, "final_ews_status").replace("", pd.NA).dropna().unique().tolist())
                ews_filter = st.multiselect("EWS", ews_values)

            company_search = st.text_input("Company", placeholder="Search company")

        filtered = master.copy()
        if states:
            filtered = filtered[filtered["state"].isin(states)]
        if risk_classes:
            filtered = filtered[core.text(filtered, "integrated_banking_risk_class").isin(risk_classes)]
        if ews_filter:
            filtered = filtered[core.text(filtered, "final_ews_status").isin(ews_filter)]
        if company_search:
            filtered = filtered[core.text(filtered, "company").str.contains(company_search, case=False, na=False)]

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


def project_master_row(master: pd.DataFrame, project_id: Any) -> pd.Series:
    rows = master[master["project_id"].astype(str).eq(str(project_id))]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype="object")


def gap_rows(project_id: Any, layer: str | None = None) -> pd.DataFrame:
    gaps = core.optional_csv(core.GAP_FILE)
    if gaps.empty or "project_id" not in gaps.columns:
        return pd.DataFrame()
    out = gaps[gaps["project_id"].astype(str).eq(str(project_id))].copy()
    if layer and "banking_layer" in out.columns:
        out = out[out["banking_layer"].astype(str).str.upper().eq(layer.upper())]
    return out


def evidence_rows(project_id: Any) -> pd.DataFrame:
    evidence = core.optional_csv(core.EVIDENCE_FILE)
    if evidence.empty or "project_id" not in evidence.columns:
        return pd.DataFrame()
    return evidence[evidence["project_id"].astype(str).eq(str(project_id))].copy()


def page_committee(master: pd.DataFrame):
    header(
        "Credit Committee",
        "Human-review queue with full-text committee posture, escalation flags, evidence quality and monitoring tier.",
    )

    tier = core.text(master, "committee_monitoring_tier")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Immediate review", int(tier.eq("TIER_1_IMMEDIATE_REVIEW").sum()))
    c2.metric("Enhanced monitoring", int(tier.eq("TIER_2_ENHANCED_MONITORING").sum()))
    c3.metric("Data verification", int(tier.eq("TIER_3_DATA_VERIFICATION").sum()))
    c4.metric("Standard monitoring", int(tier.eq("TIER_4_STANDARD_MONITORING").sum()))

    display = master.copy()
    priority_order = {
        "TIER_1_IMMEDIATE_REVIEW": 1,
        "TIER_2_ENHANCED_MONITORING": 2,
        "TIER_3_DATA_VERIFICATION": 3,
        "TIER_3_STANDARD_REVIEW": 4,
        "TIER_4_STANDARD_MONITORING": 5,
    }
    display["_priority"] = core.text(display, "committee_monitoring_tier").map(priority_order).fillna(99)
    display["_risk"] = core.num(display, "integrated_banking_risk_score")
    display = display.sort_values(["_priority", "_risk"], ascending=[True, False], na_position="last")

    wrapped_table(
        display,
        [
            "project_id",
            "company",
            "state",
            "integrated_banking_risk_score",
            "integrated_banking_risk_class",
            "integrated_evidence_quality_class",
            "final_ews_status",
            "committee_monitoring_tier",
        ],
    )

    st.subheader("Full committee review text")
    pid = project_selector(display, "committee_full_text")
    row = project_master_row(display, pid)
    detail_grid(
        [
            ("Critical review flags", core.clean_display(row.get("critical_review_flags"))),
            ("Committee posture", core.clean_display(row.get("credit_committee_posture"))),
            ("Model explanation", core.clean_display(row.get("integrated_credit_committee_explanation"))),
            ("Evidence quality", core.clean_display(row.get("integrated_evidence_quality_class"))),
        ]
    )
    st.caption("Committee posture is workflow guidance for human review, not an automated lending decision.")


def page_borrower(master: pd.DataFrame):
    header(
        "Borrower Financials",
        "Borrower-level profitability, leverage, liquidity and repayment-capacity evidence, with missing fields kept explicit.",
    )

    borrower = core.optional_csv(core.BORROWER_FILE)
    if borrower.empty:
        state_panel(
            "Borrower financial dataset unavailable",
            "No borrower financial panel is currently available for display.",
            "The application does not infer borrower financials from project investment.",
            "warn",
        )
        return

    project_id = project_selector(master, "borrower_project_v3")
    b = borrower[borrower["project_id"].astype(str).eq(str(project_id))].copy()
    if b.empty:
        state_panel(
            "No borrower observation",
            "No borrower financial observation is linked to this project.",
            "Missing values remain unavailable rather than being imputed.",
            "warn",
        )
        return

    latest = b.iloc[-1]
    if pd.isna(latest.get("borrower_financial_risk_score")):
        state_panel(
            "Borrower risk is not observable from current evidence",
            "The borrower layer does not have enough verified or comparable financial fields to support a borrower risk score for this project.",
            "This is an evidence limitation, not a zero-risk assessment.",
            "warn",
        )
    else:
        state_panel(
            "Borrower evidence available",
            "The borrower layer contains usable financial evidence for this project. Coverage may still be partial.",
            "Borrower-level evidence is not automatically treated as project-level debt.",
            "good",
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Financial strength", core.fmt(latest.get("borrower_financial_strength_score")), core.clean_display(latest.get("borrower_financial_strength_class")))
    c2.metric("Debt / Equity", core.fmt(latest.get("debt_equity_ratio")))
    c3.metric("Debt / EBITDA", core.fmt(latest.get("debt_to_ebitda")))
    c4.metric("Interest coverage", core.fmt(latest.get("interest_coverage_effective")))

    detail_grid(
        [
            ("Financial year", core.clean_display(latest.get("financial_year"))),
            ("Revenue", core.money(latest.get("revenue_crore"))),
            ("EBITDA", core.money(latest.get("ebitda_crore"))),
            ("PAT", core.money(latest.get("pat_crore"))),
            ("Borrower data coverage", core.fmt_pct(latest.get("borrower_financial_coverage_pct"))),
            ("Borrower score coverage", core.fmt_pct(latest.get("borrower_score_coverage_pct"))),
            ("Monitoring signal", core.clean_display(latest.get("borrower_monitoring_signal"))),
            ("Financial deterioration flags", core.fmt(latest.get("financial_deterioration_flag_count"), 0)),
        ]
    )

    with st.expander("Underlying borrower record", expanded=False):
        wrapped_table(
            b,
            [
                "financial_year",
                "revenue_crore",
                "ebitda_crore",
                "ebitda_margin_pct",
                "pat_crore",
                "pat_margin_pct",
                "total_debt_crore",
                "debt_equity_ratio",
                "debt_to_ebitda",
                "interest_coverage_effective",
                "borrower_financial_risk_class",
                "borrower_monitoring_signal",
            ],
        )


def page_project_finance(master: pd.DataFrame):
    header(
        "Project Finance Underwriting",
        "Debt-service, leverage, DCCO and cost-overrun analysis only where transaction-level information is verified.",
    )

    pf = core.optional_csv(core.PROJECT_FINANCE_FILE)
    if pf.empty:
        state_panel(
            "Project-finance output unavailable",
            "The project-finance underwriting file is not available.",
            "No DSCR, project debt or debt-service metrics are inferred.",
            "warn",
        )
        return

    project_id = project_selector(master, "pf_project_v3")
    row = pf[pf["project_id"].astype(str).eq(str(project_id))].copy()
    if row.empty:
        state_panel(
            "No project-finance record",
            "No project-finance observation is linked to this project.",
            "Transaction-level fields remain unavailable.",
            "warn",
        )
        return

    r = row.iloc[0]
    master_row = project_master_row(master, project_id)
    verified = str(r.get("banking_data_verified")).strip().lower() in {"true", "1", "yes"}
    verified_coverage = r.get("verified_project_finance_coverage_pct")
    if pd.isna(verified_coverage):
        verified_coverage = r.get("underwriting_data_coverage_pct")

    if not verified:
        state_panel(
            "Verified transaction data not yet available",
            "Project-level debt, annual debt service and cash available for debt service are not verified for this project, so DSCR and related underwriting ratios are intentionally withheld.",
            "Public project investment is shown only as project scale; it is not bank exposure, sanctioned debt or EAD.",
            "warn",
        )
    else:
        state_panel(
            "Verified project-finance evidence available",
            "The underwriting layer contains verified transaction-level data for this project.",
            "Ratios remain research screening outputs and require human credit review.",
            "good",
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Verified DSCR", core.fmt(r.get("dscr_verified")))
    c2.metric("Verified D/E", core.fmt(r.get("debt_equity_ratio_verified")))
    c3.metric("DCCO delay", f"{core.fmt(r.get('dcco_delay_days_verified'), 0)} days" if pd.notna(r.get("dcco_delay_days_verified")) else "—")
    c4.metric("Verified coverage", core.fmt_pct(verified_coverage))

    detail_grid(
        [
            ("Project investment scale", core.money(master_row.get("investment_crore"))),
            ("Verification status", core.clean_display(r.get("verification_status"))),
            ("Sanctioned project debt", core.money(r.get("sanctioned_debt_crore"))),
            ("Outstanding project debt", core.money(r.get("outstanding_debt_crore"))),
            ("Annual principal due", core.money(r.get("annual_principal_due_crore"))),
            ("Annual interest due", core.money(r.get("annual_interest_due_crore"))),
            ("Cash available for debt service", core.money(r.get("cash_available_for_debt_service_crore"))),
            ("Project finance review priority", core.clean_display(r.get("project_finance_review_priority"))),
        ]
    )

    gaps = gap_rows(project_id, "PROJECT_FINANCE")
    st.subheader("Data required to activate underwriting")
    if gaps.empty:
        st.caption("No project-finance gaps are registered for this project.")
    else:
        wrapped_table(gaps, ["missing_field", "status", "safe_treatment"])

    evidence = evidence_rows(project_id)
    if not evidence.empty:
        st.subheader("Current source-backed evidence")
        wrapped_table(
            evidence,
            ["field", "verified_value", "unit", "evidence_scope", "banking_usability", "source_document", "verification_status", "interpretation"],
            max_rows=20,
        )

    with st.expander("Technical project-finance record", expanded=False):
        wrapped_table(
            row,
            ["verification_status", "banking_data_verified", "verified_project_finance_coverage_pct", "dscr_screening_signal", "interest_coverage_screening_signal", "cost_overrun_screening_signal", "dcco_screening_signal", "project_finance_review_priority"],
        )


def page_execution(master: pd.DataFrame):
    header(
        "Execution & Implementation Risk",
        "Project status, commissioning timing, DCCO, completion and cost-overrun evidence with explicit coverage limits.",
    )

    execution = core.optional_csv(core.EXECUTION_FILE)
    if execution.empty:
        state_panel(
            "Execution-risk output unavailable",
            "The execution-risk panel is not available.",
            "No execution status is inferred from unrelated financial data.",
            "warn",
        )
        return

    project_id = project_selector(master, "execution_project_v3")
    e = execution[execution["project_id"].astype(str).eq(str(project_id))].copy()
    if e.empty:
        state_panel(
            "No execution observation",
            "No execution record is linked to this project.",
            "Missing implementation milestones remain unavailable.",
            "warn",
        )
        return

    r = e.iloc[0]
    coverage = pd.to_numeric(pd.Series([r.get("execution_data_coverage_pct")]), errors="coerce").iloc[0]
    if pd.isna(coverage) or coverage < 50:
        state_panel(
            "Execution evidence is partial",
            "Current execution evidence does not cover enough implementation fields for a bank-style project monitoring view.",
            "Missing completion, DCCO or cost-overrun fields remain explicit.",
            "warn",
        )
    else:
        state_panel(
            "Execution evidence available",
            "The project has source-backed execution evidence, although some implementation fields may still be missing.",
            None,
            "good",
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Execution risk", core.fmt(r.get("execution_risk_score")), core.clean_display(r.get("execution_risk_class")))
    c2.metric("Completion", core.fmt_pct(r.get("project_completion_pct")))
    c3.metric("DCCO delay", f"{core.fmt(r.get('dcco_delay_days'), 0)} days" if pd.notna(r.get("dcco_delay_days")) else "—")
    c4.metric("Cost overrun", core.fmt_pct(r.get("cost_overrun_pct")))

    detail_grid(
        [
            ("Project status", core.clean_display(r.get("project_status"))),
            ("Status class", core.clean_display(r.get("project_status_class"))),
            ("Execution data coverage", core.fmt_pct(r.get("execution_data_coverage_pct"))),
            ("Execution score coverage", core.fmt_pct(r.get("execution_score_coverage_pct"))),
            ("Monitoring signal", core.clean_display(r.get("execution_monitoring_signal"))),
            ("Review priority", core.clean_display(r.get("execution_review_priority"))),
            ("Entity reconciliation flag", core.clean_display(r.get("entity_reconciliation_flag"))),
            ("Project value conflict flag", core.clean_display(r.get("project_value_conflict_flag"))),
        ]
    )

    gaps = gap_rows(project_id, "EXECUTION")
    if not gaps.empty:
        st.subheader("Execution evidence gaps")
        wrapped_table(gaps, ["missing_field", "status", "safe_treatment"])

    with st.expander("Underlying execution record", expanded=False):
        wrapped_table(e, max_rows=10)


def page_security(master: pd.DataFrame):
    header(
        "Security & Recovery",
        "Collateral, guarantees and recovery-support analysis only where verified project exposure and security evidence exist.",
    )

    security = core.optional_csv(core.SECURITY_FILE)
    if security.empty:
        state_panel(
            "Security/recovery output unavailable",
            "The security and recovery panel is not available.",
            "No collateral or recovery values are inferred.",
            "warn",
        )
        return

    project_id = project_selector(master, "security_project_v3")
    s = security[security["project_id"].astype(str).eq(str(project_id))].copy()
    if s.empty:
        state_panel(
            "No security record",
            "No security observation is linked to this project.",
            "Security coverage remains unmeasured.",
            "warn",
        )
        return

    r = s.iloc[0]
    status = core.clean_display(r.get("security_analysis_status"))
    available = status == "SECURITY_ANALYSIS_AVAILABLE"

    if not available:
        state_panel(
            "Security analysis intentionally unavailable",
            "Verified project exposure and eligible collateral or recovery evidence are not available, so security coverage and recovery coverage ratios are not calculated.",
            "Project investment is not substituted for bank exposure.",
            "warn",
        )
    else:
        state_panel(
            "Security analysis available",
            "Verified project exposure and security evidence are available for this project.",
            "Coverage remains a research decision-support measure, not regulatory LGD.",
            "good",
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Security analysis", status)
    c2.metric("Security coverage", core.fmt(r.get("project_security_coverage_ratio")))
    c3.metric("Recovery coverage", core.fmt(r.get("project_recovery_coverage_ratio")))

    detail_grid(
        [
            ("Verified collateral records", core.fmt(r.get("verified_collateral_records"), 0)),
            ("Project exposure", core.money(r.get("project_exposure_crore"))),
            ("Eligible collateral", core.money(r.get("verified_eligible_collateral_crore"))),
            ("Verified guarantees", core.money(r.get("verified_guarantee_amount_crore"))),
            ("Verified recovery value", core.money(r.get("verified_recovery_value_crore"))),
            ("Security evidence available", core.clean_display(r.get("security_evidence_available"))),
        ]
    )

    gaps = gap_rows(project_id, "SECURITY_RECOVERY")
    st.subheader("Data required for security analysis")
    if gaps.empty:
        st.caption("No security/recovery gaps are registered for this project.")
    else:
        wrapped_table(gaps, ["missing_field", "status", "safe_treatment"])

    with st.expander("Technical security record", expanded=False):
        wrapped_table(s, max_rows=10)


def page_ews(master: pd.DataFrame):
    header(
        "Early Warning System",
        "Current monitoring signals with explicit separation between cross-sectional snapshots and genuine longitudinal observations.",
    )

    ews = core.optional_csv(core.EWS_FILE)
    if ews.empty:
        state_panel(
            "EWS output unavailable",
            "The early-warning panel is not available.",
            "No monitoring status is inferred.",
            "warn",
        )
        return

    project_id = project_selector(master, "ews_project_v3")
    e = ews[ews["project_id"].astype(str).eq(str(project_id))].copy()
    if e.empty:
        state_panel(
            "No EWS observation",
            "No early-warning observation is linked to this project.",
            "Longitudinal status remains unavailable.",
            "warn",
        )
        return

    r = e.iloc[0]
    maturity = core.clean_display(r.get("monitoring_maturity"))
    verified_obs = pd.to_numeric(pd.Series([r.get("verified_monitoring_observations")]), errors="coerce").iloc[0]

    if maturity == "SNAPSHOT_ONLY" or pd.isna(verified_obs) or verified_obs < 2:
        state_panel(
            "Snapshot-only monitoring",
            "The current EWS combines available borrower, execution, stress and tail-risk signals at one point in time. It does not claim an observed deterioration trend.",
            "A longitudinal EWS requires repeated verified observations such as DSCR, repayment behaviour, covenant status, rating actions and project milestones.",
            "warn",
        )
    else:
        state_panel(
            "Longitudinal monitoring available",
            "Repeated verified observations are available for this project.",
            "Trend signals should still be interpreted by a human credit reviewer.",
            "good",
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final EWS", core.clean_display(r.get("final_ews_status")))
    c2.metric("Snapshot score", core.fmt(r.get("ews_current_snapshot_score")))
    c3.metric("Monitoring maturity", maturity)
    c4.metric("Verified observations", core.fmt(r.get("verified_monitoring_observations"), 0))

    detail_grid(
        [
            ("Borrower component", core.fmt(r.get("ews_borrower_component"))),
            ("Execution component", core.fmt(r.get("ews_execution_component"))),
            ("Stress component", core.fmt(r.get("ews_stress_component"))),
            ("Tail-risk component", core.fmt(r.get("ews_tail_risk_component"))),
            ("Current component coverage", core.fmt_pct(r.get("ews_current_coverage_pct"))),
            ("Current snapshot status", core.clean_display(r.get("ews_current_status"))),
            ("First verified observation", core.clean_display(r.get("first_verified_observation"))),
            ("Latest verified observation", core.clean_display(r.get("latest_verified_observation"))),
        ]
    )

    st.subheader("What is needed for true longitudinal monitoring")
    requirements = pd.DataFrame(
        [
            ["Debt service", "Repeated verified DSCR / CADS / principal / interest observations"],
            ["Repayment behaviour", "Days past due or other verified delinquency observations"],
            ["Covenants", "Verified covenant compliance or breach history"],
            ["External credit", "Rating actions and outlook changes over time"],
            ["Project execution", "Repeated completion, DCCO and cost-overrun observations"],
        ],
        columns=["Monitoring layer", "Required evidence"],
    )
    wrapped_table(requirements)

    with st.expander("Technical EWS record", expanded=False):
        wrapped_table(
            e,
            ["observation_date", "observation_type", "financial_year", "ews_current_snapshot_score", "ews_current_component_count", "ews_current_coverage_pct", "ews_current_status", "verified_monitoring_observations", "monitoring_maturity", "final_ews_status", "final_monitoring_priority"],
        )


def page_evidence(master: pd.DataFrame):
    header(
        "Evidence & Data Gaps",
        "Source provenance, verified evidence and missing banking information presented without truncated explanatory text.",
    )

    project_id = project_selector(master, "evidence_project_v3")
    evidence = evidence_rows(project_id)
    gaps = gap_rows(project_id)

    tab1, tab2 = st.tabs(["Evidence ledger", "Missing banking information"])

    with tab1:
        if evidence.empty:
            state_panel(
                "No field-level evidence",
                "No verified or source-backed evidence records are linked to this project in the dashboard evidence panel.",
                "This does not imply that evidence does not exist outside the current project files.",
                "warn",
            )
        else:
            wrapped_table(
                evidence,
                ["field", "verified_value", "unit", "evidence_scope", "banking_usability", "source_type", "source_document", "source_url", "verification_status", "interpretation"],
                max_rows=50,
            )

    with tab2:
        if gaps.empty:
            state_panel(
                "No registered dashboard gaps",
                "No missing-field records are registered for this project in the current dashboard gap panel.",
                "This is not a statement of full underwriting completeness.",
                "good",
            )
        else:
            wrapped_table(gaps, ["banking_layer", "missing_field", "status", "safe_treatment"], max_rows=50)


def install_overrides():
    core.CSS = CSS
    core.header = header
    core.card = card
    core.style_fig = style_fig
    core.sidebar = sidebar
    core.project_selector = project_selector

    core.page_committee = page_committee
    core.page_borrower = page_borrower
    core.page_project_finance = page_project_finance
    core.page_execution = page_execution
    core.page_security = page_security
    core.page_ews = page_ews
    core.page_evidence = page_evidence

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
