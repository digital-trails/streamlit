import streamlit as st
from dotenv import load_dotenv

load_dotenv('keys.env')

def get_study():
    return st.query_params.get("study") or st.session_state.get("study")

def study_pages(study):
    if study == "mtm":
        yield st.Page("pages/mtm/safety.py", title="Safety")
        yield st.Page("pages/mtm/compliance.py", title="Compliance")
    if study == "test":
        yield st.Page("pages/test/oura.py", title="Oura Health Data")

st.set_page_config(page_title="Trails Dashboard", layout="wide")

pages = [
    st.Page("pages/events.py", title="Events"),
    st.Page("pages/surveys.py", title="Surveys"),
    *study_pages(get_study()),
    st.Page("pages/agent.py", title="Agent")
]

pg = st.navigation(pages, position="top")

if __name__ == "__main__":
    pg.run()
    print("server running")