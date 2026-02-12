import requests
import streamlit as st

ROLES_API = "https://digital-trails.org/api/v2/roles?resource=study:{study}"

@st.cache_data(ttl=300)
def fetch_roles(study: str, token: str) -> list[str]:
    url = ROLES_API.format(study=study)
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Authentication failed: {resp.status_code}")

    data = resp.json()
    return data.get("roles", [])


def ensure_session_auth() -> tuple[str, str]:
    qp = st.query_params
    qp_token = qp.get("token")
    qp_study = qp.get("study")

    if ("token" not in st.session_state) or (qp_token and st.session_state.get("token") != qp_token):
        st.session_state["token"] = qp_token

    if ("study" not in st.session_state) or (qp_study and st.session_state.get("study") != qp_study):
        st.session_state["study"] = qp_study

    token = st.session_state.get("token")
    study = st.session_state.get("study")

    if not token or not study:
        st.error("🚫 Unauthorized: missing token or study.")
        st.stop()

    return study, token


def check_access_admin_only() -> bool:
    study, token = ensure_session_auth()

    try:
        roles = fetch_roles(study, token)
    except Exception as e:
        st.error(str(e))
        st.stop()

    if "admin" not in roles:
        st.error("Access Denied: Admin role required.")
        st.stop()

    return True