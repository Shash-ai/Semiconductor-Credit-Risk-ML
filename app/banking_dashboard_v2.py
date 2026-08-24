from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[1]

BANKING_ROOT = (
    ROOT
    / "04_Banking_Alignment"
)

DATA_DIR = (
    BANKING_ROOT
    / "06_Dashboard_Integration"
)

OUTPUT_DIR = (
    BANKING_ROOT
    / "04_Outputs"
)

PILOT_DIR = (
    BANKING_ROOT
    / "09_Bank_Pilot_Package"
)


MASTER_FILE = (
    DATA_DIR
    / "Banking_Dashboard_Master.csv"
)

KPI_FILE = (
    DATA_DIR
    / "Banking_Dashboard_KPIs.csv"
)

EVIDENCE_FILE = (
    DATA_DIR
    / "Banking_Evidence_Panel.csv"
)

GAP_FILE = (
    DATA_DIR
    / "Banking_Data_Gap_Panel.csv"
)

STRESS_FILE = (
    DATA_DIR
    / "Stress_MC_Risk_Panel.csv"
)

BORROWER_FILE = (
    DATA_DIR
    / "Borrower_Financial_Panel.csv"
)

PROJECT_FINANCE_FILE = (
    OUTPUT_DIR
    / "Project_Finance_Underwriting_Full.csv"
)

EXECUTION_FILE = (
    DATA_DIR
    / "Project_Execution_Panel.csv"
)

SECURITY_FILE = (
    DATA_DIR
    / "Security_Recovery_Panel.csv"
)

EWS_FILE = (
    DATA_DIR
    / "Longitudinal_EWS_Panel.csv"
)

ALLOCATION_FILE = (
    DATA_DIR
    / "Portfolio_Allocation_Panel.csv"
)

READINESS_FILE = (
    OUTPUT_DIR
    / "Bank_Pilot_Readiness_Scorecard.csv"
)

PILOT_GAPS_FILE = (
    OUTPUT_DIR
    / "Bank_Pilot_Remaining_Gaps.csv"
)

COMMITTEE_FILE = (
    OUTPUT_DIR
    / "Integrated_Credit_Committee_Register.csv"
)


# =============================================================================
# DESIGN SYSTEM
# =============================================================================

NAVY = "#0B1F33"
NAVY_2 = "#132F4C"
INK = "#111827"
TEXT = "#334155"
MUTED = "#64748B"

BLUE = "#2563EB"
TEAL = "#0F766E"
AMBER = "#D97706"
ORANGE = "#EA580C"
RED = "#DC2626"

BORDER = "#E5E7EB"
GRID = "#EEF2F6"
SURFACE = "#FFFFFF"
BACKGROUND = "#F6F8FB"

RISK_COLORS = {

    "LOW":
        TEAL,

    "MODERATE_LOW":
        BLUE,

    "MODERATE":
        AMBER,

    "ELEVATED":
        ORANGE,

    "HIGH":
        RED,

    "INSUFFICIENT_EVIDENCE":
        "#94A3B8",

    "NOT_OBSERVABLE":
        "#94A3B8",

    "NOT_AVAILABLE":
        "#94A3B8"
}


EWS_COLORS = {

    "GREEN":
        TEAL,

    "AMBER":
        AMBER,

    "RED":
        RED,

    "INSUFFICIENT_EVIDENCE":
        "#94A3B8",

    "NOT_OBSERVABLE":
        "#94A3B8",

    "NOT_AVAILABLE":
        "#94A3B8"
}


CSS = """
<style>

/* -------------------------------------------------------------------------- */
/* GLOBAL */
/* -------------------------------------------------------------------------- */

html, body, [class*="css"] {

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Helvetica Neue",
        Arial,
        sans-serif;
}

.stApp {

    background: #F6F8FB;
}

.block-container {

    max-width: 1540px;

    padding-top: 1.2rem;

    padding-bottom: 4rem;

    padding-left: 2rem;

    padding-right: 2rem;
}


/* -------------------------------------------------------------------------- */
/* TYPOGRAPHY */
/* -------------------------------------------------------------------------- */

h1, h2, h3, h4 {

    color: #111827 !important;

    letter-spacing: -0.025em;
}


.sci-eyebrow {

    color: #2563EB;

    font-size: .70rem;

    font-weight: 760;

    letter-spacing: .12em;

    text-transform: uppercase;

    margin-bottom: .35rem;
}


.sci-title {

    color: #111827;

    font-size: clamp(1.9rem, 3vw, 2.6rem);

    font-weight: 780;

    line-height: 1.06;

    letter-spacing: -.045em;

    margin: 0;
}


.sci-subtitle {

    color: #64748B;

    font-size: .94rem;

    line-height: 1.58;

    max-width: 920px;

    margin-top: .55rem;

    margin-bottom: 1.45rem;
}


/* -------------------------------------------------------------------------- */
/* SIDEBAR */
/* -------------------------------------------------------------------------- */

[data-testid="stSidebar"] {

    background: #0B1F33;

    border-right: 1px solid #173854;
}


[data-testid="stSidebar"] * {

    color: #F8FAFC !important;
}


[data-testid="stSidebar"] hr {

    border-color: rgba(255,255,255,.12) !important;
}


[data-testid="stSidebar"] [role="radiogroup"] label {

    padding: .42rem .50rem;

    border-radius: 8px;
}


[data-testid="stSidebar"] [role="radiogroup"] label:hover {

    background: rgba(255,255,255,.07);
}


/* -------------------------------------------------------------------------- */
/* METRICS */
/* -------------------------------------------------------------------------- */

[data-testid="stMetric"] {

    background: #FFFFFF;

    border: 1px solid #E5E7EB;

    border-radius: 12px;

    padding: .95rem 1rem;

    min-height: 105px;

    box-shadow:
        0 1px 2px rgba(15,23,42,.025);
}


[data-testid="stMetricLabel"] {

    color: #64748B !important;

    font-weight: 650;
}


[data-testid="stMetricValue"] {

    color: #111827 !important;

    font-variant-numeric: tabular-nums;

    letter-spacing: -.03em;
}


/* -------------------------------------------------------------------------- */
/* DATAFRAMES / INPUTS */
/* -------------------------------------------------------------------------- */

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


.stButton > button,

.stDownloadButton > button {

    border-radius: 8px;

    font-weight: 650;
}


div[data-testid="stAlert"] {

    border-radius: 10px;
}


hr {

    border-color: #E5E7EB !important;
}


/* -------------------------------------------------------------------------- */
/* CUSTOM CARDS */
/* -------------------------------------------------------------------------- */

.sci-card {

    background: white;

    border: 1px solid #E5E7EB;

    border-radius: 12px;

    padding: 1rem 1.1rem;

    margin-bottom: .75rem;
}


.sci-card-label {

    color: #64748B;

    font-size: .74rem;

    font-weight: 700;

    text-transform: uppercase;

    letter-spacing: .06em;
}


.sci-card-value {

    color: #111827;

    font-size: 1.05rem;

    font-weight: 700;

    margin-top: .25rem;
}


.sci-note {

    color: #64748B;

    font-size: .82rem;

    line-height: 1.5;
}


/* -------------------------------------------------------------------------- */
/* RESPONSIVE */
/* -------------------------------------------------------------------------- */

@media (max-width: 900px) {

    .block-container {

        padding-left: .9rem;

        padding-right: .9rem;
    }
}

</style>
"""


PLOTLY_CONFIG = {

    "displaylogo":
        False,

    "displayModeBar":
        "hover",

    "responsive":
        True,

    "scrollZoom":
        True,

    "doubleClick":
        "reset",

    "toImageButtonOptions": {

        "format":
            "png",

        "filename":
            "semiconductor_credit_intelligence",

        "height":
            900,

        "width":
            1500,

        "scale":
            2
    }
}


# =============================================================================
# FILE HELPERS
# =============================================================================

@st.cache_data(
    show_spinner=False
)
def read_csv(
    path: str
):

    df = pd.read_csv(
        path
    )

    df.columns = (

        df.columns

        .astype(str)

        .str.replace(
            "\ufeff",
            "",
            regex=False
        )

        .str.strip()
    )

    return df


def optional_csv(
    path: Path
):

    if not path.exists():

        return pd.DataFrame()

    return read_csv(
        str(
            path
        )
    )


def load_master():

    if not MASTER_FILE.exists():

        st.error(
            "Banking dashboard master file is unavailable."
        )

        st.stop()

    return read_csv(
        str(
            MASTER_FILE
        )
    )


# =============================================================================
# DATA HELPERS
# =============================================================================

def num(
    df,
    col
):

    if col not in df.columns:

        return pd.Series(
            np.nan,
            index=df.index
        )

    return pd.to_numeric(
        df[col],
        errors="coerce"
    )


def text(
    df,
    col
):

    if col not in df.columns:

        return pd.Series(
            "",
            index=df.index,
            dtype="object"
        )

    return (

        df[col]

        .fillna("")

        .astype(str)
    )


def fmt(
    value,
    decimals=1
):

    if value is None or pd.isna(value):

        return "—"

    try:

        return (
            f"{float(value):,.{decimals}f}"
        )

    except Exception:

        return str(
            value
        )


def fmt_pct(
    value,
    decimals=1
):

    if value is None or pd.isna(value):

        return "—"

    return (
        f"{float(value):,.{decimals}f}%"
    )


def money(
    value
):

    if value is None or pd.isna(value):

        return "—"

    return (
        f"₹{float(value):,.0f} Cr"
    )


def clean_display(
    value
):

    if value is None or pd.isna(value):

        return "NOT AVAILABLE"

    value = str(
        value
    ).strip()

    if (
        value == ""
        or
        value.lower()
        in {
            "nan",
            "none"
        }
    ):

        return "NOT AVAILABLE"

    return value


# =============================================================================
# UI HELPERS
# =============================================================================

def header(
    title,
    subtitle
):

    st.markdown(

        f"""
        <div class="sci-eyebrow">
        SEMICONDUCTOR CREDIT INTELLIGENCE
        </div>

        <div class="sci-title">
        {title}
        </div>

        <div class="sci-subtitle">
        {subtitle}
        </div>
        """,

        unsafe_allow_html=True
    )


def style_fig(
    fig,
    height=390
):

    fig.update_layout(

        height=height,

        paper_bgcolor=SURFACE,

        plot_bgcolor=SURFACE,

        font=dict(

            family=(
                '-apple-system, BlinkMacSystemFont, '
                '"Segoe UI", Arial, sans-serif'
            ),

            color=INK,

            size=12
        ),

        margin=dict(
            l=25,
            r=20,
            t=35,
            b=40
        ),

        hoverlabel=dict(

            bgcolor="#FFFFFF",

            bordercolor=BORDER,

            font_color=INK
        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.02,

            xanchor="left",

            x=0
        ),

        xaxis=dict(

            showgrid=False,

            zeroline=False,

            linecolor=BORDER,

            automargin=True
        ),

        yaxis=dict(

            showgrid=True,

            gridcolor=GRID,

            zeroline=False,

            automargin=True
        ),

        hovermode="closest",

        dragmode="pan",

        uirevision="sci-banking-v2"
    )

    return fig


def chart(
    fig,
    key,
    height=390
):

    style_fig(
        fig,
        height
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        theme=None,

        config=PLOTLY_CONFIG,

        key=key
    )


def card(
    label,
    value,
    note=None
):

    note_html = (

        f'<div class="sci-note">{note}</div>'

        if note

        else ""
    )

    st.markdown(

        f"""
        <div class="sci-card">

            <div class="sci-card-label">
                {label}
            </div>

            <div class="sci-card-value">
                {value}
            </div>

            {note_html}

        </div>
        """,

        unsafe_allow_html=True
    )


# =============================================================================
# SIDEBAR
# =============================================================================

def sidebar(
    master
):

    with st.sidebar:

        st.markdown(
            "## Semiconductor Credit Intelligence"
        )

        st.caption(
            "Institutional credit-risk decision support"
        )


        page = st.radio(

            "Navigation",

            [

                "Portfolio Overview",

                "Credit Committee",

                "Project Dossier",

                "Borrower Financials",

                "Project Finance",

                "Execution Risk",

                "Stress & Tail Risk",

                "Security & Recovery",

                "Early Warning System",

                "Evidence & Data Gaps",

                "Portfolio Allocation",

                "Governance"

            ],

            label_visibility="collapsed"
        )


        st.divider()


        st.markdown(
            "#### Portfolio filters"
        )


        states = []

        if "state" in master.columns:

            states = st.multiselect(

                "State",

                sorted(

                    text(
                        master,
                        "state"
                    )

                    .replace(
                        "",
                        pd.NA
                    )

                    .dropna()

                    .unique()

                    .tolist()
                )
            )


        risk_classes = []

        if (
            "integrated_banking_risk_class"
            in master.columns
        ):

            risk_classes = st.multiselect(

                "Integrated risk",

                sorted(

                    text(
                        master,
                        "integrated_banking_risk_class"
                    )

                    .replace(
                        "",
                        pd.NA
                    )

                    .dropna()

                    .unique()

                    .tolist()
                )
            )


        ews_filter = []

        if "final_ews_status" in master.columns:

            ews_filter = st.multiselect(

                "EWS",

                sorted(

                    text(
                        master,
                        "final_ews_status"
                    )

                    .replace(
                        "",
                        pd.NA
                    )

                    .dropna()

                    .unique()

                    .tolist()
                )
            )


        company_search = st.text_input(

            "Company search",

            placeholder="Search company"
        )


        st.divider()


        st.caption(
            "MODEL STATUS"
        )

        st.caption(
            "Research / controlled pilot"
        )

        st.caption(
            "Human credit review mandatory"
        )

        st.caption(
            "No automated lending decision"
        )


    filtered = master.copy()


    if states:

        filtered = filtered[
            filtered[
                "state"
            ].isin(
                states
            )
        ]


    if risk_classes:

        filtered = filtered[

            text(
                filtered,
                "integrated_banking_risk_class"
            )

            .isin(
                risk_classes
            )
        ]


    if ews_filter:

        filtered = filtered[

            text(
                filtered,
                "final_ews_status"
            )

            .isin(
                ews_filter
            )
        ]


    if company_search:

        filtered = filtered[

            text(
                filtered,
                "company"
            )

            .str.contains(
                company_search,
                case=False,
                na=False
            )
        ]


    return page, filtered


# =============================================================================
# PROJECT SELECTOR
# =============================================================================

def project_selector(
    df,
    key
):

    options = (

        df[
            [
                "project_id",
                "company"
            ]
        ]

        .drop_duplicates()

        .copy()
    )


    options[
        "label"
    ] = (

        options[
            "project_id"
        ].astype(str)

        +

        "  |  "

        +

        options[
            "company"
        ].astype(str)
    )


    selected = st.selectbox(

        "Project",

        options[
            "label"
        ].tolist(),

        key=key
    )


    project_id = (

        options.loc[
            options[
                "label"
            ]
            ==
            selected,

            "project_id"
        ]

        .iloc[0]
    )


    return project_id


# =============================================================================
# PORTFOLIO OVERVIEW
# =============================================================================

def page_overview(
    df
):

    header(

        "Portfolio Risk Overview",

        "Integrated institutional view across semiconductor vulnerability, "
        "tail risk, borrower financials, execution, EWS, concentration "
        "and evidence quality."
    )


    risk = num(
        df,
        "integrated_banking_risk_score"
    )

    evidence = num(
        df,
        "integrated_evidence_quality_score"
    )

    ews = text(
        df,
        "final_ews_status"
    ).str.upper()


    c1, c2, c3, c4, c5 = st.columns(
        5
    )


    c1.metric(
        "Projects",
        len(
            df
        )
    )


    c2.metric(

        "Avg integrated risk",

        (
            fmt(
                risk.mean()
            )

            if risk.notna().any()

            else "—"
        )
    )


    c3.metric(

        "RED EWS",

        int(
            ews.eq(
                "RED"
            ).sum()
        )
    )


    c4.metric(

        "Immediate review",

        int(

            text(
                df,
                "committee_monitoring_tier"
            )

            .eq(
                "TIER_1_IMMEDIATE_REVIEW"
            )

            .sum()
        )
    )


    c5.metric(

        "Avg evidence quality",

        (
            fmt_pct(
                evidence.mean()
            )

            if evidence.notna().any()

            else "—"
        )
    )


    st.caption(
        "Integrated risk is a research decision-support score. "
        "It is not Probability of Default."
    )


    left, right = st.columns(
        [
            0.9,
            1.25
        ]
    )


    with left:

        st.subheader(
            "Risk classification"
        )


        counts = (

            text(
                df,
                "integrated_banking_risk_class"
            )

            .replace(
                "",
                "NOT_AVAILABLE"
            )

            .value_counts()

            .reset_index()
        )


        counts.columns = [
            "Risk",
            "Projects"
        ]


        fig = px.bar(

            counts,

            x="Risk",

            y="Projects",

            color="Risk",

            color_discrete_map=RISK_COLORS,

            text="Projects"
        )


        fig.update_traces(
            textposition="outside"
        )


        fig.update_layout(
            showlegend=False
        )


        chart(
            fig,
            "overview_risk_distribution",
            350
        )


    with right:

        st.subheader(
            "Risk versus evidence quality"
        )


        plot = df.copy()


        plot[
            "Integrated Risk"
        ] = num(
            plot,
            "integrated_banking_risk_score"
        )


        plot[
            "Evidence Quality"
        ] = num(
            plot,
            "integrated_evidence_quality_score"
        )


        plot[
            "EWS"
        ] = (

            text(
                plot,
                "final_ews_status"
            )

            .str.upper()

            .replace(
                "",
                "NOT_AVAILABLE"
            )
        )


        plot[
            "Project Scale"
        ] = (

            num(
                plot,
                "investment_crore"
            )

            .fillna(
                0
            )

            .clip(
                lower=0
            )
        )


        plot = plot.dropna(

            subset=[

                "Integrated Risk",

                "Evidence Quality"
            ]
        )


        size_col = (

            "Project Scale"

            if plot[
                "Project Scale"
            ].gt(
                0
            ).any()

            else None
        )


        fig = px.scatter(

            plot,

            x="Evidence Quality",

            y="Integrated Risk",

            color="EWS",

            size=size_col,

            hover_name="company",

            hover_data={

                c: True

                for c in [

                    "project_id",

                    "state",

                    "project_type",

                    "integrated_banking_risk_class",

                    "committee_monitoring_tier"

                ]

                if c in plot.columns
            },

            color_discrete_map=EWS_COLORS,

            size_max=48
        )


        fig.update_traces(

            marker=dict(

                line=dict(
                    width=1,
                    color="#FFFFFF"
                ),

                opacity=.88
            )
        )


        fig.update_xaxes(
            title="Evidence quality (%)"
        )


        fig.update_yaxes(
            title="Integrated banking risk"
        )


        chart(
            fig,
            "overview_risk_evidence",
            350
        )


    st.subheader(
        "Risk ranking"
    )


    rank = df.copy()


    rank[
        "Risk"
    ] = num(
        rank,
        "integrated_banking_risk_score"
    )


    rank[
        "Risk Class"
    ] = text(
        rank,
        "integrated_banking_risk_class"
    )


    rank = (

        rank

        .dropna(
            subset=[
                "Risk"
            ]
        )

        .sort_values(
            "Risk",
            ascending=True
        )
    )


    fig = px.bar(

        rank,

        x="Risk",

        y="company",

        orientation="h",

        color="Risk Class",

        color_discrete_map=RISK_COLORS,

        hover_data=[

            c

            for c in [

                "project_id",

                "state",

                "final_ews_status",

                "integrated_evidence_quality_class",

                "committee_monitoring_tier"

            ]

            if c in rank.columns
        ]
    )


    fig.update_xaxes(
        title="Integrated banking risk score"
    )


    fig.update_yaxes(
        title=""
    )


    chart(

        fig,

        "overview_ranking",

        max(
            420,
            34
            *
            len(
                rank
            )
            +
            100
        )
    )


# =============================================================================
# CREDIT COMMITTEE
# =============================================================================

def page_committee(
    df
):

    header(

        "Credit Committee",

        "Prioritised human-review queue showing risk level, evidence "
        "quality, EWS, monitoring tier and critical escalation flags."
    )


    tier = text(
        df,
        "committee_monitoring_tier"
    )


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Immediate review",

        int(
            tier.eq(
                "TIER_1_IMMEDIATE_REVIEW"
            ).sum()
        )
    )


    c2.metric(

        "Enhanced monitoring",

        int(
            tier.eq(
                "TIER_2_ENHANCED_MONITORING"
            ).sum()
        )
    )


    c3.metric(

        "Data verification",

        int(
            tier.eq(
                "TIER_3_DATA_VERIFICATION"
            ).sum()
        )
    )


    c4.metric(

        "Standard monitoring",

        int(
            tier.eq(
                "TIER_4_STANDARD_MONITORING"
            ).sum()
        )
    )


    display = df.copy()


    priority_order = {

        "TIER_1_IMMEDIATE_REVIEW":
            1,

        "TIER_2_ENHANCED_MONITORING":
            2,

        "TIER_3_DATA_VERIFICATION":
            3,

        "TIER_3_STANDARD_REVIEW":
            4,

        "TIER_4_STANDARD_MONITORING":
            5
    }


    display[
        "_priority"
    ] = (

        text(
            display,
            "committee_monitoring_tier"
        )

        .map(
            priority_order
        )

        .fillna(
            99
        )
    )


    display[
        "_risk"
    ] = num(
        display,
        "integrated_banking_risk_score"
    )


    display = display.sort_values(

        [
            "_priority",
            "_risk"
        ],

        ascending=[
            True,
            False
        ],

        na_position="last"
    )


    cols = [

        col

        for col in [

            "project_id",

            "company",

            "state",

            "integrated_banking_risk_score",

            "integrated_banking_risk_class",

            "integrated_evidence_quality_class",

            "final_ews_status",

            "critical_review_flags",

            "committee_monitoring_tier",

            "credit_committee_posture"

        ]

        if col in display.columns
    ]


    st.dataframe(

        display[
            cols
        ],

        use_container_width=True,

        hide_index=True
    )


    st.caption(
        "Committee posture is workflow guidance for human review, "
        "not an automated lending decision."
    )


# =============================================================================
# PROJECT DOSSIER
# =============================================================================

def page_dossier(
    master
):

    header(

        "Project Credit Dossier",

        "Integrated single-project view designed for analyst and "
        "credit-committee review."
    )


    project_id = project_selector(

        master,

        "dossier_project"
    )


    row = (

        master[
            master[
                "project_id"
            ].astype(str)
            ==
            str(
                project_id
            )
        ]

        .iloc[0]
    )


    st.markdown(
        f"## {clean_display(row.get('company'))}"
    )


    st.caption(

        f"{clean_display(row.get('project_id'))} · "
        f"{clean_display(row.get('project_type'))} · "
        f"{clean_display(row.get('state'))}"
    )


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Integrated risk",

        fmt(
            row.get(
                "integrated_banking_risk_score"
            )
        ),

        clean_display(
            row.get(
                "integrated_banking_risk_class"
            )
        )
    )


    c2.metric(

        "EWS",

        clean_display(
            row.get(
                "final_ews_status"
            )
        )
    )


    c3.metric(

        "Evidence quality",

        clean_display(
            row.get(
                "integrated_evidence_quality_class"
            )
        )
    )


    c4.metric(

        "Committee tier",

        clean_display(
            row.get(
                "committee_monitoring_tier"
            )
        )
    )


    tabs = st.tabs(

        [

            "Executive View",

            "Borrower",

            "Project & Execution",

            "Stress",

            "Security",

            "Evidence",

            "Governance"
        ]
    )


    # -------------------------------------------------------------------------
    # EXECUTIVE
    # -------------------------------------------------------------------------

    with tabs[0]:

        st.markdown(
            "### Committee posture"
        )


        st.info(

            clean_display(
                row.get(
                    "credit_committee_posture"
                )
            )
        )


        left, right = st.columns(
            2
        )


        with left:

            card(

                "Project investment",

                money(
                    row.get(
                        "investment_crore"
                    )
                ),

                "Project investment scale; not bank exposure."
            )


            card(

                "Stress vulnerability",

                fmt(
                    row.get(
                        "project_stress_vulnerability_score"
                    )
                ),

                clean_display(
                    row.get(
                        "project_stress_vulnerability_class"
                    )
                )
            )


            card(

                "Borrower financial risk",

                fmt(
                    row.get(
                        "borrower_financial_risk_score"
                    )
                ),

                clean_display(
                    row.get(
                        "borrower_financial_risk_class"
                    )
                )
            )


        with right:

            card(

                "Execution risk",

                fmt(
                    row.get(
                        "execution_risk_score"
                    )
                ),

                clean_display(
                    row.get(
                        "execution_risk_class"
                    )
                )
            )


            card(

                "Monitoring maturity",

                clean_display(
                    row.get(
                        "monitoring_maturity"
                    )
                )
            )


            card(

                "Critical review flags",

                clean_display(
                    row.get(
                        "critical_review_flags"
                    )
                )
            )


        st.markdown(
            "### Model explanation"
        )


        st.write(

            clean_display(

                row.get(
                    "integrated_credit_committee_explanation"
                )
            )
        )


    # -------------------------------------------------------------------------
    # BORROWER
    # -------------------------------------------------------------------------

    with tabs[1]:

        borrower = optional_csv(
            BORROWER_FILE
        )


        if borrower.empty:

            st.warning(
                "Borrower financial evidence unavailable."
            )

        else:

            b = borrower[

                borrower[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ].copy()


            if b.empty:

                st.info(
                    "No borrower financial observation for this project."
                )

            else:

                st.dataframe(

                    b,

                    use_container_width=True,

                    hide_index=True
                )


    # -------------------------------------------------------------------------
    # PROJECT / EXECUTION
    # -------------------------------------------------------------------------

    with tabs[2]:

        execution = optional_csv(
            EXECUTION_FILE
        )


        if execution.empty:

            st.warning(
                "Execution-risk data unavailable."
            )

        else:

            e = execution[

                execution[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ]


            if e.empty:

                st.info(
                    "No execution observation for this project."
                )

            else:

                st.dataframe(

                    e,

                    use_container_width=True,

                    hide_index=True
                )


    # -------------------------------------------------------------------------
    # STRESS
    # -------------------------------------------------------------------------

    with tabs[3]:

        stress = optional_csv(
            STRESS_FILE
        )


        if stress.empty:

            st.warning(
                "Stress panel unavailable."
            )

        else:

            s = stress[

                stress[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ]


            if s.empty:

                st.info(
                    "No stress record available."
                )

            else:

                st.dataframe(

                    s,

                    use_container_width=True,

                    hide_index=True
                )


    # -------------------------------------------------------------------------
    # SECURITY
    # -------------------------------------------------------------------------

    with tabs[4]:

        security = optional_csv(
            SECURITY_FILE
        )


        if security.empty:

            st.warning(
                "Security/recovery evidence unavailable."
            )

        else:

            s = security[

                security[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ]


            if s.empty:

                st.info(
                    "No verified security information available."
                )

            else:

                st.dataframe(

                    s,

                    use_container_width=True,

                    hide_index=True
                )


    # -------------------------------------------------------------------------
    # EVIDENCE
    # -------------------------------------------------------------------------

    with tabs[5]:

        evidence = optional_csv(
            EVIDENCE_FILE
        )


        gaps = optional_csv(
            GAP_FILE
        )


        st.markdown(
            "#### Verified/source-backed evidence"
        )


        if evidence.empty:

            st.info(
                "No evidence ledger."
            )

        else:

            ev = evidence[

                evidence[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ]


            st.dataframe(

                ev,

                use_container_width=True,

                hide_index=True
            )


        st.markdown(
            "#### Banking evidence gaps"
        )


        if gaps.empty:

            st.info(
                "No gap register."
            )

        else:

            gp = gaps[

                gaps[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ]


            if gp.empty:

                st.success(
                    "No registered gaps for this project."
                )

            else:

                st.dataframe(

                    gp,

                    use_container_width=True,

                    hide_index=True
                )


    # -------------------------------------------------------------------------
    # GOVERNANCE
    # -------------------------------------------------------------------------

    with tabs[6]:

        st.warning(
            "Human credit review is mandatory."
        )


        st.markdown(
            """
**This project output is not:**

- a Probability of Default estimate;
- an LGD estimate;
- an EAD estimate;
- an Expected Credit Loss calculation;
- an official bank internal rating;
- an automated approval or rejection.
            """
        )


# =============================================================================
# BORROWER FINANCIALS PAGE
# =============================================================================

def page_borrower(
    master
):

    header(

        "Borrower Financials",

        "Borrower-level profitability, leverage, liquidity and repayment-capacity "
        "signals using only available financial evidence."
    )


    borrower = optional_csv(
        BORROWER_FILE
    )


    if borrower.empty:

        st.warning(
            "Borrower financial dataset is unavailable."
        )

        return


    project_id = project_selector(

        master,

        "borrower_project"
    )


    b = borrower[

        borrower[
            "project_id"
        ].astype(str)
        ==
        str(
            project_id
        )

    ].copy()


    if b.empty:

        st.info(
            "No borrower financial observation available."
        )

        return


    latest = b.iloc[
        -1
    ]


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Financial strength",

        fmt(
            latest.get(
                "borrower_financial_strength_score"
            )
        ),

        clean_display(
            latest.get(
                "borrower_financial_strength_class"
            )
        )
    )


    c2.metric(

        "Debt / Equity",

        fmt(
            latest.get(
                "debt_equity_ratio"
            )
        )
    )


    c3.metric(

        "Debt / EBITDA",

        fmt(
            latest.get(
                "debt_to_ebitda"
            )
        )
    )


    c4.metric(

        "Interest coverage",

        fmt(
            latest.get(
                "interest_coverage_effective"
            )
        )
    )


    metric_map = {

        "EBITDA Margin":
            latest.get(
                "ebitda_margin_pct"
            ),

        "Debt / Equity":
            latest.get(
                "debt_equity_ratio"
            ),

        "Debt / EBITDA":
            latest.get(
                "debt_to_ebitda"
            ),

        "Current Ratio":
            latest.get(
                "current_ratio"
            ),

        "Interest Coverage":
            latest.get(
                "interest_coverage_effective"
            )
    }


    chart_df = pd.DataFrame(

        [

            {
                "Metric":
                    key,

                "Value":
                    value
            }

            for key, value
            in metric_map.items()

            if pd.notna(
                value
            )
        ]
    )


    if not chart_df.empty:

        fig = px.bar(

            chart_df,

            x="Metric",

            y="Value",

            text_auto=".2f"
        )


        fig.update_traces(
            marker_color=BLUE
        )


        chart(
            fig,
            "borrower_metrics",
            360
        )


    st.subheader(
        "Underlying borrower evidence"
    )


    st.dataframe(

        b,

        use_container_width=True,

        hide_index=True
    )


# =============================================================================
# PROJECT FINANCE PAGE
# =============================================================================

def page_project_finance(
    master
):

    header(

        "Project Finance Underwriting",

        "Debt-service, leverage, DCCO and cost-overrun analysis where "
        "transaction-level information has been verified."
    )


    pf = optional_csv(
        PROJECT_FINANCE_FILE
    )


    if pf.empty:

        st.warning(
            "Project-finance underwriting output unavailable."
        )

        return


    project_id = project_selector(

        master,

        "pf_project"
    )


    row = pf[

        pf[
            "project_id"
        ].astype(str)
        ==
        str(
            project_id
        )

    ].copy()


    if row.empty:

        st.info(
            "No project-finance observation available."
        )

        return


    r = row.iloc[
        0
    ]


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Verified DSCR",

        fmt(
            r.get(
                "dscr_verified"
            )
        )
    )


    c2.metric(

        "Verified D/E",

        fmt(
            r.get(
                "debt_equity_ratio_verified"
            )
        )
    )


    c3.metric(

        "DCCO delay",

        (
            f"{fmt(r.get('dcco_delay_days_verified'), 0)} days"

            if pd.notna(
                r.get(
                    "dcco_delay_days_verified"
                )
            )

            else "—"
        )
    )


    c4.metric(

        "Data coverage",

        fmt_pct(
            r.get(
                "underwriting_data_coverage_pct"
            )
        )
    )


    if (
        pd.isna(
            r.get(
                "dscr_verified"
            )
        )
    ):

        st.warning(

            "Verified project-level DSCR is unavailable. "
            "No DSCR has been inferred from project investment "
            "or borrower-level facilities."
        )


    st.dataframe(

        row,

        use_container_width=True,

        hide_index=True
    )


# =============================================================================
# EXECUTION PAGE
# =============================================================================

def page_execution(
    master
):

    header(

        "Execution & Implementation Risk",

        "Project implementation status, commissioning timing, DCCO, "
        "completion and cost-overrun monitoring."
    )


    execution = optional_csv(
        EXECUTION_FILE
    )


    if execution.empty:

        st.warning(
            "Execution-risk output unavailable."
        )

        return


    project_id = project_selector(

        master,

        "execution_project"
    )


    e = execution[

        execution[
            "project_id"
        ].astype(str)
        ==
        str(
            project_id
        )

    ].copy()


    if e.empty:

        st.info(
            "No execution data available."
        )

        return


    r = e.iloc[
        0
    ]


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Execution risk",

        fmt(
            r.get(
                "execution_risk_score"
            )
        ),

        clean_display(
            r.get(
                "execution_risk_class"
            )
        )
    )


    c2.metric(

        "Completion",

        fmt_pct(
            r.get(
                "project_completion_pct"
            )
        )
    )


    c3.metric(

        "DCCO delay",

        (
            f"{fmt(r.get('dcco_delay_days'), 0)} days"

            if pd.notna(
                r.get(
                    "dcco_delay_days"
                )
            )

            else "—"
        )
    )


    c4.metric(

        "Cost overrun",

        fmt_pct(
            r.get(
                "cost_overrun_pct"
            )
        )
    )


    st.dataframe(

        e,

        use_container_width=True,

        hide_index=True
    )


# =============================================================================
# STRESS & MC PAGE
# =============================================================================

def page_stress():

    header(

        "Stress & Tail Risk",

        "Comparison of deterministic stress vulnerability with Monte Carlo "
        "tail-risk behaviour."
    )


    risk = optional_csv(
        STRESS_FILE
    )


    if risk.empty:

        st.warning(
            "Stress/Monte Carlo panel unavailable."
        )

        return


    risk[
        "Stress"
    ] = num(
        risk,
        "project_stress_vulnerability_score"
    )


    risk[
        "P95"
    ] = num(
        risk,
        "p95_score"
    )


    plot = risk.dropna(

        subset=[
            "Stress",
            "P95"
        ]
    )


    if not plot.empty:

        fig = px.scatter(

            plot,

            x="Stress",

            y="P95",

            hover_name="company",

            hover_data=[

                c

                for c in [

                    "project_id",

                    "p99_score",

                    "tail_risk_rank",

                    "probability_top_3"

                ]

                if c in plot.columns
            ]
        )


        fig.update_traces(

            marker=dict(

                size=13,

                color=BLUE,

                opacity=.82,

                line=dict(

                    width=1,

                    color="#FFFFFF"
                )
            )
        )


        fig.update_xaxes(
            title="Deterministic stress vulnerability"
        )


        fig.update_yaxes(
            title="Monte Carlo P95 stress"
        )


        chart(
            fig,
            "stress_mc_scatter",
            430
        )


    ranking = risk.dropna(
        subset=[
            "P95"
        ]
    ).sort_values(
        "P95"
    )


    if not ranking.empty:

        fig = px.bar(

            ranking,

            x="P95",

            y="company",

            orientation="h"
        )


        fig.update_traces(
            marker_color=BLUE
        )


        fig.update_xaxes(
            title="P95 simulated stress"
        )


        fig.update_yaxes(
            title=""
        )


        chart(

            fig,

            "stress_mc_rank",

            max(
                400,
                len(
                    ranking
                )
                *
                33
                +
                100
            )
        )


    st.caption(
        "Stress scores are constructed/modelled vulnerability indicators, "
        "not observed losses or default probabilities."
    )


# =============================================================================
# SECURITY PAGE
# =============================================================================

def page_security(
    master
):

    header(

        "Security & Recovery",

        "Collateral, guarantees, enforceability and recovery-support evidence "
        "where transaction-level information is available."
    )


    security = optional_csv(
        SECURITY_FILE
    )


    if security.empty:

        st.warning(
            "Security/recovery output unavailable."
        )

        return


    project_id = project_selector(

        master,

        "security_project"
    )


    s = security[

        security[
            "project_id"
        ].astype(str)
        ==
        str(
            project_id
        )

    ].copy()


    if s.empty:

        st.info(
            "No security observation available."
        )

        return


    r = s.iloc[
        0
    ]


    c1, c2, c3 = st.columns(
        3
    )


    c1.metric(

        "Security analysis",

        clean_display(
            r.get(
                "security_analysis_status"
            )
        )
    )


    c2.metric(

        "Security coverage",

        fmt(
            r.get(
                "project_security_coverage_ratio"
            )
        )
    )


    c3.metric(

        "Recovery coverage",

        fmt(
            r.get(
                "project_recovery_coverage_ratio"
            )
        )
    )


    if (
        clean_display(
            r.get(
                "security_analysis_status"
            )
        )
        !=
        "SECURITY_ANALYSIS_AVAILABLE"
    ):

        st.warning(
            "Coverage analysis remains unavailable until verified "
            "project exposure and security evidence exist."
        )


    st.dataframe(

        s,

        use_container_width=True,

        hide_index=True
    )


# =============================================================================
# EWS PAGE
# =============================================================================

def page_ews(
    master
):

    header(

        "Early Warning System",

        "Current cross-sectional monitoring signals with explicit distinction "
        "between snapshot-only cases and genuine longitudinal histories."
    )


    ews = optional_csv(
        EWS_FILE
    )


    if ews.empty:

        st.warning(
            "EWS output unavailable."
        )

        return


    project_id = project_selector(

        master,

        "ews_project"
    )


    e = ews[

        ews[
            "project_id"
        ].astype(str)
        ==
        str(
            project_id
        )

    ].copy()


    if e.empty:

        st.info(
            "No EWS observation available."
        )

        return


    r = e.iloc[
        0
    ]


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(

        "Final EWS",

        clean_display(
            r.get(
                "final_ews_status"
            )
        )
    )


    c2.metric(

        "Snapshot score",

        fmt(
            r.get(
                "ews_current_snapshot_score"
            )
        )
    )


    c3.metric(

        "Monitoring maturity",

        clean_display(
            r.get(
                "monitoring_maturity"
            )
        )
    )


    c4.metric(

        "Verified observations",

        fmt(
            r.get(
                "verified_monitoring_observations"
            ),
            0
        )
    )


    if (
        clean_display(
            r.get(
                "monitoring_maturity"
            )
        )
        ==
        "SNAPSHOT_ONLY"
    ):

        st.warning(

            "This is a cross-sectional EWS snapshot. "
            "No observed longitudinal deterioration trend is being claimed."
        )


    st.dataframe(

        e,

        use_container_width=True,

        hide_index=True
    )


# =============================================================================
# EVIDENCE PAGE
# =============================================================================

def page_evidence(
    master
):

    header(

        "Evidence & Data Gaps",

        "Audit-oriented view of verified evidence, source provenance "
        "and information still required for bank-grade underwriting."
    )


    project_id = project_selector(

        master,

        "evidence_project"
    )


    evidence = optional_csv(
        EVIDENCE_FILE
    )


    gaps = optional_csv(
        GAP_FILE
    )


    tab1, tab2 = st.tabs(

        [
            "Evidence ledger",
            "Missing banking information"
        ]
    )


    with tab1:

        if evidence.empty:

            st.info(
                "Evidence ledger unavailable."
            )

        else:

            ev = evidence[

                evidence[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ].copy()


            if ev.empty:

                st.info(
                    "No field-level evidence available."
                )

            else:

                st.dataframe(

                    ev,

                    use_container_width=True,

                    hide_index=True
                )


    with tab2:

        if gaps.empty:

            st.info(
                "Banking gap register unavailable."
            )

        else:

            gp = gaps[

                gaps[
                    "project_id"
                ].astype(str)
                ==
                str(
                    project_id
                )

            ].copy()


            if gp.empty:

                st.success(
                    "No registered gaps."
                )

            else:

                st.dataframe(

                    gp,

                    use_container_width=True,

                    hide_index=True
                )


# =============================================================================
# ALLOCATION PAGE
# =============================================================================

def page_allocation():

    header(

        "Portfolio Allocation",

        "Scenario-robust allocation ranking and portfolio concentration context."
    )


    allocation = optional_csv(
        ALLOCATION_FILE
    )


    if allocation.empty:

        st.warning(
            "Allocation robustness output unavailable."
        )

        return


    if {
        "company",
        "mean_allocation_share"
    }.issubset(
        allocation.columns
    ):

        allocation[
            "Mean Allocation"
        ] = num(
            allocation,
            "mean_allocation_share"
        )


        plot = (

            allocation

            .dropna(
                subset=[
                    "Mean Allocation"
                ]
            )

            .sort_values(
                "Mean Allocation"
            )
        )


        fig = px.bar(

            plot,

            x="Mean Allocation",

            y="company",

            orientation="h",

            hover_data=[

                c

                for c in [

                    "robust_allocation_rank",

                    "best_allocation_rank",

                    "worst_allocation_rank",

                    "allocation_stability"

                ]

                if c in plot.columns
            ]
        )


        fig.update_traces(
            marker_color=TEAL
        )


        fig.update_yaxes(
            title=""
        )


        fig.update_xaxes(
            title="Mean allocation share"
        )


        chart(

            fig,

            "allocation_robustness",

            max(
                400,
                33
                *
                len(
                    plot
                )
                +
                100
            )
        )


    st.caption(
        "Allocation share is an analytical portfolio result, "
        "not actual sanctioned lending exposure."
    )


# =============================================================================
# GOVERNANCE PAGE
# =============================================================================

def page_governance():

    header(

        "Governance & Pilot Readiness",

        "Control framework, model limitations and outstanding requirements "
        "before institutional validation or deployment."
    )


    readiness = optional_csv(
        READINESS_FILE
    )


    gaps = optional_csv(
        PILOT_GAPS_FILE
    )


    st.warning(

        "The system is research / controlled-pilot decision support. "
        "Production readiness is not inferred from successful model execution."
    )


    if not readiness.empty:

        st.subheader(
            "Readiness scorecard"
        )


        if {
            "dimension",
            "score_5"
        }.issubset(
            readiness.columns
        ):

            plot = readiness.copy()


            plot[
                "Score"
            ] = num(
                plot,
                "score_5"
            )


            fig = px.bar(

                plot,

                x="Score",

                y="dimension",

                orientation="h",

                text_auto=".2f"
            )


            fig.update_traces(
                marker_color=BLUE
            )


            fig.update_xaxes(

                title="Readiness score / 5",

                range=[
                    0,
                    5
                ]
            )


            fig.update_yaxes(
                title=""
            )


            chart(
                fig,
                "governance_readiness",
                380
            )


        st.dataframe(

            readiness,

            use_container_width=True,

            hide_index=True
        )


    st.subheader(
        "Core governance restrictions"
    )


    st.markdown(
        """
- **No PD:** integrated scores must not be interpreted as Probability of Default.
- **No LGD:** recovery analysis is not regulatory Loss Given Default.
- **No EAD:** project investment is not bank exposure.
- **No ECL:** the framework does not calculate Expected Credit Loss.
- **No automatic approval or rejection.**
- **No official bank/CRA rating claim.**
- Missing project-finance information remains unavailable.
- Borrower-level facilities are not automatically project-specific debt.
- Longitudinal deterioration requires repeated verified observations.
- Human credit-committee review remains mandatory.
        """
    )


    if not gaps.empty:

        st.subheader(
            "Remaining pilot gaps"
        )


        st.dataframe(

            gaps,

            use_container_width=True,

            hide_index=True
        )


# =============================================================================
# APPLICATION
# =============================================================================

def render_app():

    st.markdown(
        CSS,
        unsafe_allow_html=True
    )


    master = load_master()


    page, filtered = sidebar(
        master
    )


    if filtered.empty:

        st.warning(
            "No projects match the current filters."
        )

        return


    if page == "Portfolio Overview":

        page_overview(
            filtered
        )


    elif page == "Credit Committee":

        page_committee(
            filtered
        )


    elif page == "Project Dossier":

        page_dossier(
            filtered
        )


    elif page == "Borrower Financials":

        page_borrower(
            filtered
        )


    elif page == "Project Finance":

        page_project_finance(
            filtered
        )


    elif page == "Execution Risk":

        page_execution(
            filtered
        )


    elif page == "Stress & Tail Risk":

        page_stress()


    elif page == "Security & Recovery":

        page_security(
            filtered
        )


    elif page == "Early Warning System":

        page_ews(
            filtered
        )


    elif page == "Evidence & Data Gaps":

        page_evidence(
            filtered
        )


    elif page == "Portfolio Allocation":

        page_allocation()


    elif page == "Governance":

        page_governance()
