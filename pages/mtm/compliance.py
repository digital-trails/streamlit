import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, consents_as_flows

check_access_admin_only()

def index_flow_name(df):
    start_times = { r.linking_code: r.date for r in compliance_flows.itertuples() if r.flow_name == "consent" }
    for r in df.itertuples():
        if r.flow_name != "track your progress":
            yield r.flow_name
        else:
            start_time = start_times[r.linking_code]
            i = int((r.date-start_time).total_seconds()//(60*60*24*14))
            yield f"track your progress {min(i,4)}"

study = st.session_state.get("study")
data = load_data(study)
flows = completed_flow_values(data)[["flow_name","linking_code","date"]].drop_duplicates()
consents = consents_as_flows(data)

is_intro = flows['flow_name'] == "intro"
is_TYP   = flows['flow_name'].str.startswith("track your progress")

compliance_flows = pd.concat([consents,flows[is_intro|is_TYP]]).sort_values(["linking_code","date","flow_name"])

compliance_flows["flow_name"] = list(index_flow_name(compliance_flows))
compliance_flows["date"] = compliance_flows["date"].dt.date

compliance_flows = compliance_flows.sort_values(["linking_code","date","flow_name"]).groupby(['linking_code',"flow_name"]).tail(1)

st.title("Compliance")
st.write(compliance_flows.pivot(columns="flow_name",index="linking_code",values="date"))