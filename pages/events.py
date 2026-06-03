import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, consents_as_flows, to_local_naive

check_access_admin_only()

study = st.session_state.get("study")
datums = load_data(study)

st.title("Events")

if datums is None or datums.empty:
    st.text("No data is available")

else:
    datums["date"] = datums.apply(lambda r: to_local_naive(r['date'], r['tz']), axis=1)
    flows = completed_flow_values(datums)[["flow_name","linking_code","date"]].drop_duplicates()
    consents = consents_as_flows(datums)
    st.scatter_chart(pd.concat([flows,consents]), x="date", y="linking_code", color="flow_name")
