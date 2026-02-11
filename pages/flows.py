import streamlit as st
import pandas as pd
from utils import check_access, load_data

check_access()

study = st.session_state.get("study")
if not study:
    st.error("⚠️ No study in session")
    st.stop()

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

st.title("🔄 Flow Details")
st.write(f"Study: **{study}**")

df = load_data(study)
flow_values = process_flows(df)

for fn in flow_values["flow_name"].drop_duplicates().tolist():
    st.write(f"### {fn}")
    specific = flow_values[flow_values["flow_name"] == fn]
    specific = specific.drop_duplicates(["flow_id","name"])
    st.write(specific.pivot(index=["flow_id"], columns="name", values="value"))