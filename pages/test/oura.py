import streamlit as st
import pandas as pd
import json
from auth import check_access_admin_only
from utils import load_data

check_access_admin_only()
study = st.session_state.get("study")

def parse_oura_rows(df):
    """Filter Oura IoT rows and parse the nested JSON string."""
    oura = df[
        (df["type"] == "Iot") &
        (df["data"].apply(lambda d: d.get("did") == "oura"))
    ].copy().reset_index(drop=True)

    def extract(row):
        raw = row["data"].get("data")
        if not raw:
            return None
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            parsed["_pid"]       = row.get("pid")
            parsed["_date"]      = row.get("date")
            parsed["_data_type"] = row["data"].get("data_type", "unknown")
            return parsed
        except Exception:
            return None

    records = [extract(row) for _, row in oura.iterrows()]
    records = [r for r in records if r is not None]
    return pd.DataFrame(records) if records else pd.DataFrame()

st.title("Oura Health Data")

df_raw = load_data(study)
df = parse_oura_rows(df_raw)

if df.empty:
    st.info("No Oura data found for this study.")
    st.stop()

# Sidebar filters
data_types = sorted(df["_data_type"].dropna().unique().tolist())
selected_type = st.sidebar.selectbox("Data Type", ["All"] + data_types)
if selected_type != "All":
    df = df[df["_data_type"] == selected_type]

participants = sorted(df["_pid"].dropna().unique().tolist())
selected_pid = st.sidebar.selectbox("Participant", ["All"] + participants)
if selected_pid != "All":
    df = df[df["_pid"] == selected_pid]

# Drop internal columns for display
display_cols = [c for c in df.columns if not c.startswith("_")]

st.write(f"**{len(df)} records** — filtered by: `{selected_type}` / `{selected_pid}`")

# Show per data type
for dt in df["_data_type"].dropna().unique():
    st.write(f"### {dt.replace('_', ' ').title()}")
    subset = df[df["_data_type"] == dt][display_cols + ["_pid", "_date"]]
    subset = subset.sort_values("_date")
    st.dataframe(subset, use_container_width=True)