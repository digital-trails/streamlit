# utils.py
import json
import pandas as pd
import streamlit as st
from deltalake import DeltaTable
from azure.identity import DefaultAzureCredential


@st.cache_data(ttl=300)
def load_data(study: str) -> pd.DataFrame:
    credential = DefaultAzureCredential()
    accesstoken = credential.get_token("https://storage.azure.com/.default")
    storage_options = {"ACCOUNT_NAME": "trailsdata", "BEARER_TOKEN": accesstoken.token}
    dt = DeltaTable(f"abfs://datums", storage_options=storage_options)
    df = dt.to_pandas(partitions=[("study","=",study)])

    df["date"] = pd.to_datetime(df["ts"], unit="s", errors="coerce")

    # I don't think we need this for now.
    # starts = df.groupby("pid", as_index=False)["date"].min().rename(columns={"date": "start_date"})
    # df = df.merge(starts, on="pid", how="left")
    # df["start_date"] = pd.to_datetime(df["start_date"].dt.date, errors="coerce")
    # df["rel_date"] = df["date"] - df["start_date"]
    # df["rel_day"] = df["rel_date"].dt.days

    def _parse(x):
        if isinstance(x, (dict, list)):
            return x
        try:
            return json.loads(x)
        except Exception:
            return None
    
    df["data"] = df["data"].apply(_parse)

    linking_codes = df[df["type"] == "Link"]
    linking_codes = { r.pid:r.data["Code"] for r in linking_codes.itertuples(index=False) }
    df["linking_code"] = [ f'{linking_codes.get(r.pid,r.pid[:10])}'.zfill(3) for r in df.itertuples() ]

    if study == "mtm":
        dep_names = [f"neuroqol_dep_{i}" for i in range(1,9)]
        anx_names = [f"neuroqol_anx_{i}" for i in range(1,9)]
        qol_names = set(dep_names+anx_names)

        for _,row in df.iterrows():
            if row["data"] and row["data"].get("name") in qol_names:
                if row["data"]["value"] is not None:
                    row["data"]["value"] = str(int(row["data"]["value"]) + 1)

    return df

def completed_flow_values(df: pd.DataFrame, only_completed: bool = True, only_named: bool = True, drop_meta: bool = True):
    flows = df[df["type"] == "Flow"].copy()
    flows["flow_id"] = flows["data"].apply(lambda d: d.get("flow_id"))

    if only_completed:
        flow_endings = flows[flows["data"].apply(lambda d: d.get("name") == "$Ending")].copy()
        completed_flowids = flow_endings["flow_id"][flow_endings["data"].apply(lambda d: d["value"]) == "Completion"]
        flows = flows[flows["flow_id"].isin(completed_flowids)]

    flow_names = flows[flows["data"].apply(lambda d: d.get("name") == "$RootPath")].copy()
    flow_names["flow_name"] = flow_names["data"].apply(lambda d: d["value"][d["value"][:-1].rfind("/")+1:].strip("/").replace(".json",""))
    flow_names["date"] = pd.to_datetime(flow_names['ts'],unit='s').dt.date

    flows = flows.merge(flow_names[["flow_id","flow_name"]], on = "flow_id")

    flows["name"]  = flows["data"].apply(lambda d: d.get("name"))
    flows["value"] = flows["data"].apply(lambda d: d.get("value"))

    flows = flows.drop(["data"],axis=1)

    if only_named:
        flows = flows[~flows["name"].isnull()]

    if drop_meta:
        flows = flows[~flows["name"].str.startswith("$")]

    return flows[(~flows["name"].isnull())] if only_named else flows

def consents_as_flows(df: pd.DataFrame):
    df2 = df[df["type"]=="Consent"].copy()
    df2["flow_name"] = "consent"
    return df2[["flow_name","linking_code","date"]]

def to_local_naive(dt, offset_str):
    from datetime import timezone, timedelta
    if not offset_str: return dt
    sign = 1 if offset_str[0] == '+' else -1
    h, m = map(int, offset_str[1:].split(':'))
    tz = timezone(timedelta(hours=sign * h, minutes=sign * m))
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)