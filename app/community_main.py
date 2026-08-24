# =============================================================================
# STREAMLIT COMMUNITY CLOUD ENTRYPOINT
# =============================================================================

import streamlit as st


# Must be first Streamlit command.
st.set_page_config(

    page_title=
        "Semiconductor Credit Intelligence",

    page_icon=
        "🏦",

    layout=
        "wide",

    initial_sidebar_state=
        "expanded"
)


from app.bank_product_ui import (
    render_app
)


render_app()
