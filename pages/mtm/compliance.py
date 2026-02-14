import streamlit as st
from auth import check_access_admin_only
from utils import load_data, completed_flow_values

check_access_admin_only()

study = st.session_state.get("study")

st.title("Compliance")

flows = completed_flow_values(load_data(study))

def index_flow_name(df):
    typ_index = dict()
    for r in df.itertuples():
        if r.flow_name == "intro":
            yield "intro"
        if r.flow_name == "track your progress":
            i = typ_index.get(r.linking_code,1)
            yield f"track your progress {min(i,4)}"
            typ_index[r.linking_code] = i+1

compliance_flows = flows[flows['flow_name'].isin(["intro","track your progress"])]
compliance_flows = compliance_flows[["flow_name","date","linking_code"]].drop_duplicates()
compliance_flows["flow_name"] = list(index_flow_name(compliance_flows))
compliance_flows["date"] = compliance_flows["date"].dt.date
compliance_flows = compliance_flows.sort_values(["linking_code","date","flow_name"]).groupby(['linking_code',"flow_name"]).head(1)
st.write(compliance_flows.pivot(columns="flow_name",index="linking_code",values="date"))