import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")

st.title("Surveys")

datums = load_data(study)
flows = completed_flow_values(datums, only_completed=False)

if flows is None or flows.empty:
    st.text("No data is available")

else:

    flow_dates = flows.groupby("flow_id")["date"].min().reset_index()
    flow_dates["date"] = flow_dates["date"].dt.date
    flows = flows[["linking_code","flow_id","flow_name","name","value"]]
    flows = flows.merge(flow_dates)

    for fn in flows["flow_name"].drop_duplicates().sort_values().tolist():
        st.write(f"### {fn}")
        flow = flows[flows["flow_name"] == fn]
        flow = flow.drop_duplicates(["flow_id","name"]).sort_values(["date"])
        st.write(flow.pivot(index=["linking_code","flow_id","date"], columns="name", values="value"))
