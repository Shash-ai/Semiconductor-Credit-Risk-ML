# =============================================================================
# STREAMLIT COMMUNITY CLOUD ENTRYPOINT
# =============================================================================

from pathlib import Path
import sys

import streamlit as st


st.set_page_config(
    page_title="Semiconductor Credit Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit executes this file from inside the app directory on Community Cloud.
# Add that directory explicitly so the dashboard module resolves independently
# of package/import-path behavior.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from cloud_dashboard import render_app

render_app()
