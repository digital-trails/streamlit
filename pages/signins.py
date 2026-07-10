import streamlit as st
from auth import check_access_admin_only
from utils import load_datums, to_local_naive

check_access_admin_only()

study = st.session_state.get("study")
datums = load_datums(study)

signins = datums[datums["type"] == "Signed-in"].copy()

st.title("Sign-ins")

if signins.empty:
    st.info("No sign-in events found for this study.")
    st.stop()

signins["date"] = signins.apply(lambda r: to_local_naive(r["date"], r["tz"]), axis=1)
signins["consented"] = signins["data"].apply(lambda d: (d or {}).get("Consented"))

table = (
    signins[["linking_code", "date", "consented"]]
    .sort_values("date", ascending=False)
    .reset_index(drop=True)
)

st.write(table)
