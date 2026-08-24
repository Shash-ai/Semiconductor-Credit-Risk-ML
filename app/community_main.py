# =============================================================================
# STREAMLIT COMMUNITY CLOUD ENTRY POINT
# =============================================================================

from pathlib import Path
import runpy
import sys

import streamlit as st


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Semiconductor Credit Risk",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# GOVERNANCE NOTICE
# =============================================================================

st.warning(
    """
    Research / bank-pilot decision-support prototype.

    This system does not estimate regulatory PD, LGD, EAD or ECL,
    does not constitute an official credit rating, and must not
    be used for automated lending decisions.
    """
)


# =============================================================================
# DEPLOYMENT CLASSIFICATION
# =============================================================================

with st.sidebar:

    st.markdown(
        "### Deployment"
    )

    st.write(
        "Streamlit Community Cloud"
    )

    st.caption(
        "Zero-cost research / pilot deployment"
    )


# =============================================================================
# LOAD DASHBOARD
# =============================================================================

dashboard_path = (
    PROJECT_ROOT
    / "app"
    / "community_dashboard_core.py"
)


if not dashboard_path.exists():

    st.error(
        "Cloud dashboard module could not be located."
    )

    st.stop()


try:

    runpy.run_path(
        str(dashboard_path),
        run_name="__main__"
    )

except Exception as exc:

    st.error(
        "The dashboard encountered an application error."
    )

    st.exception(exc)
