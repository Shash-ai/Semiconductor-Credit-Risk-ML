"""
Semiconductor Credit Intelligence
=================================

Front-end information architecture for the research /
bank-pilot decision-support system.

All data is loaded from existing project outputs.

No model score is recalculated here.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from app.design_system import (
    CHART_CONFIG,
    badge,
    hero,
    initialize_design,
    kpi,
    polish_chart,
    section
)


# =============================================================================
# PROJECT ROOT
# =============================================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


# =============================================================================
# FILE CANDIDATES
# =============================================================================

BANK_MODEL_CANDIDATES = [

    PROJECT_ROOT
    / "05_Final_Results"
    / "FINAL_BANK_CREDIT_FRAMEWORK"
    / "FINAL_Bank_Credit_Decision_Support_Full.csv",

    PROJECT_ROOT
    / "05_Final_Results"
    / "Phase_7A_Bank_Credit_Decision_Support"
    / "Bank_Credit_Decision_Support_Full.csv",

]


COMMITTEE_CANDIDATES = [

    PROJECT_ROOT
    / "05_Final_Results"
    / "Phase_7D_Bank_Credit_Committee_Report"
    / "Final_Bank_Credit_Committee_Register.csv"
]


STRESS_CANDIDATES = [

    PROJECT_ROOT
    / "03_Modeling"
    / "Phase_3E_Robust_Stress_Test"
    / "Robust_Stress_Test_Full.csv",

    PROJECT_ROOT
    / "03_Modeling"
    / "Phase_3E_Robust_Stress_Test"
    / "Final_Robust_Vulnerability_Ranking.csv"
]


MONTE_CARLO_CANDIDATES = [

    PROJECT_ROOT
    / "03_Modeling"
    / "Phase_6B_Monte_Carlo_Stress"
    / "Monte_Carlo_Project_Risk_Summary.csv"
]


ALLOCATION_CANDIDATES = [

    PROJECT_ROOT
    / "05_Final_Results"
    / "Final_Project_Allocation_Robustness.csv",

    PROJECT_ROOT
    / "05_Final_Results"
    / "FINAL_PROJECT_FREEZE"
    / "Final_Project_Allocation_Robustness.csv"
]


# =============================================================================
# DATA UTILITIES
# =============================================================================

def first_existing(
    candidates
):

    for path in candidates:

        if path.exists():
            return path

    return None


@st.cache_data(
    show_spinner=False
)
def load_csv(
    path_string
):

    df = pd.read_csv(
        path_string
    )

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    return df


def load_first(
    candidates
):

    path = first_existing(
        candidates
    )

    if path is None:

        return None, None

    return (
        load_csv(
            str(path)
        ),
        path
    )


# =============================================================================
# COLUMN DISCOVERY
# =============================================================================

def normalize_name(
    value
):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower()
    )


def find_col(
    df,
    candidates
):

    if df is None:
        return None

    lookup = {

        normalize_name(col):
            col

        for col
        in df.columns
    }


    for candidate in candidates:

        key = normalize_name(
            candidate
        )

        if key in lookup:

            return lookup[key]


    return None


# =============================================================================
# STANDARD COLUMN DETECTION
# =============================================================================

def detect_columns(
    df
):

    return {

        "id":
            find_col(
                df,
                [
                    "project_id",
                    "source_project_id",
                    "ecosystem_id"
                ]
            ),

        "company":
            find_col(
                df,
                [
                    "company",
                    "company_name"
                ]
            ),

        "project":
            find_col(
                df,
                [
                    "project_name",
                    "project"
                ]
            ),

        "state":
            find_col(
                df,
                [
                    "state",
                    "project_state"
                ]
            ),

        "grade":
            find_col(
                df,
                [
                    "indicative_grade",
                    "indicative_internal_risk_grade",
                    "research_grade",
                    "risk_grade"
                ]
            ),

        "ews":
            find_col(
                df,
                [
                    "early_warning_status",
                    "ews_status",
                    "early_warning"
                ]
            ),

        "stress":
            find_col(
                df,
                [
                    "project_stress_vulnerability_score",
                    "project_stress_score",
                    "stress_vulnerability_score",
                    "severe_score",
                    "enhanced_score"
                ]
            ),

        "rank":
            find_col(
                df,
                [
                    "enhanced_rank",
                    "vulnerability_rank",
                    "final_rank",
                    "rank"
                ]
            ),

        "p95":
            find_col(
                df,
                [
                    "p95_score",
                    "p95_tail_risk_score",
                    "monte_carlo_p95",
                    "mc_p95",
                    "tail_risk_score"
                ]
            ),

        "amount":
            find_col(
                df,
                [
                    "financial_measure_crore",
                    "investment_crore",
                    "project_outlay_crore",
                    "allocated_credit_crore",
                    "allocation_crore"
                ]
            ),

        "credit_posture":
            find_col(
                df,
                [
                    "credit_posture",
                    "credit_review_posture"
                ]
            ),

        "exposure_posture":
            find_col(
                df,
                [
                    "exposure_posture"
                ]
            ),

        "monitoring":
            find_col(
                df,
                [
                    "monitoring_priority",
                    "monitoring_status"
                ]
            ),

        "drivers":
            find_col(
                df,
                [
                    "primary_risk_drivers",
                    "risk_drivers"
                ]
            ),

        "mitigants":
            find_col(
                df,
                [
                    "primary_risk_mitigants",
                    "risk_mitigants",
                    "mitigants"
                ]
            ),

        "borrower_strength":
            find_col(
                df,
                [
                    "borrower_credit_strength",
                    "borrower_strength"
                ]
            ),

        "concentration":
            find_col(
                df,
                [
                    "portfolio_concentration_signal",
                    "concentration_score",
                    "portfolio_concentration"
                ]
            )
    }


# =============================================================================
# FORMATTING
# =============================================================================

def clean_text(
    value
):

    if pd.isna(value):
        return "Not available"

    return str(value)


def compact_number(
    value
):

    try:

        value = float(value)

    except Exception:

        return "—"


    if abs(value) >= 100000:

        return (
            f"{value/100000:.1f}L"
        )


    if abs(value) >= 1000:

        return (
            f"{value/1000:.1f}K"
        )


    if float(value).is_integer():

        return (
            f"{int(value):,}"
        )


    return (
        f"{value:,.1f}"
    )


def numeric_series(
    df,
    column
):

    if (
        df is None
        or column is None
    ):

        return pd.Series(
            dtype=float
        )


    return pd.to_numeric(
        df[column],
        errors="coerce"
    )


# =============================================================================
# PLOTLY
# =============================================================================

def show_chart(
    fig,
    height=390
):

    polish_chart(
        fig,
        height=height
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=CHART_CONFIG
    )


# =============================================================================
# SIDEBAR
# =============================================================================

def sidebar():

    with st.sidebar:

        st.markdown(
            """
            <div style="
                font-size:0.68rem;
                letter-spacing:0.12em;
                font-weight:760;
                opacity:0.72;
                margin-top:0.3rem;
            ">
                CREDIT ANALYTICS
            </div>

            <div style="
                font-size:1.12rem;
                font-weight:730;
                margin-top:0.35rem;
                margin-bottom:1rem;
            ">
                Semiconductor
                Intelligence
            </div>
            """,
            unsafe_allow_html=True
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

                "Model Validation"
            ],

            label_visibility=
                "collapsed"
        )


        st.divider()


        st.caption(
            "Research / bank-pilot prototype"
        )

        st.caption(
            "Human credit judgement required"
        )


    return page


# =============================================================================
# LOAD CORE MODEL
# =============================================================================

def load_core():

    bank,
    path = load_first(
        BANK_MODEL_CANDIDATES
    )

    if bank is None:

        st.error(
            "Bank decision-support output "
            "could not be located."
        )

        st.stop()


    return (
        bank,
        path,
        detect_columns(
            bank
        )
    )


# =============================================================================
# OVERVIEW
# =============================================================================

def render_overview(
    bank,
    cols
):

    hero(

        "Portfolio Risk Overview",

        (
            "Executive view of semiconductor "
            "project vulnerability, monitoring "
            "signals and concentration indicators."
        )
    )


    projects = len(
        bank
    )


    red_count = 0

    if cols["ews"]:

        red_count = int(
            bank[
                cols["ews"]
            ]
            .astype(str)
            .str.upper()
            .eq("RED")
            .sum()
        )


    priority_count = 0

    if cols["monitoring"]:

        priority_count = int(
            bank[
                cols["monitoring"]
            ]
            .astype(str)
            .str.upper()
            .str.contains(
                "HIGH|PRIORITY|SENIOR",
                regex=True
            )
            .sum()
        )

    elif cols["ews"]:

        priority_count = red_count


    amount_total = None

    if cols["amount"]:

        amount_total = (
            numeric_series(
                bank,
                cols["amount"]
            ).sum()
        )


    c1,
    c2,
    c3,
    c4 = st.columns(4)


    with c1:

        kpi(
            "Projects analyzed",
            f"{projects}",
            "Current bank decision-support universe"
        )


    with c2:

        kpi(

            "Analyzed financial scale",

            (
                "₹"
                + compact_number(
                    amount_total
                )
                + " Cr"
                if amount_total
                else "—"
            ),

            "Project/investment scale, not bank EAD"
        )


    with c3:

        kpi(
            "Red EWS",
            str(
                red_count
            ),
            "Priority monitoring signals"
        )


    with c4:

        kpi(
            "Priority reviews",
            str(
                priority_count
            ),
            "Cases requiring closer analyst attention"
        )


    st.write("")


    # -------------------------------------------------------------------------
    # ROW 1
    # -------------------------------------------------------------------------

    left,
    right = st.columns(
        [1.2, 0.8]
    )


    with left:

        section(
            "Risk-grade distribution",
            (
                "Indicative research grades — "
                "not official bank ratings."
            )
        )


        if cols["grade"]:

            grade_counts = (

                bank[
                    cols["grade"]
                ]
                .fillna(
                    "Not available"
                )
                .astype(str)
                .value_counts()
                .rename_axis(
                    "Grade"
                )
                .reset_index(
                    name="Projects"
                )
            )


            fig = px.bar(

                grade_counts,

                x=
                    "Grade",

                y=
                    "Projects",

                text=
                    "Projects"
            )


            fig.update_traces(

                textposition=
                    "outside",

                hovertemplate=
                    "Grade %{x}<br>"
                    "%{y} projects"
                    "<extra></extra>"
            )


            show_chart(
                fig,
                height=360
            )

        else:

            st.info(
                "Grade field is unavailable."
            )


    with right:

        section(
            "Early-warning profile",
            "Current monitoring distribution."
        )


        if cols["ews"]:

            ews_counts = (

                bank[
                    cols["ews"]
                ]
                .fillna(
                    "Not available"
                )
                .astype(str)
                .value_counts()
                .rename_axis(
                    "Status"
                )
                .reset_index(
                    name="Projects"
                )
            )


            fig = px.pie(

                ews_counts,

                names=
                    "Status",

                values=
                    "Projects",

                hole=
                    0.63
            )


            fig.update_layout(
                showlegend=True
            )


            show_chart(
                fig,
                height=360
            )

        else:

            st.info(
                "EWS field is unavailable."
            )


    # -------------------------------------------------------------------------
    # RISK RANKING
    # -------------------------------------------------------------------------

    section(
        "Priority project view",
        (
            "Relative analytical vulnerability. "
            "Scores are not probabilities of default."
        )
    )


    ranking_col = (
        cols["stress"]
        or cols["rank"]
    )


    if ranking_col:

        company_col = (
            cols["company"]
            or cols["project"]
            or cols["id"]
        )


        if company_col:

            ranking = bank[
                [
                    company_col,
                    ranking_col
                ]
            ].copy()


            ranking[
                ranking_col
            ] = pd.to_numeric(

                ranking[
                    ranking_col
                ],

                errors="coerce"
            )


            ranking = (

                ranking
                .dropna(
                    subset=[
                        ranking_col
                    ]
                )
                .sort_values(
                    ranking_col,
                    ascending=False
                )
                .head(12)
            )


            fig = px.bar(

                ranking,

                x=
                    ranking_col,

                y=
                    company_col,

                orientation=
                    "h"
            )


            fig.update_layout(

                yaxis=dict(
                    autorange="reversed"
                )
            )


            fig.update_traces(

                hovertemplate=
                    "%{y}<br>"
                    "%{x:.2f}"
                    "<extra></extra>"
            )


            show_chart(
                fig,
                height=470
            )


    # -------------------------------------------------------------------------
    # STATE SCALE
    # -------------------------------------------------------------------------

    if (
        cols["state"]
        and cols["amount"]
    ):

        section(
            "Geographic concentration",
            (
                "Financial project scale by state; "
                "not actual bank exposure."
            )
        )


        temp = bank[
            [
                cols["state"],
                cols["amount"]
            ]
        ].copy()


        temp[
            cols["amount"]
        ] = pd.to_numeric(

            temp[
                cols["amount"]
            ],

            errors="coerce"
        )


        state_scale = (

            temp
            .groupby(
                cols["state"],
                dropna=False
            )[
                cols["amount"]
            ]
            .sum()
            .sort_values(
                ascending=False
            )
            .reset_index()
        )


        fig = px.bar(

            state_scale,

            x=
                cols["amount"],

            y=
                cols["state"],

            orientation=
                "h"
        )


        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            )
        )


        show_chart(
            fig,
            height=390
        )


# =============================================================================
# CREDIT COMMITTEE
# =============================================================================

def render_credit_committee(
    bank,
    cols
):

    hero(

        "Credit Committee",

        (
            "Prioritized view of exposures requiring "
            "enhanced review, mitigants or monitoring."
        )
    )


    review = bank.copy()


    # Priority sort
    if cols["ews"]:

        order = {
            "RED": 0,
            "AMBER": 1,
            "GREEN": 2
        }


        review[
            "_ews_priority"
        ] = (

            review[
                cols["ews"]
            ]
            .astype(str)
            .str.upper()
            .map(
                order
            )
            .fillna(
                3
            )
        )


        review = review.sort_values(
            "_ews_priority"
        )


    display_candidates = [

        cols["id"],

        cols["company"],

        cols["project"],

        cols["state"],

        cols["grade"],

        cols["ews"],

        cols["credit_posture"],

        cols["exposure_posture"],

        cols["monitoring"],

        cols["stress"]
    ]


    display_cols = [

        col
        for col in display_candidates
        if col is not None
    ]


    # Deduplicate
    display_cols = list(
        dict.fromkeys(
            display_cols
        )
    )


    section(
        "Committee review register",
        "Sorted toward higher monitoring priority where available."
    )


    st.dataframe(

        review[
            display_cols
        ],

        use_container_width=True,

        hide_index=True,

        height=480
    )


    # Posture
    if cols["credit_posture"]:

        section(
            "Credit-review posture"
        )


        posture_counts = (

            bank[
                cols["credit_posture"]
            ]
            .fillna(
                "Not available"
            )
            .astype(str)
            .value_counts()
            .rename_axis(
                "Posture"
            )
            .reset_index(
                name="Projects"
            )
        )


        fig = px.bar(

            posture_counts,

            x=
                "Projects",

            y=
                "Posture",

            orientation=
                "h"
        )


        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            )
        )


        show_chart(
            fig,
            height=420
        )


# =============================================================================
# PROJECT ANALYSIS
# =============================================================================

def render_project_analysis(
    bank,
    cols
):

    hero(

        "Project Analysis",

        (
            "Drill down into one project using "
            "borrower, stress, concentration and "
            "monitoring evidence."
        )
    )


    label_col = (
        cols["company"]
        or cols["project"]
        or cols["id"]
    )


    if label_col is None:

        st.error(
            "No suitable project identifier found."
        )

        return


    labels = (
        bank[
            label_col
        ]
        .fillna(
            "Unknown"
        )
        .astype(str)
    )


    selected = st.selectbox(

        "Select project / company",

        labels.tolist()
    )


    matching = bank[
        labels == selected
    ]


    if matching.empty:

        return


    row = matching.iloc[0]


    c1,
    c2,
    c3,
    c4 = st.columns(4)


    with c1:

        kpi(
            "Indicative grade",
            (
                clean_text(
                    row[
                        cols["grade"]
                    ]
                )
                if cols["grade"]
                else "—"
            ),
            "Research decision-support grade"
        )


    with c2:

        kpi(
            "Early warning",
            (
                clean_text(
                    row[
                        cols["ews"]
                    ]
                )
                if cols["ews"]
                else "—"
            ),
            "Monitoring signal"
        )


    with c3:

        value = (
            pd.to_numeric(
                pd.Series(
                    [
                        row[
                            cols["stress"]
                        ]
                    ]
                ),
                errors="coerce"
            ).iloc[0]
            if cols["stress"]
            else np.nan
        )


        kpi(
            "Stress vulnerability",
            (
                f"{value:.2f}"
                if pd.notna(
                    value
                )
                else "—"
            ),
            "Relative analytical score"
        )


    with c4:

        value = (
            row[
                cols["borrower_strength"]
            ]
            if cols["borrower_strength"]
            else "Not available"
        )


        kpi(
            "Borrower strength",
            clean_text(
                value
            ),
            "Based only on verified available evidence"
        )


    st.write("")


    left,
    right = st.columns(2)


    with left:

        section(
            "Credit posture"
        )

        st.info(

            clean_text(
                row[
                    cols["credit_posture"]
                ]
            )

            if cols["credit_posture"]

            else "Not available"
        )


        section(
            "Primary risk drivers"
        )

        st.write(

            clean_text(
                row[
                    cols["drivers"]
                ]
            )

            if cols["drivers"]

            else (
                "Detailed risk-driver field "
                "is not available in this output."
            )
        )


    with right:

        section(
            "Exposure posture"
        )

        st.info(

            clean_text(
                row[
                    cols["exposure_posture"]
                ]
            )

            if cols["exposure_posture"]

            else "Not available"
        )


        section(
            "Risk mitigants"
        )

        st.write(

            clean_text(
                row[
                    cols["mitigants"]
                ]
            )

            if cols["mitigants"]

            else (
                "Detailed mitigant field "
                "is not available in this output."
            )
        )


    with st.expander(
        "View complete analytical record"
    ):

        record = (

            row
            .to_frame(
                name="Value"
            )
            .reset_index()
            .rename(
                columns={
                    "index":
                        "Field"
                }
            )
        )


        st.dataframe(

            record,

            use_container_width=True,

            hide_index=True
        )


# =============================================================================
# STRESS TESTING
# =============================================================================

def render_stress():

    hero(

        "Stress Testing",

        (
            "Scenario analysis of relative project "
            "vulnerability under adverse banking and "
            "macro-financial conditions."
        )
    )


    stress,
    path = load_first(
        STRESS_CANDIDATES
    )


    if stress is None:

        st.info(
            "Stress-test output could not be located."
        )

        return


    scenario_col = find_col(
        stress,
        [
            "scenario",
            "stress_scenario"
        ]
    )


    score_col = find_col(
        stress,
        [
            "stress_score",
            "stressed_score",
            "vulnerability_score",
            "score"
        ]
    )


    if (
        scenario_col
        and score_col
    ):

        temp = stress[
            [
                scenario_col,
                score_col
            ]
        ].copy()


        temp[
            score_col
        ] = pd.to_numeric(
            temp[
                score_col
            ],
            errors="coerce"
        )


        summary = (

            temp
            .groupby(
                scenario_col
            )[
                score_col
            ]
            .mean()
            .reset_index(
                name="Mean score"
            )
        )


        section(
            "Scenario progression",
            "Mean constructed vulnerability score by scenario."
        )


        fig = px.line(

            summary,

            x=
                scenario_col,

            y=
                "Mean score",

            markers=True
        )


        show_chart(
            fig,
            height=390
        )


    else:

        # Attempt wide scenario structure

        scenario_fields = []


        for candidate in [
            "baseline",
            "mild",
            "moderate",
            "severe"
        ]:

            col = find_col(
                stress,
                [
                    candidate,
                    candidate
                    + "_score"
                ]
            )

            if col:

                scenario_fields.append(
                    (
                        candidate.title(),
                        col
                    )
                )


        if scenario_fields:

            scenario_summary = []


            for label, col in scenario_fields:

                values = pd.to_numeric(
                    stress[
                        col
                    ],
                    errors="coerce"
                )


                scenario_summary.append({

                    "Scenario":
                        label,

                    "Mean score":
                        values.mean()
                })


            summary = pd.DataFrame(
                scenario_summary
            )


            fig = px.line(

                summary,

                x=
                    "Scenario",

                y=
                    "Mean score",

                markers=True
            )


            show_chart(
                fig,
                height=390
            )


        else:

            st.dataframe(
                stress.head(30),
                use_container_width=True,
                hide_index=True
            )


    st.caption(
        (
            "Stress scores are constructed analytical "
            "indices and are not observed defaults or losses."
        )
    )


# =============================================================================
# MONTE CARLO
# =============================================================================

def render_monte_carlo():

    hero(

        "Monte Carlo Tail Risk",

        (
            "Distribution-based analytical stress "
            "assessment under simulated adverse conditions."
        )
    )


    mc,
    path = load_first(
        MONTE_CARLO_CANDIDATES
    )


    if mc is None:

        st.info(
            "Monte Carlo summary could not be located."
        )

        return


    company = find_col(
        mc,
        [
            "company",
            "project_name",
            "project_id"
        ]
    )


    mean_col = find_col(
        mc,
        [
            "mean_score",
            "mc_mean",
            "monte_carlo_mean"
        ]
    )


    p95_col = find_col(
        mc,
        [
            "p95",
            "p95_score",
            "mc_p95",
            "tail_risk_p95"
        ]
    )


    top3_col = find_col(
        mc,
        [
            "top3_probability",
            "top_3_probability",
            "probability_top3"
        ]
    )


    if (
        company
        and mean_col
        and p95_col
    ):

        plot = mc[
            [
                company,
                mean_col,
                p95_col
            ]
        ].copy()


        plot[
            mean_col
        ] = pd.to_numeric(
            plot[
                mean_col
            ],
            errors="coerce"
        )


        plot[
            p95_col
        ] = pd.to_numeric(
            plot[
                p95_col
            ],
            errors="coerce"
        )


        plot = plot.dropna()


        section(
            "Mean risk vs tail risk",
            "Projects farther upward exhibit higher simulated tail vulnerability."
        )


        fig = px.scatter(

            plot,

            x=
                mean_col,

            y=
                p95_col,

            hover_name=
                company
        )


        show_chart(
            fig,
            height=450
        )


    elif (
        company
        and p95_col
    ):

        ranking = mc[
            [
                company,
                p95_col
            ]
        ].copy()


        ranking[
            p95_col
        ] = pd.to_numeric(
            ranking[
                p95_col
            ],
            errors="coerce"
        )


        ranking = ranking.sort_values(
            p95_col,
            ascending=False
        )


        fig = px.bar(

            ranking,

            x=
                p95_col,

            y=
                company,

            orientation="h"
        )


        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            )
        )


        show_chart(
            fig,
            height=470
        )


    else:

        st.dataframe(
            mc,
            use_container_width=True,
            hide_index=True
        )


    st.caption(
        (
            "Monte Carlo shock distributions are "
            "analytical assumptions and are not estimated "
            "default probabilities."
        )
    )


# =============================================================================
# ALLOCATION
# =============================================================================

def render_allocation(
    bank,
    cols
):

    hero(

        "Portfolio Allocation",

        (
            "Concentration-aware credit allocation "
            "and portfolio exposure analysis."
        )
    )


    alloc,
    path = load_first(
        ALLOCATION_CANDIDATES
    )


    if alloc is None:

        # Fall back to bank layer if allocation variables carried through.

        alloc = bank.copy()


    company = find_col(
        alloc,
        [
            "company",
            "project_name",
            "project_id"
        ]
    )


    amount = find_col(
        alloc,
        [
            "allocated_credit_crore",
            "allocation_crore",
            "recommended_allocation_crore",
            "mean_allocation_crore"
        ]
    )


    state = find_col(
        alloc,
        [
            "state"
        ]
    )


    if (
        company
        and amount
    ):

        plot = alloc[
            [
                company,
                amount
            ]
        ].copy()


        plot[
            amount
        ] = pd.to_numeric(
            plot[
                amount
            ],
            errors="coerce"
        )


        plot = (

            plot
            .dropna(
                subset=[
                    amount
                ]
            )
            .sort_values(
                amount,
                ascending=False
            )
        )


        section(
            "Relative project allocation",
            (
                "Model allocation output where available; "
                "not an actual sanctioned bank facility."
            )
        )


        fig = px.bar(

            plot,

            x=
                amount,

            y=
                company,

            orientation=
                "h"
        )


        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            )
        )


        show_chart(
            fig,
            height=480
        )


    elif (
        cols["amount"]
        and cols["company"]
    ):

        section(
            "Project financial scale",
            (
                "Allocation output unavailable; "
                "showing project scale instead."
            )
        )


        plot = bank[
            [
                cols["company"],
                cols["amount"]
            ]
        ].copy()


        plot[
            cols["amount"]
        ] = pd.to_numeric(
            plot[
                cols["amount"]
            ],
            errors="coerce"
        )


        plot = plot.sort_values(
            cols["amount"],
            ascending=False
        )


        fig = px.bar(

            plot,

            x=
                cols["amount"],

            y=
                cols["company"],

            orientation=
                "h"
        )


        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            )
        )


        show_chart(
            fig,
            height=480
        )


    st.info(
        (
            "Portfolio optimization supports exposure "
            "analysis only. It does not constitute a "
            "loan sanction recommendation."
        )
    )


# =============================================================================
# VALIDATION
# =============================================================================

def render_validation(
    bank,
    path
):

    hero(

        "Model Validation & Governance",

        (
            "Evidence, methodological boundaries and "
            "controls supporting responsible interpretation."
        )
    )


    c1,
    c2,
    c3 = st.columns(3)


    with c1:

        kpi(
            "Bank-model observations",
            str(
                len(
                    bank
                )
            ),
            "Loaded directly from final decision-support output"
        )


    with c2:

        kpi(
            "Default target",
            "Not used",
            "No fabricated default labels"
        )


    with c3:

        kpi(
            "Decision mode",
            "Human-in-loop",
            "No automated approval/rejection"
        )


    section(
        "Model architecture"
    )


    st.markdown(
        """
        **Structural ML → stress testing → Monte Carlo →
        borrower evidence → portfolio concentration →
        bank decision-support**
        """
    )


    section(
        "Interpretation boundaries"
    )


    st.warning(
        """
        The framework does not estimate regulatory
        Probability of Default (PD), LGD, EAD or ECL.
        A–E categories are research decision-support
        grades and are not official bank or CRA ratings.
        """
    )


    section(
        "Current deployment classification"
    )


    st.info(
        """
        Zero-cost research / controlled pilot deployment.
        Do not upload confidential bank customer data to
        the public Community Cloud application.
        """
    )


    with st.expander(
        "Technical source file"
    ):

        st.code(
            str(
                path.relative_to(
                    PROJECT_ROOT
                )
            )
        )


# =============================================================================
# APP
# =============================================================================

def render_app():

    initialize_design()


    page = sidebar()


    bank,
    bank_path,
    cols = load_core()


    if page == "Overview":

        render_overview(
            bank,
            cols
        )


    elif page == "Credit Committee":

        render_credit_committee(
            bank,
            cols
        )


    elif page == "Project Analysis":

        render_project_analysis(
            bank,
            cols
        )


    elif page == "Stress Testing":

        render_stress()


    elif page == "Monte Carlo":

        render_monte_carlo()


    elif page == "Portfolio Allocation":

        render_allocation(
            bank,
            cols
        )


    elif page == "Model Validation":

        render_validation(
            bank,
            bank_path
        )


    st.divider()


    st.caption(
        (
            "Semiconductor Credit Intelligence · "
            "Research decision-support prototype · "
            "Human credit judgement required"
        )
    )
