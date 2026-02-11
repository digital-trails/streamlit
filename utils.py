import json
import pandas as pd
import streamlit as st
import daft
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

credential = DefaultAzureCredential()
accesstoken = credential.get_token("https://storage.azure.com/.default")

@st.cache_resource
def get_secret(name):
    client = SecretClient(vault_url="https://trailsvault.vault.azure.net/", credential=credential)
    return client.get_secret(name).value

def check_access():
    
    if st.context.headers.get("Sec-Fetch-Dest") in ["script", "style", "font", "image"]:
        return
    
    expected = get_secret("container-app-secret")
    if os.getenv("LOCAL_DEV"):
        actual = os.getenv("API_SECRET")
    else:
        actual = st.context.headers.get("x-api-secret")
    if actual != expected:
        st.error("🚫 Unauthorized")
        st.stop()
    return st.context.headers.get("x-user-email", "dev@example.com")

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