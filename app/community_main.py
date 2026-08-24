# =============================================================================
# STREAMLIT COMMUNITY CLOUD ENTRYPOINT
# =============================================================================

import streamlit as st


st.set_page_config(
    page_title="Semiconductor Credit Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.cloud_dashboard import render_app

render_app()
