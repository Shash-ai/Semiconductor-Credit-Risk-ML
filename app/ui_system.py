"""
Professional Streamlit UI System
================================

Global design system for the Semiconductor Credit Risk
Decision-Support Platform.

This file controls visual presentation only.
It does not modify analytical calculations.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio


# =============================================================================
# DESIGN TOKENS
# =============================================================================

BACKGROUND = "#F6F8FB"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F9FAFC"

TEXT = "#172033"
TEXT_MUTED = "#667085"

PRIMARY = "#173B57"
PRIMARY_SOFT = "#EAF1F6"

ACCENT = "#327AA5"

BORDER = "#E5EAF0"

SUCCESS = "#217A5B"
WARNING = "#A56A18"
DANGER = "#A63D40"

GRID = "#E9EDF2"


# =============================================================================
# GLOBAL CSS
# =============================================================================

GLOBAL_CSS = """
<style>

/* =========================================================
   APPLICATION
   ========================================================= */

.stApp {
    background:
        linear-gradient(
            180deg,
            #F7F9FC 0%,
            #F4F7FA 100%
        );
}


/* Main page width */

.block-container {
    max-width: 1450px;
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
}


/* =========================================================
   TYPOGRAPHY
   ========================================================= */

html,
body,
[class*="css"] {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        Helvetica,
        Arial,
        sans-serif;
}


h1 {
    font-size: 2.05rem !important;
    font-weight: 720 !important;
    letter-spacing: -0.035em !important;
    color: #172033 !important;
    margin-bottom: 0.25rem !important;
}


h2 {
    font-size: 1.45rem !important;
    font-weight: 680 !important;
    letter-spacing: -0.02em !important;
    color: #172033 !important;
}


h3 {
    font-size: 1.08rem !important;
    font-weight: 650 !important;
    color: #26354A !important;
}


p {
    color: #526174;
}


/* =========================================================
   SIDEBAR
   ========================================================= */

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #101D2A 0%,
            #162838 100%
        );

    border-right: 1px solid rgba(255,255,255,0.06);
}


section[data-testid="stSidebar"] * {
    color: #EEF4F8;
}


section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12);
}


/* =========================================================
   METRIC CARDS
   ========================================================= */

div[data-testid="stMetric"] {

    background: rgba(255,255,255,0.96);

    border:
        1px solid
        #E5EAF0;

    border-radius: 16px;

    padding:
        1.1rem
        1.2rem;

    box-shadow:
        0 2px 4px rgba(20,34,50,0.02),
        0 8px 24px rgba(20,34,50,0.045);

    transition:
        transform 0.18s ease,
        box-shadow 0.18s ease,
        border-color 0.18s ease;
}


div[data-testid="stMetric"]:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 4px 8px rgba(20,34,50,0.03),
        0 12px 32px rgba(20,34,50,0.07);

    border-color:
        #D8E1EA;
}


div[data-testid="stMetricLabel"] {

    color:
        #667085 !important;

    font-size:
        0.78rem !important;

    font-weight:
        620 !important;

    letter-spacing:
        0.02em;
}


div[data-testid="stMetricValue"] {

    color:
        #172033 !important;

    font-size:
        1.75rem !important;

    font-weight:
        720 !important;

    letter-spacing:
        -0.035em;
}


/* =========================================================
   TABS
   ========================================================= */

button[data-baseweb="tab"] {

    border-radius:
        10px;

    padding:
        0.55rem
        0.9rem;

    font-weight:
        600;

    color:
        #667085;

    transition:
        all
        0.16s ease;
}


button[data-baseweb="tab"][aria-selected="true"] {

    background:
        #EAF1F6;

    color:
        #173B57;
}


/* =========================================================
   DATAFRAME / TABLE
   ========================================================= */

div[data-testid="stDataFrame"] {

    border:
        1px solid
        #E5EAF0;

    border-radius:
        14px;

    overflow:
        hidden;

    background:
        #FFFFFF;

    box-shadow:
        0 4px 18px rgba(20,34,50,0.035);
}


/* =========================================================
   INPUTS
   ========================================================= */

div[data-baseweb="select"] > div,
div[data-baseweb="input"] {

    border-radius:
        10px !important;

    border-color:
        #DDE4EC !important;
}


/* =========================================================
   BUTTONS
   ========================================================= */

.stButton > button {

    border-radius:
        10px;

    border:
        1px solid
        #DDE5EC;

    font-weight:
        620;

    padding:
        0.48rem
        0.95rem;

    transition:
        all
        0.16s ease;
}


.stButton > button:hover {

    transform:
        translateY(-1px);

    border-color:
        #BFCBD6;
}


/* =========================================================
   ALERTS
   ========================================================= */

div[data-testid="stAlert"] {

    border-radius:
        13px;

    border:
        1px solid
        rgba(0,0,0,0.05);
}


/* =========================================================
   EXPANDERS
   ========================================================= */

details {

    border:
        1px solid
        #E5EAF0 !important;

    border-radius:
        13px !important;

    background:
        #FFFFFF !important;
}


/* =========================================================
   DIVIDERS
   ========================================================= */

hr {

    border:
        none;

    border-top:
        1px solid
        #E8EDF2;

    margin:
        1.5rem 0;
}


/* =========================================================
   SCROLLBAR
   ========================================================= */

::-webkit-scrollbar {

    width:
        8px;

    height:
        8px;
}


::-webkit-scrollbar-track {

    background:
        transparent;
}


::-webkit-scrollbar-thumb {

    background:
        #C7D0DA;

    border-radius:
        20px;
}


::-webkit-scrollbar-thumb:hover {

    background:
        #AAB6C3;
}


/* =========================================================
   PAGE FADE-IN
   ========================================================= */

.main .block-container {

    animation:
        fadeInPage
        0.28s ease-out;
}


@keyframes fadeInPage {

    from {
        opacity: 0;
        transform:
            translateY(4px);
    }

    to {
        opacity: 1;
        transform:
            translateY(0);
    }
}


/* =========================================================
   MOBILE / TABLET
   ========================================================= */

@media (
    max-width: 900px
) {

    .block-container {

        padding-left:
            1rem;

        padding-right:
            1rem;

        padding-top:
            1.2rem;
    }


    h1 {

        font-size:
            1.65rem !important;
    }

}

</style>
"""


# =============================================================================
# PLOTLY TEMPLATE
# =============================================================================

def register_plotly_template():

    template = go.layout.Template()

    template.layout = go.Layout(

        font=dict(
            family="Inter, Segoe UI, Arial, sans-serif",
            size=13,
            color=TEXT
        ),

        paper_bgcolor="rgba(0,0,0,0)",

        plot_bgcolor="rgba(0,0,0,0)",

        margin=dict(
            l=35,
            r=25,
            t=60,
            b=45
        ),

        title=dict(
            font=dict(
                size=18,
                color=TEXT
            ),
            x=0.01,
            xanchor="left"
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(
                size=11,
                color=TEXT_MUTED
            )
        ),

        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=BORDER,
            font=dict(
                color=TEXT,
                size=12
            )
        ),

        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=BORDER,
            tickfont=dict(
                color=TEXT_MUTED
            ),
            title_font=dict(
                color=TEXT_MUTED
            ),
            automargin=True
        ),

        yaxis=dict(
            gridcolor=GRID,
            gridwidth=1,
            zeroline=False,
            linecolor=BORDER,
            tickfont=dict(
                color=TEXT_MUTED
            ),
            title_font=dict(
                color=TEXT_MUTED
            ),
            automargin=True
        ),

        colorway=[
            "#173B57",
            "#327AA5",
            "#69A6C9",
            "#557A66",
            "#927A50",
            "#795F86",
            "#A35C58",
            "#708090"
        ]
    )

    pio.templates[
        "semiconductor_bank"
    ] = template

    pio.templates.default = (
        "semiconductor_bank"
    )


# =============================================================================
# FIGURE POLISH
# =============================================================================

def polish_figure(
    fig,
    height=None
):

    if fig is None:
        return fig

    try:

        fig.update_layout(

            template=
                "semiconductor_bank",

            autosize=True,

            hovermode=
                "closest",

            transition=dict(
                duration=250,
                easing="cubic-in-out"
            )
        )


        if height is not None:

            fig.update_layout(
                height=height
            )


        # ---------------------------------------------
        # BAR CHARTS
        # ---------------------------------------------

        fig.update_traces(
            selector=dict(
                type="bar"
            ),
            marker_line_width=0,
            opacity=0.94
        )


        # ---------------------------------------------
        # LINE CHARTS
        # ---------------------------------------------

        fig.update_traces(
            selector=dict(
                type="scatter",
                mode="lines"
            ),
            line_width=2.5
        )


        # ---------------------------------------------
        # LINE + MARKER CHARTS
        # ---------------------------------------------

        fig.update_traces(
            selector=dict(
                type="scatter"
            ),
            marker=dict(
                size=7
            )
        )


        # ---------------------------------------------
        # PIE / DONUT
        # ---------------------------------------------

        fig.update_traces(
            selector=dict(
                type="pie"
            ),
            textposition="inside",
            hovertemplate=(
                "%{label}<br>"
                "%{value}<br>"
                "%{percent}"
                "<extra></extra>"
            )
        )


    except Exception:

        # Never break the analytical dashboard
        # because of visual styling.
        pass


    return fig


# =============================================================================
# STREAMLIT CHART WRAPPER
# =============================================================================

_original_plotly_chart = None


def enable_smooth_plotly():

    global _original_plotly_chart

    if _original_plotly_chart is not None:
        return

    _original_plotly_chart = (
        st.plotly_chart
    )


    def smooth_plotly_chart(
        figure_or_data,
        *args,
        **kwargs
    ):

        try:

            polish_figure(
                figure_or_data
            )

        except Exception:
            pass


        config = kwargs.pop(
            "config",
            {}
        ) or {}


        default_config = {

            "displaylogo":
                False,

            "responsive":
                True,

            "scrollZoom":
                False,

            "doubleClick":
                "reset",

            "modeBarButtonsToRemove": [

                "lasso2d",

                "select2d",

                "toggleSpikelines"
            ]
        }


        default_config.update(
            config
        )


        kwargs[
            "config"
        ] = default_config


        # Current Streamlit versions support width.
        # Existing dashboard calls remain untouched.

        if (
            "width"
            not in kwargs
            and
            "use_container_width"
            not in kwargs
        ):

            kwargs[
                "use_container_width"
            ] = True


        return _original_plotly_chart(
            figure_or_data,
            *args,
            **kwargs
        )


    st.plotly_chart = (
        smooth_plotly_chart
    )


# =============================================================================
# DATAFRAME WRAPPER
# =============================================================================

_original_dataframe = None


def enable_smooth_tables():

    global _original_dataframe

    if _original_dataframe is not None:
        return

    _original_dataframe = (
        st.dataframe
    )


    def smooth_dataframe(
        data=None,
        *args,
        **kwargs
    ):

        if (
            "width"
            not in kwargs
            and
            "use_container_width"
            not in kwargs
        ):

            kwargs[
                "use_container_width"
            ] = True


        if (
            "hide_index"
            not in kwargs
        ):

            kwargs[
                "hide_index"
            ] = True


        return _original_dataframe(
            data,
            *args,
            **kwargs
        )


    st.dataframe = (
        smooth_dataframe
    )


# =============================================================================
# UI COMPONENTS
# =============================================================================

def page_header(
    title,
    subtitle=None
):

    st.markdown(
        f"""
        <div style="
            margin-bottom:1.4rem;
        ">
            <div style="
                font-size:2.05rem;
                font-weight:720;
                letter-spacing:-0.035em;
                color:#172033;
            ">
                {title}
            </div>
        """,
        unsafe_allow_html=True
    )

    if subtitle:

        st.markdown(
            f"""
            <div style="
                margin-top:-1rem;
                margin-bottom:1.3rem;
                color:#667085;
                font-size:0.95rem;
            ">
                {subtitle}
            </div>
            """,
            unsafe_allow_html=True
        )


def section_header(
    title,
    description=None
):

    st.markdown(
        f"""
        <div style="
            margin-top:1.3rem;
            margin-bottom:0.75rem;
        ">
            <div style="
                font-size:1.16rem;
                font-weight:680;
                color:#172033;
            ">
                {title}
            </div>
        """,
        unsafe_allow_html=True
    )

    if description:

        st.markdown(
            f"""
            <div style="
                margin-top:-0.65rem;
                margin-bottom:0.8rem;
                color:#667085;
                font-size:0.86rem;
            ">
                {description}
            </div>
            """,
            unsafe_allow_html=True
        )


def insight_card(
    title,
    text
):

    st.markdown(
        f"""
        <div style="
            background:#FFFFFF;
            border:1px solid #E5EAF0;
            border-radius:14px;
            padding:1rem 1.1rem;
            margin:0.55rem 0;
            box-shadow:
                0 4px 18px
                rgba(20,34,50,0.035);
        ">
            <div style="
                color:#172033;
                font-size:0.9rem;
                font-weight:670;
                margin-bottom:0.3rem;
            ">
                {title}
            </div>

            <div style="
                color:#667085;
                font-size:0.86rem;
                line-height:1.55;
            ">
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =============================================================================
# INITIALIZE
# =============================================================================

def initialize_ui():

    register_plotly_template()

    st.markdown(
        GLOBAL_CSS,
        unsafe_allow_html=True
    )

    enable_smooth_plotly()

    enable_smooth_tables()
