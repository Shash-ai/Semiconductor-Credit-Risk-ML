from pathlib import Path
import sys

import streamlit as st

st.set_page_config(
    page_title="Semiconductor Credit Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from banking_dashboard_v3_1 import render_app

render_app()
