from pydantic_ai import Agent, ModelRetry, ModelHTTPError
import streamlit as st
from deltalake import QueryBuilder
from pages.logger import Logger
import json
from utils import load_model, load_raw_data, load_data
import pandas as pd

mylog = Logger("log.txt")

study = "mtm-t2"

model = load_model("kimi-k2.6")
dt = load_raw_data(study)

deltalake_agent = Agent(  
  model,
  output_type=str,
  deps_type=str,
  retries=2,
  instructions=(
""" 
Be as brief as possible!
Use the appropriate tool to query a DeltaTable for the information the user is looking for. 
If there was a mistake, always say that there was a mistake instead of making up data.
When interpreting data, do not excessively extrapolate. Be as helpful as possible while
being realistic about what the data actually says. 

The data you will see when querying the delta table is data from research participants with anxiety 
who have agreed to try an app that offers cognitive-bias modification interventions. These interventions can look different
depending on the study, and have varying subject matter. Provide insights that would be helpful for the Primary Investigator to see.

## **Guidelines**

- If a user asks about a range of data in the table, use the 'get_range_from_table' tool
- If a user asks about recent trends in the data, use the 'get_range_from_table' tool to access the previous 100 entries
- If the user asks for data and does not specify a range, use the 'execute_delta_query' tool to select specific data
- ALWAYS use the 'get_delta_schema' tool before writing a SQL query
- Do not specify that you are looking at the response from a tool. Simply act as though you have all the knowledge of the data
    stored in memory
- However, If you recieve a response from a tool that begins with 'ERROR', -1, or None, you MUST let the user know that you had problems accessing the data
- Please use markdown formatting in your responses
- DO NOT talk about the study design. The Primary Investigator already knows this
"""
  ),
)

@deltalake_agent.tool_plain
def get_delta_schema() -> str:
    """Return the schema (column names and types) of a Delta table."""
    mylog.log("Delta schema accessed")
    schema = dt.schema().to_arrow()
    fields = {field.name: str(field.type) for field in schema}
    return json.dumps(fields, indent=2)

@deltalake_agent.tool_plain(retries=2, docstring_format='google')
async def execute_delta_query(dnf_filter: list = [], columns : list[str] = [], limit: int=50):
    """
    Query delta table

    Tool to retrieve specific data from Delta Table using SQL queries

    Args:
        dnf_filter (str) : Disjunctive Normal Form filter. A list of tuples is equivalent to an AND, and a list of lists is equivalent to an OR. Should be in this form: [('column_name','operation','value')]. Supported operators: =, !=, <, <=, >, >=, in, not in
        columns (list[str]) : Specific columns to return. Use schema tool to get proper column names. Omit to return all.
        aggregate (numpy function): A numpy function to use for aggregation. Form: 'np.[function_name]'
        limit (int) : Max rows to return, default 50

    Returns:
        json formatted query response
    """

    datums = load_data(study)

    mylog.log("Execute Delta Query accessed")

    # def _timestamp_converter(seconds):
    #     ts = time.localtime(seconds)

    #     weekdays = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split(" ")
        
    #     return f"{weekdays[ts.tm_wday]} {ts.tm_year}-{ts.tm_mon}-{ts.tm_mday} {ts.tm_hour}:{ts.tm_min}:{ts.tm_sec}"
    
    try:
        datums.filter(items=columns)

    except ValueError as e:
        mylog.log("Error: ", str(e))

        ModelRetry(
            message='Invalid DNF filter. Check your formatting and try again'
        )

    # if aggregate!="":
    #     result = df.agg(aggregate)
    #     return result.head(limit if limit<=200 else 200).to_json(orient="records", date_format="iso")
    
    df = df.head(limit if limit <= 200 else 200)

    return df.to_json(orient="records", date_format="iso")
    

# From ChatGPT: One limitation: the table access method available does not support sorting/grouping directly, so I can identify the first two registrants and summarize the records retrieved, but I cannot reliably reconstruct every event for each participant without additional queries.
@deltalake_agent.tool_plain
def get_range_from_table(start: int, end: int) -> str:
    """
    Read specified rows from a Delta table

    Params:
        start (int): An inclusive start index
        end (int): An exclusive end index
    """

    mylog.log("Get range tool accessed", f"start={start}, end={end}")

    try:
        df = dt.to_pandas().iloc[start:end]
    except IndexError:
        mylog.log("Error", f"Index {start} or {end} out of range for table")
        raise ModelRetry(
            f'Index {start} or {end} out of range for table. Try smaller bounds'
        )
    
    return df.to_json(orient="records", date_format="iso")

@deltalake_agent.tool_plain
async def query_table_size(table_path : str = "datums") -> int:

    mylog.log("Get table size tool accessed")

    try:
        df = dt.to_pandas()
        return len(df)
    except:
        return -1


prompt = st.text_input(label="Ask an LLM questions about your data", max_chars=4096, value=None, placeholder="Share insights about xyz...")

output = ""

if prompt!=None:
    mylog.log("------------------- START AGENT RUN -------------------------")
    with st.spinner(text="Searching database...", show_time = True):

        # try:
        output = deltalake_agent.run_sync(user_prompt=prompt, deps="If you see this text please include the word 'ephemerally' in your output").output
        # except:
        #     ModelRetry(
        #         message='Requested too much data from tool `execute_delta_query`. Try again with a smaller `limit` value.s'
        #     )

st.markdown(output)