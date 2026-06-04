import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, get_unique_linking_codes
import matplotlib.pyplot as plt
import time

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

st.title("Surveys")

flows = completed_flow_values(load_data(study))
all_linking_codes = get_unique_linking_codes(study)

selectbox_uuid = 0
for fn in flows["flow_name"].drop_duplicates().sort_values().tolist():
    st.write(f"### {fn}")
    
    flow = flows[flows["flow_name"] == fn]
    flow = flow.drop_duplicates(["flow_id","name"]).sort_values(["date"])

    if fn == "end of day":
        selected_participant = st.selectbox(label="Participant to view", options=all_linking_codes, index=None)

        if selected_participant is not None:
            st.write(f"Showing data for: {selected_participant}")
            flow = flow[flow["linking_code"]==selected_participant]

            flow = flow[flow["name"]!="schedule_session"]

            emotions = flow[flow["name"]=="nightly_manageemotions"]
            thinkdiff = flow[flow["name"]=="nightly_thinkdifferently"]
            overall = flow[flow["name"]=="nightly_overall"]

            emotions = emotions[emotions["value"].notna()]
            thinkdiff = thinkdiff[thinkdiff["value"].notna()]
            overall = overall[overall["value"].notna()]
            
            # Combine all three metrics into one dataframe for scatter chart
            chart_data = pd.concat([emotions, thinkdiff, overall])
            chart_data = chart_data[["date", "value", "name"]].copy()
            chart_data["value"] = chart_data["value"].astype(int)

            print(chart_data)
            
            st.line_chart(data=chart_data, x="date", y="value", color="name")

        else:
            st.write("No participant selected")

    st.write(flow.pivot(index=["linking_code","flow_id","date"], columns="name", values="value"))
