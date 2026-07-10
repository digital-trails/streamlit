import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_datums, completed_flow_values, consents_as_events, invites_as_events

check_access_admin_only()

def index_typ(df):
    start_times = { r.linking_code: r.date for r in df.itertuples() if r.event == "invite" }
    for r in df.itertuples():
        if r.event != "track your progress":
            yield r.event
        else:
            start_time = start_times[r.linking_code]
            i = int((r.date-start_time).total_seconds()//(60*60*24*14))
            yield f"track your progress {min(i,4)}"

study = st.session_state.get("study")
data = load_datums(study)

flows = completed_flow_values(data, only_completed=False)
flows = flows[["flow_name","flow_id","linking_code","date"]].drop_duplicates().reset_index()
flows = flows.rename(columns={"flow_name": "event"})[["event","linking_code","date"]]

invites = pd.concat([consents_as_events(data),invites_as_events(data)])
invites["event"] = "invite"

is_intro = flows['event'] == "intro"
is_TYP   = flows['event'].str.startswith("track your progress")

compliance_events = pd.concat([invites,flows[is_intro|is_TYP]]).sort_values(["linking_code","date","event"])

compliance_events["event"] = list(index_typ(compliance_events))
compliance_events["date"]  = compliance_events["date"].dt.date

compliance_events = compliance_events.sort_values(["linking_code","date","event"]).groupby(['linking_code',"event"]).tail(1)

column_order = ["invite","intro","track your progress 1","track your progress 2","track your progress 3","track your progress 4"]

st.title("Compliance")
st.write(compliance_events.pivot(columns="event",index="linking_code",values="date")[column_order])