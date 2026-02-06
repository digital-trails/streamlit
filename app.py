import json
import pandas as pd
import streamlit as st
import json
import daft;
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
accesstoken = credential.get_token("https://storage.azure.com/.default")

df = daft.read_deltalake(
   "abfss://datums@trailsdata.dfs.core.windows.net",
    io_config=daft.io.IOConfig(
        azure=daft.io.AzureConfig(
            storage_account="trailsdata",
            bearer_token=accesstoken.token
        )
    )
)

df = df.where(df["study"]=="mtm").to_pandas()

df["pid"]  = df["pid"].str[:10]
df['date'] = pd.to_datetime(df['ts'],unit='s')

df = df.merge(df.groupby("pid")["date"].min().reset_index().rename({"date":"start_date"},axis=1))

df['start_date'] = pd.to_datetime(df['start_date'].dt.date)
df["rel_date"] = (df["date"] - df["start_date"])
df["rel_day"] = df["rel_date"].dt.days

df["data"] = df["data"].apply(json.loads)

flows = df[(df["type"]=="Flow")].reset_index(drop=True).copy()
flows["flow_id"] = flows["data"].apply(lambda d: d.get("flow_id"))

flow_names = flows[flows["data"].apply(lambda d: d.get("name") == "$RootPath")].copy()
flow_names["flow_name"] = flow_names["data"].apply(lambda d: d["value"][d["value"][:-1].rfind("/")+1:].strip("/").replace(".json",""))
flow_names = flow_names[["flow_id","pid","date","flow_name"]]

flows = pd.merge(flows,flow_names)

flow_values = flows[flows["data"].apply(lambda d: d.get("type") != "metadata" and d.get("name") != None)].copy()
flow_values["name"] = flow_values["data"].apply(lambda d: d["name"])
flow_values["value"] = flow_values["data"].apply(lambda d: d["value"])
flow_values = flow_values[["flow_id","flow_name","name","value"]]

st.set_page_config(layout="wide")

with st.container():

    st.write("## All Events")
    st.scatter_chart(flow_names[["date","pid","flow_name"]], x="date", y="pid", color="flow_name")

    # flow_values.drop_duplicates(["flow_id","name"])
    # for fn in flow_values["flow_name"].drop_duplicates().tolist():
    #     st.write(f"## {fn}")
    #     specific_flow_values = flow_values[flow_values["flow_name"] == fn]
    #     specific_flow_values = specific_flow_values.drop_duplicates(["flow_id","name"])
    #     st.write(specific_flow_values.pivot(index=["flow_id"],columns="name",values="value"))
