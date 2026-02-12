import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data

check_access_admin_only()

study = st.session_state.get("study")

def process_event_flows(df):
    flows = df[(df["type"]=="Flow")].reset_index(drop=True).copy()
    flows["flow_id"] = flows["data"].apply(lambda d: d.get("flow_id"))
    
    flow_names = flows[flows["data"].apply(lambda d: d.get("name") == "$RootPath")].copy()
    flow_names["flow_name"] = flow_names["data"].apply(
        lambda d: d["value"][d["value"][:-1].rfind("/")+1:].strip("/").replace(".json","")
    )
    return flow_names[["flow_id","pid","date","flow_name"]]

st.title("Events")
st.write(study)

df = load_data(study)
flow_names = process_event_flows(df)

st.scatter_chart(flow_names[["date","pid","flow_name"]], x="date", y="pid", color="flow_name")