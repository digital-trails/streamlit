import ast
import json
import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data

check_access_admin_only()
study = st.session_state.get("study")

def safe_parse(raw):
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        try:
            fixed = raw.replace("null", "None").replace("true", "True").replace("false", "False")
            return ast.literal_eval(fixed)
        except Exception:
            return {}

def infer_data_type(inner):
    keys = set(inner.keys())
    if "activity" in keys: return "workout"
    if "sleep_phase_5_min" in keys: return "sleep"
    if "tags" in keys: return "tag"
    if "score" in keys: return "daily_activity"
    return "unknown"

def parse_oura_rows(df):
    oura = df[
        (df["type"] == "Iot") &
        (df["did"] == "oura")
    ].copy().reset_index(drop=True)

    def extract(row):
        try:
            outer = safe_parse(row["data"])
            raw_inner = outer.get("data")
            inner = safe_parse(raw_inner) if raw_inner else outer

            data_type = outer.get("data_type") or infer_data_type(inner)

            inner["_pid"]       = row.get("pid")
            inner["_date"]      = pd.to_datetime(row.get("ts"), unit="s")
            inner["_data_type"] = data_type
            return inner
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

data_types = sorted(df["_data_type"].dropna().unique().tolist())
selected_type = st.sidebar.selectbox("Data Type", ["All"] + data_types)
if selected_type != "All":
    df = df[df["_data_type"] == selected_type]

participants = sorted(df["_pid"].dropna().unique().tolist())
selected_pid = st.sidebar.selectbox("Participant", ["All"] + participants)
if selected_pid != "All":
    df = df[df["_pid"] == selected_pid]

st.write(f"**{len(df)} records**")

for dt in sorted(df["_data_type"].dropna().unique()):
    st.write(f"### {dt.replace('_', ' ').title()}")
    subset = df[df["_data_type"] == dt].copy()

    subset = subset.dropna(axis=1, how="all")

    display_cols = [c for c in subset.columns if not c.startswith("_")]
    subset = subset[display_cols + ["_pid", "_date"]].sort_values("_date")

    st.dataframe(subset, use_container_width=True)