import json
import pandas as pd
import requests
import streamlit as st
import daft
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
accesstoken = credential.get_token("https://storage.azure.com/.default")

@st.cache_resource
def get_secret(name):
    client = SecretClient(vault_url="https://trailsvault.vault.azure.net/", credential=credential)
    return client.get_secret(name).value

@st.cache_data(ttl=100)
def check_access():
    if "token" not in st.session_state:
        token = st.query_params.get("token")
        st.session_state.token = token
    else:
        token = st.session_state.token
        
    if "study" not in st.session_state:
        study = st.query_params.get("study")
        st.session_state.study = study
    else:
        study = st.session_state.study
     
    if not token or not study:
        st.error("🚫 Unauthorized")
        st.stop()
        
        url = f"https://digital-trails.org/api/v2/roles?resource=study:{study}"
        headers = { "Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                st.error(f"Authentication failed: {response.status_code}")
                st.stop()

            data = response.json()

            roles = data.get("roles", [])
            if "admin" not in roles:
                st.error("Access Denied: Admin role required")
                st.stop()
            return True

        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"Error checking access: {str(e)}")
            st.stop()

@st.cache_data(ttl=300)
def load_data(study):
    df = daft.read_deltalake(
        "abfss://datums@trailsdata.dfs.core.windows.net",
        io_config=daft.io.IOConfig(
            azure=daft.io.AzureConfig(
                storage_account="trailsdata",
                bearer_token=accesstoken.token
            )
        )
    )
    df = df.where(df["study"] == study).to_pandas()
    df["pid"] = df["pid"].str[:10]
    df['date'] = pd.to_datetime(df['ts'], unit='s')
    df = df.merge(df.groupby("pid")["date"].min().reset_index().rename({"date":"start_date"}, axis=1))
    df['start_date'] = pd.to_datetime(df['start_date'].dt.date)
    df["rel_date"] = (df["date"] - df["start_date"])
    df["rel_day"] = df["rel_date"].dt.days
    df["data"] = df["data"].apply(json.loads)
    return df