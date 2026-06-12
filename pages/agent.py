from pydantic_ai import Agent, ModelRetry, ModelHTTPError, RunContext, UsageLimits
import streamlit as st
from deltalake import QueryBuilder
from pages.logger import Logger
import json
from utils import load_model, load_raw_data, load_data
import pandas as pd
import pages.tool_params
import duckdb
import asyncio

prompt = st.text_input(label="Ask an LLM questions about your data", max_chars=4096, value=None, placeholder="Share insights about xyz...")
output_box = st.empty()

model_name="kimi-k2.6"

mylog = Logger("log.txt", model=model_name)

study = "mtm-t2"

model = load_model(model_name)
dt = load_raw_data(study)

deltalake_agent = Agent(  
  model,
  output_type=str,
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
- ALWAYS use the 'get_delta_schema' tool before writing a query
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

@deltalake_agent.tool_plain()
async def execute_sql_query(params: pages.tool_params.ExecuteDeltaQueryParams) -> str:
    """
    Executes a SQL query against a delta table via DuckDB and returns
    a compact JSON string safe to pass back as a tool result.
    """

    mylog.log("SQL Query Tool Accessed", f"query: {params.sql}")

    dataset = dt.to_pyarrow_dataset()

    # Inject the delta table as 'tbl' and enforce the row limit
    wrapped_sql = f"""
        WITH tbl AS (
            SELECT * FROM dataset
        )
        SELECT * FROM ({params.sql}) AS _query
        LIMIT {params.limit}
    """
    

    try:
        con = duckdb.connect()
        df: pd.DataFrame = con.execute(wrapped_sql).df()

    except duckdb.Error as e:
        mylog.log("Error: ", f"{str(e)}. Query was: {params.sql}")
        return json.dumps({"error": str(e)})
    
    finally:
        con.close()

    if df.empty:
        return "Empty dataframe"

    return df.to_json(
        orient="records",
        date_format="iso",
        double_precision=4,
    )


@deltalake_agent.tool_plain(retries=5)
def get_range_from_table(start: int, end: int) -> str:
    """
    Read specified rows from a Delta table. Difference between start and end cannot exceed 500

    Params:
        start (int): An inclusive start index
        end (int): An exclusive end index
    """

    mylog.log("Get range tool accessed", f"start={start}, end={end}")

    if(end-start>500):
        raise ModelRetry(f"Difference between start and end index cannot excceed 500, but {end}-{start}={end-start}")

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



async def run_agent(prompt: str):
  async with deltalake_agent.run_stream(user_prompt=prompt) as result:  
      async for message in result.stream_text():  
          output_box.markdown(message)

if prompt!=None:
    mylog.log("------------------- START AGENT RUN -------------------------")
    with st.spinner(text="Working...", show_time = True):

        # try:
        output = asyncio.run(run_agent(prompt=prompt))
        # except:
        #     ModelRetry(
        #         message='Requested too much data from tool `execute_delta_query`. Try again with a smaller `limit` value.s'
        #     )



