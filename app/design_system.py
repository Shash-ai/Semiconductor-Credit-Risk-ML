"""
Banking Product Design System
=============================

Visual presentation only.

Does not change:
- model calculations
- risk scores
- rankings
- grades
- stress scenarios
- Monte Carlo results
- allocation results
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio


# =============================================================================
# PALETTE
# =============================================================================

NAVY = "#12263A"
NAVY_2 = "#1B3A55"
BLUE = "#2E6F9E"
BLUE_LIGHT = "#6EA6C8"

BACKGROUND = "#F5F7FA"
SURFACE = "#FFFFFF"
SURFACE_2 = "#F9FAFB"

TEXT = "#172033"
TEXT_2 = "#344054"
MUTED = "#667085"

BORDER = "#E3E8EF"
GRID = "#E8EDF3"

GREEN = "#1F7A5A"
GREEN_BG = "#EAF6F1"

AMBER = "#9A6515"
AMBER_BG = "#FFF6E5"

RED = "#A33D46"
RED_BG = "#FCEDEF"

PURPLE = "#765A88"


# =============================================================================
# TYPOGRAPHY
# =============================================================================

FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)

NUMBER_FONT = (
    "'SFMono-Regular', Consolas, "
    "'Liberation Mono', monospace"
)


# =============================================================================
# GLOBAL CSS
# =============================================================================

CSS = f"""
<style>

/* -------------------------------------------------------------------------- */
/* APP                                                                        */
/* -------------------------------------------------------------------------- */

.stApp {{
    background:
        linear-gradient(
            180deg,
            #F7F9FC 0%,
            {BACKGROUND} 100%
        );
}}


.block-container {{
    max-width: 1500px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    padding-left: 2.4rem;
    padding-right: 2.4rem;
}}


/* -------------------------------------------------------------------------- */
/* TYPOGRAPHY                                                                 */
/* -------------------------------------------------------------------------- */

html,
body,
[class*="css"],
p,
div,
span,
button,
input,
textarea,
select {{
    font-family: {FONT_STACK};
}}


h1 {{
    color: {TEXT} !important;

    font-size:
        clamp(1.8rem, 2.8vw, 2.45rem)
        !important;

    font-weight:
        760 !important;

    letter-spacing:
        -0.045em !important;

    line-height:
        1.12 !important;
}}


h2 {{
    color: {TEXT} !important;

    font-size:
        1.45rem !important;

    font-weight:
        720 !important;

    letter-spacing:
        -0.025em !important;
}}


h3 {{
    color: {TEXT_2} !important;

    font-size:
        1.08rem !important;

    font-weight:
        680 !important;

    letter-spacing:
        -0.01em !important;
}}


p {{
    color: {MUTED};
    line-height: 1.6;
}}


/* Numbers */

.metric-number {{
    font-family:
        {NUMBER_FONT};

    font-variant-numeric:
        tabular-nums;

    letter-spacing:
        -0.04em;
}}


/* -------------------------------------------------------------------------- */
/* SIDEBAR                                                                    */
/* -------------------------------------------------------------------------- */

section[data-testid="stSidebar"] {{

    background:
        linear-gradient(
            180deg,
            #0F1D2A 0%,
            #152A3B 52%,
            #17344A 100%
        );

    border-right:
        1px solid
        rgba(255,255,255,0.06);
}}


section[data-testid="stSidebar"] * {{
    color: #F2F6F9;
}}


section[data-testid="stSidebar"]
div[role="radiogroup"] label {{

    border-radius:
        9px;

    padding:
        0.25rem 0.35rem;

    transition:
        background 0.15s ease;
}}


section[data-testid="stSidebar"]
div[role="radiogroup"] label:hover {{

    background:
        rgba(255,255,255,0.07);
}}


/* -------------------------------------------------------------------------- */
/* KPI CARDS                                                                  */
/* -------------------------------------------------------------------------- */

.bank-kpi {{

    background:
        linear-gradient(
            180deg,
            #FFFFFF 0%,
            #FCFDFE 100%
        );

    border:
        1px solid {BORDER};

    border-radius:
        16px;

    padding:
        1.15rem 1.2rem;

    min-height:
        122px;

    box-shadow:
        0 2px 5px
            rgba(17, 34, 51, 0.025),

        0 10px 28px
            rgba(17, 34, 51, 0.045);

    transition:
        transform 0.18s ease,
        box-shadow 0.18s ease,
        border-color 0.18s ease;
}}


.bank-kpi:hover {{

    transform:
        translateY(-2px);

    border-color:
        #D3DCE5;

    box-shadow:
        0 5px 10px
            rgba(17, 34, 51, 0.035),

        0 14px 34px
            rgba(17, 34, 51, 0.065);
}}


.bank-kpi-label {{

    color:
        {MUTED};

    font-size:
        0.76rem;

    font-weight:
        670;

    letter-spacing:
        0.04em;

    text-transform:
        uppercase;
}}


.bank-kpi-value {{

    color:
        {TEXT};

    font-family:
        {NUMBER_FONT};

    font-size:
        1.72rem;

    font-weight:
        760;

    letter-spacing:
        -0.045em;

    margin-top:
        0.42rem;
}}


.bank-kpi-note {{

    color:
        {MUTED};

    font-size:
        0.75rem;

    margin-top:
        0.42rem;
}}


/* -------------------------------------------------------------------------- */
/* CONTENT CARDS                                                              */
/* -------------------------------------------------------------------------- */

.bank-card {{

    background:
        rgba(255,255,255,0.98);

    border:
        1px solid {BORDER};

    border-radius:
        16px;

    padding:
        1.1rem 1.15rem;

    box-shadow:
        0 5px 22px
        rgba(20,35,50,0.035);
}}


.bank-card-title {{

    color:
        {TEXT};

    font-size:
        0.96rem;

    font-weight:
        700;

    letter-spacing:
        -0.01em;
}}


.bank-card-subtitle {{

    color:
        {MUTED};

    font-size:
        0.78rem;

    margin-top:
        0.2rem;
}}


/* -------------------------------------------------------------------------- */
/* PAGE HERO                                                                  */
/* -------------------------------------------------------------------------- */

.bank-hero {{
    margin-bottom:
        1.5rem;
}}


.bank-eyebrow {{

    color:
        {BLUE};

    font-size:
        0.72rem;

    font-weight:
        760;

    letter-spacing:
        0.095em;

    text-transform:
        uppercase;

    margin-bottom:
        0.45rem;
}}


.bank-title {{

    color:
        {TEXT};

    font-size:
        clamp(2rem, 3.3vw, 2.7rem);

    font-weight:
        780;

    letter-spacing:
        -0.052em;

    line-height:
        1.06;
}}


.bank-subtitle {{

    color:
        {MUTED};

    font-size:
        0.93rem;

    max-width:
        780px;

    line-height:
        1.58;

    margin-top:
        0.65rem;
}}


/* -------------------------------------------------------------------------- */
/* BADGES                                                                     */
/* -------------------------------------------------------------------------- */

.risk-badge {{

    display:
        inline-flex;

    align-items:
        center;

    gap:
        0.35rem;

    border-radius:
        100px;

    padding:
        0.25rem 0.6rem;

    font-size:
        0.72rem;

    font-weight:
        720;
}}


.badge-green {{
    background:
        {GREEN_BG};
    color:
        {GREEN};
}}


.badge-amber {{
    background:
        {AMBER_BG};
    color:
        {AMBER};
}}


.badge-red {{
    background:
        {RED_BG};
    color:
        {RED};
}}


.badge-neutral {{
    background:
        #EEF2F6;
    color:
        {TEXT_2};
}}


/* -------------------------------------------------------------------------- */
/* STREAMLIT METRICS                                                          */
/* -------------------------------------------------------------------------- */

div[data-testid="stMetric"] {{

    background:
        #FFFFFF;

    border:
        1px solid {BORDER};

    border-radius:
        15px;

    padding:
        1rem 1.1rem;

    box-shadow:
        0 5px 20px
        rgba(18,38,58,0.035);
}}


div[data-testid="stMetricLabel"] {{
    color:
        {MUTED} !important;

    font-weight:
        650 !important;
}}


div[data-testid="stMetricValue"] {{

    color:
        {TEXT} !important;

    font-family:
        {NUMBER_FONT};

    font-weight:
        760 !important;

    font-variant-numeric:
        tabular-nums;
}}


/* -------------------------------------------------------------------------- */
/* TABS                                                                       */
/* -------------------------------------------------------------------------- */

button[data-baseweb="tab"] {{

    border-radius:
        10px;

    padding:
        0.55rem 0.9rem;

    font-weight:
        650;

    color:
        {MUTED};

    transition:
        all 0.15s ease;
}}


button[data-baseweb="tab"][aria-selected="true"] {{

    color:
        {NAVY};

    background:
        #EAF1F6;
}}


/* -------------------------------------------------------------------------- */
/* DATAFRAMES                                                                 */
/* -------------------------------------------------------------------------- */

div[data-testid="stDataFrame"] {{

    border:
        1px solid {BORDER};

    border-radius:
        14px;

    overflow:
        hidden;

    background:
        #FFFFFF;

    box-shadow:
        0 5px 22px
        rgba(18,38,58,0.03);
}}


/* -------------------------------------------------------------------------- */
/* SELECTBOX / INPUT                                                          */
/* -------------------------------------------------------------------------- */

div[data-baseweb="select"] > div,
div[data-baseweb="input"] {{

    border-radius:
        10px !important;

    border-color:
        #DCE3EA !important;
}}


/* -------------------------------------------------------------------------- */
/* BUTTON                                                                     */
/* -------------------------------------------------------------------------- */

.stButton > button {{

    border-radius:
        10px;

    font-weight:
        670;

    border:
        1px solid
        #DCE4EB;

    transition:
        transform 0.15s ease,
        border 0.15s ease;
}}


.stButton > button:hover {{

    transform:
        translateY(-1px);

    border-color:
        #BBC8D4;
}}


/* -------------------------------------------------------------------------- */
/* ALERTS                                                                     */
/* -------------------------------------------------------------------------- */

div[data-testid="stAlert"] {{

    border-radius:
        13px;

    border:
        1px solid
        rgba(0,0,0,0.045);
}}


/* -------------------------------------------------------------------------- */
/* EXPANDERS                                                                  */
/* -------------------------------------------------------------------------- */

details {{

    background:
        #FFFFFF !important;

    border:
        1px solid
        {BORDER} !important;

    border-radius:
        13px !important;
}}


/* -------------------------------------------------------------------------- */
/* SCROLLBAR                                                                  */
/* -------------------------------------------------------------------------- */

::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}


::-webkit-scrollbar-track {{
    background:
        transparent;
}}


::-webkit-scrollbar-thumb {{

    background:
        #C4CDD6;

    border-radius:
        20px;
}}


::-webkit-scrollbar-thumb:hover {{
    background:
        #A6B2BE;
}}


/* -------------------------------------------------------------------------- */
/* ANIMATION                                                                  */
/* -------------------------------------------------------------------------- */

.main .block-container {{

    animation:
        bankFade
        0.24s ease-out;
}}


@keyframes bankFade {{

    from {{
        opacity: 0;
        transform:
            translateY(3px);
    }}

    to {{
        opacity: 1;
        transform:
            translateY(0);
    }}
}}


/* -------------------------------------------------------------------------- */
/* RESPONSIVE                                                                 */
/* -------------------------------------------------------------------------- */

@media (
    max-width: 900px
) {{

    .block-container {{

        padding-left:
            1rem;

        padding-right:
            1rem;
    }}


    .bank-title {{
        font-size:
            1.8rem;
    }}


    .bank-kpi-value {{
        font-size:
            1.45rem;
    }}

}}

</style>
"""


# =============================================================================
# PLOTLY THEME
# =============================================================================

def register_plotly_theme():

    theme = go.layout.Template()

    theme.layout = go.Layout(

        font=dict(
            family=FONT_STACK,
            size=12,
            color=TEXT
        ),

        paper_bgcolor=
            "rgba(0,0,0,0)",

        plot_bgcolor=
            "rgba(0,0,0,0)",

        margin=dict(
            l=32,
            r=24,
            t=54,
            b=40
        ),

        title=dict(
            font=dict(
                family=FONT_STACK,
                size=16,
                color=TEXT
            ),

            x=0.01,

            xanchor=
                "left"
        ),

        legend=dict(

            orientation=
                "h",

            yanchor=
                "bottom",

            y=
                1.02,

            xanchor=
                "right",

            x=
                1,

            font=dict(
                size=10,
                color=MUTED
            )
        ),

        hoverlabel=dict(

            bgcolor=
                "#FFFFFF",

            bordercolor=
                BORDER,

            font=dict(
                family=FONT_STACK,
                size=12,
                color=TEXT
            )
        ),

        xaxis=dict(

            showgrid=
                False,

            zeroline=
                False,

            linecolor=
                BORDER,

            tickfont=dict(
                color=MUTED
            ),

            automargin=
                True
        ),

        yaxis=dict(

            gridcolor=
                GRID,

            gridwidth=
                1,

            zeroline=
                False,

            tickfont=dict(
                color=MUTED
            ),

            automargin=
                True
        ),

        colorway=[

            NAVY,

            BLUE,

            BLUE_LIGHT,

            GREEN,

            "#85764B",

            PURPLE,

            RED,

            "#6B7C8E"
        ]
    )

    pio.templates[
        "bank_product"
    ] = theme

    pio.templates.default = (
        "bank_product"
    )


# =============================================================================
# CHART POLISH
# =============================================================================

def polish_chart(
    fig,
    height=None
):

    if fig is None:
        return fig

    try:

        fig.update_layout(

            template=
                "bank_product",

            autosize=
                True,

            hovermode=
                "closest",

            transition=dict(
                duration=220,
                easing="cubic-in-out"
            ),

            uirevision=
                "bank-product"
        )


        if height:

            fig.update_layout(
                height=height
            )


        fig.update_traces(
            selector=dict(
                type="bar"
            ),

            marker_line_width=0,

            opacity=0.93
        )


        fig.update_traces(
            selector=dict(
                type="scatter"
            ),

            marker=dict(
                size=7
            )
        )


        fig.update_traces(
            selector=dict(
                type="pie"
            ),

            textposition=
                "inside"
        )


    except Exception:

        pass


    return fig


# =============================================================================
# CHART CONFIG
# =============================================================================

CHART_CONFIG = {

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


# =============================================================================
# UI INITIALIZER
# =============================================================================

def initialize_design():

    register_plotly_theme()

    st.markdown(
        CSS,
        unsafe_allow_html=True
    )


# =============================================================================
# HERO
# =============================================================================

def hero(
    title,
    subtitle,
    eyebrow="SEMICONDUCTOR CREDIT INTELLIGENCE"
):

    st.markdown(

        f"""
        <div class="bank-hero">

            <div class="bank-eyebrow">
                {eyebrow}
            </div>

            <div class="bank-title">
                {title}
            </div>

            <div class="bank-subtitle">
                {subtitle}
            </div>

        </div>
        """,

        unsafe_allow_html=True
    )


# =============================================================================
# SECTION HEADER
# =============================================================================

def section(
    title,
    subtitle=None
):

    st.markdown(
        f"### {title}"
    )

    if subtitle:

        st.caption(
            subtitle
        )


# =============================================================================
# KPI CARD
# =============================================================================

def kpi(
    label,
    value,
    note=""
):

    st.markdown(

        f"""
        <div class="bank-kpi">

            <div class="bank-kpi-label">
                {label}
            </div>

            <div class="bank-kpi-value">
                {value}
            </div>

            <div class="bank-kpi-note">
                {note}
            </div>

        </div>
        """,

        unsafe_allow_html=True
    )


# =============================================================================
# BADGE
# =============================================================================

def badge(
    value
):

    value = (
        "Not available"
        if value is None
        else str(value)
    )

    normalized = (
        value.strip().upper()
    )


    if (
        normalized == "GREEN"
        or normalized == "A"
    ):

        css = "badge-green"


    elif (
        normalized == "AMBER"
        or normalized in {
            "B",
            "C"
        }
    ):

        css = "badge-amber"


    elif (
        normalized == "RED"
        or normalized in {
            "D",
            "E"
        }
    ):

        css = "badge-red"


    else:

        css = "badge-neutral"


    return f"""
    <span class="
        risk-badge {css}
    ">
        {value}
    </span>
    """
