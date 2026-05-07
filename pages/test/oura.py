import json
import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data

check_access_admin_only()
study = st.session_state.get("study")

def parse_oura_rows(df):
    oura = df[df["type"] == "oura"].copy().reset_index(drop=True)

    def extract(row):
        inner = json.loads(row["data"])
        return {
            **{k: v for k, v in inner.items() if not isinstance(v, (dict, list))},
            "_pid": row.get("pid"),
            "_date": pd.to_datetime(row.get("ts"), unit="s"),
            "_data_type": row.get("dataType", "unknown"),
        }

    records = [extract(row) for _, row in oura.iterrows()]
    return pd.DataFrame(records)

st.title("Oura Health Data")
df = parse_oura_rows(load_data(study))

if df.empty:
    st.info("No Oura data found for this study.")
    st.stop()

data_types = sorted(df["_data_type"].dropna().unique())
selected_type = st.sidebar.selectbox("Data Type", ["All"] + list(data_types))
if selected_type != "All":
    df = df[df["_data_type"] == selected_type]

participants = sorted(df["_pid"].dropna().unique())
selected_pid = st.sidebar.selectbox("Participant", ["All"] + list(participants))
if selected_pid != "All":
    df = df[df["_pid"] == selected_pid]

st.write(f"**{len(df)} records**")

for dt in sorted(df["_data_type"].dropna().unique()):
    st.write(f"### {dt.replace('_', ' ').title()}")
    subset = df[df["_data_type"] == dt].dropna(axis=1, how="all")
    display_cols = [c for c in subset.columns if not c.startswith("_")]
    st.dataframe(subset[display_cols + ["_pid", "_date"]].sort_values("_date"), use_container_width=True)