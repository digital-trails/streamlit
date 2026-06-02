import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, consents_as_flows, to_local_naive, get_unique_linking_codes

check_access_admin_only()

study = st.session_state.get("study")
datums = load_data(study)
datums["date"] = datums.apply(lambda r: to_local_naive(r['date'], r['tz']), axis=1)

all_flows = completed_flow_values(datums)[["flow_name","linking_code","date"]].drop_duplicates()
consents = consents_as_flows(datums)

st.title("Events")


all_linking_codes = get_unique_linking_codes(study)
with st.container(border=True):
    selected_linking_codes = st.multiselect("Linking Codes", all_linking_codes, default=all_linking_codes)
    print(selected_linking_codes)
if selected_linking_codes != []:
    flows = all_flows[all_flows["linking_code"].isin(selected_linking_codes)]
    st.scatter_chart(pd.concat([flows, consents]), x="date",y="linking_code",color="flow_name")
else:    
    st.scatter_chart(pd.concat([all_flows,consents]), x="date", y="linking_code", color="flow_name")

