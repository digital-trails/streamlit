import streamlit as st

st.set_page_config(page_title="Trails Dashboard", layout="wide")

pages = [
    st.Page("pages/events.py", title="Events"),
    st.Page("pages/flows.py", title="Flows")
]

if st.query_params.get("study") == "mtm":
    pages.append(st.Page("pages/mtm/compliance.py", title="Compliance"))

pg = st.navigation(pages, position="top")
pg.run()