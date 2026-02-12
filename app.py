import streamlit as st
from auth import check_access_admin_only

check_access_admin_only()

st.set_page_config(page_title="Trails Dashboard", layout="wide")

events = st.Page("pages/events.py", title="Events")
flows  = st.Page("pages/flows.py",  title="Flows")

pg = st.navigation([events, flows], position="top")
pg.run()