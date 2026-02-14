import streamlit as st
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")

st.title("Safety")

flows = completed_flow_values(load_data(study))

dep_names = [f"neuroqol_dep_{i}" for i in range(1,9)]
anx_names = [f"neuroqol_anx_{i}" for i in range(1,9)]

def nanint(x):
    try:
        return int(x)
    except:
        return float('nan')

def nansum(x):
    return x.sum() if not x.isna().any() else float('nan')

for tipe, neuroqol_names in [("Anxiety",anx_names), ("Depression",dep_names)]:

    neuroqol_elements = flows[flows['name'].isin(neuroqol_names)].copy().reset_index(drop=True)

    neuroqol_elements['value'] = neuroqol_elements['value'].apply(nanint)

    neuroqol_baseline = neuroqol_elements[neuroqol_elements["flow_name"] == "intro"]
    neuroqol_checkins = neuroqol_elements[neuroqol_elements["flow_name"] != "intro"]

    baselines = neuroqol_baseline.groupby(["linking_code","date","flow_id"])['value'].apply(nansum).reset_index().rename({"value":"baseline"},axis=1)
    baselines = baselines.sort_values(["linking_code","date"]).groupby('linking_code').head(1) #some users completed intro multiple times, we just take latest
    baselines = baselines[["linking_code","baseline"]]

    checkins = neuroqol_checkins.groupby(["linking_code","flow_id","date"])['value'].apply(nansum).reset_index().rename({"value":"checkin"},axis=1)

    #these values are coded 0-4 but they should be 1-5 so we add +1 for each of the 8 items
    checkins["checkin"] += 8
    baselines["baseline"] += 8

    checkins_with_baselines = checkins.merge(baselines,on="linking_code")

    checkins_with_baselines["change"] = [ r.checkin/r.baseline if r.baseline else float('nan') for r in checkins_with_baselines.itertuples()]
    rising_scores = checkins_with_baselines[checkins_with_baselines["change"] >= 1.5].sort_values("date",ascending=False).copy()
    rising_scores["track your progress"] = rising_scores["checkin"]
    rising_scores["increase"] = (rising_scores["change"].round(2)-1).apply('{:.0%}'.format) #percentage format
    rising_scores = rising_scores.sort_values(["date"],ascending=False)

    st.write(f"## {tipe} Rising Score")
    st.write(rising_scores[["linking_code", "date", "baseline", "track your progress", "increase"]])
