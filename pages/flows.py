import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")
def process_flows(df):
    flows = df[(df["type"]=="Flow")].reset_index(drop=True).copy()
    flows["flow_id"] = flows["data"].apply(lambda d: d.get("flow_id"))
    
    flow_names = flows[flows["data"].apply(lambda d: d.get("name") == "$RootPath")].copy()
    flow_names["flow_name"] = flow_names["data"].apply(
        lambda d: d["value"][d["value"][:-1].rfind("/")+1:].strip("/").replace(".json","")
    )
    flow_names = flow_names[["flow_id","pid","date","flow_name"]]
    
    flows = pd.merge(flows, flow_names)
    
    flow_values = flows[flows["data"].apply(
        lambda d: d.get("type") != "metadata" and d.get("name") != None
    )].copy()
    flow_values["name"] = flow_values["data"].apply(lambda d: d["name"])
    flow_values["value"] = flow_values["data"].apply(lambda d: d["value"])
    
    return flow_values[["flow_id","flow_name","name","value"]]

st.title("Flows")

flows = completed_flow_values(load_data(study))

for fn in flows["flow_name"].drop_duplicates().tolist().sort():
    st.write(f"### {fn}")
    flow = flows[flows["flow_name"] == fn]
    flow = flow.drop_duplicates(["flow_id","name"]).sort_values(["date"])
    st.write(flow.pivot(index=["code","flow_id","date"], columns="name", values="value"))
