import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")

st.title("Events")

flows = completed_flow_values(load_data(study))
st.scatter_chart(flows[["flow_name","code","date"]].drop_duplicates(), x="date", y="code", color="flow_name")