import altair as alt
import streamlit as st
import pandas as pd
from auth import check_access_admin_only
from utils import load_datums, completed_flow_values, consents_as_events, invites_as_events

check_access_admin_only()

study = st.session_state.get("study")
datums = load_datums(study)

st.title("Events")

if datums is None or datums.empty:
    st.text("No data is available")

else:
    flows = completed_flow_values(datums, only_completed=False)
    flows = flows[["flow_name","flow_id","linking_code","date"]].drop_duplicates().reset_index()
    flows = flows.rename(columns={"flow_name": "event"})[["event","linking_code","date"]]

    consents = consents_as_events(datums)
    invites = invites_as_events(datums)
    events = pd.concat([flows, consents, invites])
    
    legend_sel = alt.selection_point(fields=["event"], bind="legend")

    chart = (
        alt.Chart(events)
        .mark_circle(size=100)
        .encode(
            x="date:T",
            y=alt.Y("linking_code:O", axis=alt.Axis(grid=True)),
            color=alt.Color(
                "event:N",
                legend=alt.Legend(orient="bottom", columns=5, title="event"),
            ),
            opacity=alt.condition(legend_sel, alt.value(0.9), alt.value(0.1)),
            tooltip=["date:T", "linking_code:Q", "event:N"],
        )
        .add_params(legend_sel)
        .properties(height=alt.Step(18))
        .interactive()  # pan + zoom on the data area
    )

    
    st.altair_chart(chart, width="stretch")
