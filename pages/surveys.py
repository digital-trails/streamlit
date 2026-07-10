import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_datums, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")

st.title("Surveys")

datums = load_datums(study)
flows = completed_flow_values(datums, only_completed=False)

if flows is None or flows.empty:
    st.text("No data is available")

else:
    for fn in flows["flow_name"].drop_duplicates().sort_values().tolist():
        st.write(f"### {fn}")
        flow = flows[flows["flow_name"] == fn]
        flow = flow.drop_duplicates(["flow_id","name"]).sort_values(["date"])
        st.write(flow.pivot(index=["linking_code","flow_id","date"], columns="name", values="value"))
