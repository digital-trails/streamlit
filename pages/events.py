import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

def enrollments_as_flows(df: pd.DataFrame):
    df2 = df[df["type"]=="Consent"].copy()
    df2["flow_name"] = "consent"
    return df2[["flow_name","linking_code","date"]]

study = st.session_state.get("study")
datums = load_data(study)
flows = completed_flow_values(datums)[["flow_name","linking_code","date"]].drop_duplicates()
enrollments = enrollments_as_flows(datums)

st.title("Events")
st.scatter_chart(pd.concat([flows,datums]), x="date", y="linking_code", color="flow_name")
