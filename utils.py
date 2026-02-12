# utils.py
import json
import pandas as pd
import streamlit as st
import daft
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
accesstoken = credential.get_token("https://storage.azure.com/.default")

@st.cache_data(ttl=300)
def load_data(study: str):
    df = daft.read_deltalake(
        "abfss://datums@trailsdata.dfs.core.windows.net",
        io_config=daft.io.IOConfig(
            azure=daft.io.AzureConfig(
                storage_account="trailsdata",
                bearer_token=accesstoken.token,
            )
        ),
    )
    df = df.where(df["study"] == study).to_pandas()

    df["pid"] = df["pid"].astype(str).str[:10]
    df["date"] = pd.to_datetime(df["ts"], unit="s", errors="coerce")

    starts = (
        df.groupby("pid", as_index=False)["date"]
        .min()
        .rename(columns={"date": "start_date"})
    )
    df = df.merge(starts, on="pid", how="left")
    df["start_date"] = pd.to_datetime(df["start_date"].dt.date, errors="coerce")
    df["rel_date"] = df["date"] - df["start_date"]
    df["rel_day"] = df["rel_date"].dt.days

    def _parse(x):
        if isinstance(x, (dict, list)):
            return x
        try:
            return json.loads(x)
        except Exception:
            return None
    df["data"] = df["data"].apply(_parse)

    return df