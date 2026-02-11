import streamlit as st
from utils import check_access

check_access()

st.set_page_config(page_title="Trails Dashboard", layout="wide")

params = st.query_params
if "study" not in st.session_state:
    study = params.get("study")
    if not study:
        st.error("⚠️ No study specified")
        st.info("Please access this dashboard through the API with a valid study parameter")
        st.stop()
    st.session_state.study = study


events = st.Page("pages/events.py", title="Events", icon="📊")
flows = st.Page("pages/flows.py", title="Flows", icon="🔄")

pg = st.navigation([events, flows])
pg.run()