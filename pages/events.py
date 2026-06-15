import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, consents_as_flows, to_local_naive, get_unique_linking_codes
import datetime

study = "mtm-t2"
datums = load_data(study)
datums["date"] = datums.apply(lambda r: to_local_naive(r['date'], r['tz']), axis=1)

all_flows = completed_flow_values(datums)[["flow_name","linking_code","date"]].drop_duplicates()
consents = consents_as_flows(datums)

def round_timestamp_to_day(timestamp: float) -> float:
    asPdTimestamp = pd.Timestamp(1970, 1, 1, tz='UTC') + pd.Timedelta(seconds=timestamp)
    rounded_ts = asPdTimestamp.round('1D')
    rounded_epoch = float(rounded_ts.timestamp())
    return rounded_epoch

st.title("Events")


all_linking_codes = get_unique_linking_codes(study)
with st.container(border=True):
    selected_linking_codes = st.multiselect("Linking Codes", all_linking_codes, default=None)
    
if selected_linking_codes is not None and len(selected_linking_codes)>0:
    flows = all_flows[all_flows["linking_code"].isin(selected_linking_codes)]
    st.scatter_chart(pd.concat([flows, consents]), x="date",y="linking_code",color="flow_name")
else:    
    st.scatter_chart(pd.concat([all_flows,consents]), x="date", y="linking_code", color="flow_name")

# --- Session Heatmap Grid ---
st.header("Sessions per Participant by Date")

# Get flow data with flow_id for counting unique sessions
flows_with_id = completed_flow_values(datums)[["flow_name","linking_code","ts","flow_id"]].drop_duplicates()

print(flows_with_id)

flows_with_id = flows_with_id[flows_with_id["flow_name"]=="sessions"]
flows_with_id["ts"] = flows_with_id["ts"].apply(round_timestamp_to_day)

# Count unique flow_id groups per linking_code per date
session_counts = flows_with_id.groupby(["linking_code", "ts"])["flow_id"].nunique().reset_index()
session_counts = session_counts.rename(columns={"flow_id": "session_count"})

# Pivot: rows = linking_code, columns = date, values = session_count
session_counts["ts"] = session_counts["ts"].apply(datetime.date.fromtimestamp).astype(str)
heatmap_df = session_counts.pivot(index="linking_code", columns="ts", values="session_count")
heatmap_df = heatmap_df.fillna(0).astype(int)

# Sort columns chronologically
heatmap_df = heatmap_df.reindex(sorted(heatmap_df.columns), axis=1)

# Date range filter
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", value=None)
with col2:
    end_date = st.date_input("End date", value=None)

if start_date is not None and end_date is not None:
    filtered_dates = [d for d in heatmap_df.columns if start_date <= datetime.date.fromisoformat(d) <= end_date]
    if filtered_dates:
        heatmap_df = heatmap_df[filtered_dates]
    else:
        st.warning("No dates in the selected range.")

if not heatmap_df.empty:
    # Format cells as integers for display
    styled_table = heatmap_df.style.format("{:.0f}")
    
    # Apply yellow-to-red gradient on all columns (linking_code column excluded by default since it's the index)
    styled_table = styled_table.background_gradient(
        cmap="YlOrRd",
        axis=None,
        subset=None,  # Apply to all numeric columns
        low=0.1,
        high=0.9,
    )
    
    st.dataframe(
        styled_table,
        column_config={
            col: st.column_config.NumberColumn(col)
            for col in heatmap_df.columns
        },
    )
else:
    st.info("No session data available for the selected filters.")