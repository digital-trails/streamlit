import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_data, completed_flow_values, get_unique_linking_codes
import matplotlib.pyplot as plt
import time

check_access_admin_only()

study = st.session_state.get("study")
def process_flows(df):
    flows = df[(df["type"]=="Flow")].reset_index(drop=True).copy()
    flows["flow_id"] = flows["data"].apply(lambda d: d.get("flow_id"))
    
    flow_names = flows[flows["data"].apply(lambda d: d.get("name") == "$RootPath")].copy()
    flow_names["flow_name"] = flow_names["data"].apply(
        lambda d: d["value"][d["value"][:-1].rfind("/")+1:].strip("/").replace(".json","")
    )
    flow_names = flow_names[["flow_id","pid","date","flow_name"]]
    
    flows = pd.merge(flows, flow_names)
    
    flow_values = flows[flows["data"].apply(
        lambda d: d.get("type") != "metadata" and d.get("name") != None
    )].copy()
    flow_values["name"] = flow_values["data"].apply(lambda d: d["name"])
    flow_values["value"] = flow_values["data"].apply(lambda d: d["value"])
    
    return flow_values[["flow_id","flow_name","name","value"]]


@st.cache_data
def create_typ_diff_chart(flows: pd.DataFrame, first: int, second: int, participant: str):
        """
        Returns a DataFrame of the difference between user selections in the first and second track your progress surveys.

        Parameters:
            flows (DataFrame): The flows given by `utils.completed_flow_values()`
            first (int): {1, 2, 3} - the first of the surveys whose difference is being taken
            second (int): {1, 2, 3} - the survey data whose values will be subtracted from the first
            participant (str): The linking code of the participant whose data is being viewed

        Returns:
            DataFrame: The difference values between the two surveys
        """
        if((first in [1,2,3]) and (second in [1,2,3]) and (participant in get_unique_linking_codes(study))):
             try:

                flows = flows[flows["linking_code"]==participant]

                typ1 = flows[flows["flow_name"]==f"track your progress {first}"]
                typ2 = flows[flows["flow_name"]==f"track your progress {second}"]

                if typ1.empty or typ2.empty: return pd.DataFrame()

                typ2 = typ2.sort_values("name")
                typ1 = typ1.sort_values("name")

                names = typ2["name"].reset_index().drop("index", axis=1)

                typ2 = typ2["value"].astype(int).reset_index().drop("index", axis=1)
                typ1 = typ1["value"].astype(int).reset_index().drop("index", axis=1)

                difference_values = typ1.subtract(typ2)

                return pd.concat((difference_values, names), axis=1)
             
             except:
                 raise Exception("Error creating diff chart")
             
        raise Exception("Invalid argument in surveys.create_typ_diff_chart()")

st.title("Surveys")

flows = completed_flow_values(load_data(study))
all_linking_codes = get_unique_linking_codes(study)

selectbox_uuid = 0
for fn in flows["flow_name"].drop_duplicates().sort_values().tolist():
    st.write(f"## {fn}")
    
    flow = flows[flows["flow_name"] == fn]
    flow = flow.drop_duplicates(["flow_id","name"]).sort_values(["date"])

    if fn == "end of day":
        selected_participant = st.selectbox(label="Participant to view", options=all_linking_codes, index=None)

        if selected_participant is not None:
            st.write(f"Showing data for: {selected_participant}")
            flow = flow[flow["linking_code"]==selected_participant]

            flow = flow[flow["name"]!="schedule_session"]

            emotions = flow[flow["name"]=="nightly_manageemotions"]
            thinkdiff = flow[flow["name"]=="nightly_thinkdifferently"]
            overall = flow[flow["name"]=="nightly_overall"]

            emotions = emotions[emotions["value"].notna()]
            thinkdiff = thinkdiff[thinkdiff["value"].notna()]
            overall = overall[overall["value"].notna()]
            
            # Combine all three metrics into one dataframe for scatter chart
            chart_data = pd.concat([emotions, thinkdiff, overall])
            chart_data = chart_data[["date", "value", "name"]].copy()
            chart_data["value"] = chart_data["value"].astype(int)

            print(chart_data)
            
            st.line_chart(data=chart_data, x="date", y="value", color="name")

        else:
            st.write("No participant selected")

    st.write(flow.pivot(index=["linking_code","flow_id","date"], columns="name", values="value"))

    if fn== "track your progress 3":
        st.write("## Charts")

        form = st.form("diff_chart_form")
        form.write("## Enter Difference Chart Selections")

        selected_participant = form.selectbox(label="Select a participant whose data you want to view", index=None, options=all_linking_codes, key=0)

        surveys_selections = form.multiselect(label="Select which two *track your progress* surveys you want to see data from", options=[1,2,3], default=[1,2], format_func=lambda x: f"track your progress {x}", max_selections=2)

        form.form_submit_button(label="Generate Chart")

        if selected_participant is None:
            form.error("No participant selected")

        elif len(surveys_selections) != 2:
            form.error("You must select two surveys to compare")
            
        else:
            if surveys_selections[0] > surveys_selections[1]: surveys_selections[0], surveys_selections[1] = surveys_selections[1], surveys_selections[0]

            chart_data = create_typ_diff_chart(flows, surveys_selections[1], surveys_selections[0], selected_participant)

            if chart_data.empty:
                st.error(f"No data found for either *track your progress {surveys_selections[0]}* or *track your progress {surveys_selections[1]}* for participant with linking code {selected_participant}")

            else:
                st.info(body="The chart is interactive! Try scrolling and dragging to adjust your view", icon=":material/info:")
                st.write(f"### Displaying chart for typ{surveys_selections[1]}-typ{surveys_selections[0]}")
                st.bar_chart(chart_data, x="name",y="value")    
