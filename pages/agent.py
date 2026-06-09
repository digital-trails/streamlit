from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
import streamlit as st
from deltalake import DeltaTable, QueryBuilder
from pages.logger import Logger
import json

mylog = Logger("log.txt")

model = OllamaModel(
    'qwen3.5:9b', 
    provider = OllamaProvider(base_url='http://localhost:11434/v1'),
    settings = {
        "thinking" : True,
        "max_tokens" : 1000000
    }
)

from pydantic_ai import Agent

deltalake_agent = Agent(  
  model,
  output_type=str,
  deps_type=str,
  retries=2,
  instructions=(
""" 
Use the appropriate tool to query a DeltaTable for the information the user is looking for. 
If there was a mistake, always say that there was a mistake instead of making up data.
When interpreting data, do not excessively extrapolate. Be as helpful as possible while
being realistic about what the data actually says. 

The data you will see when querying the delta table is data from research participants with anxiety 
who have agreed to try an app that offers cognitive-bias modification interventions. These interventions can look different
depending on the study, and have varying subject matter. Since you understand the context of the data, provide 
insights that would be helpful for the Primary Investigator to see, instead of simple descriptions of the exact contents of the data.

## **Guidelines**

- If a user asks about a range of data in the table, use the 'get_range_from_table' tool
- If a user asks about recent trends in the data, use the 'get_range_from_table' tool to access the previous 100 entries
- If the user asks for data and does not specify a range, use the 'query_table' tool to write a custom SQL query to select the 
    relevant data for the user
- ALWAYS use the 'get_delta_schema' tool before writing a SQL query
- Do not specify that you are looking at the response from a tool. Simply act as though you have all the knowledge of the data
    stored in memory
- However, If you recieve a response from a tool that begins with 'ERROR', -1, or None, you MUST let the user know that you had problems accessing the data
- You may use markdown formatting in your responses, but **YOU MUST BE AS BRIEF AS POSSIBLE**
"""
  ),
)


# @deltalake_agent.tool
# async def roulette_wheel(ctx: RunContext[int], square: int) -> str:  
#   """check if the square is a winner"""
#   return 'winner' if square == ctx.deps else 'loser'

@deltalake_agent.tool_plain()
def get_delta_schema() -> str:
    """Return the schema (column names and types) of a Delta table."""
    mylog.log("Delta schema accessed")
    dt = DeltaTable("datums")
    schema = dt.schema().to_arrow()
    fields = {field.name: str(field.type) for field in schema}
    return json.dumps(fields, indent=2)

@deltalake_agent.tool_plain(retries=2)
async def query_table(what: str = '*', modifiers: str = "") -> str:
    """
    Call custom queries on the Delta Table to gather specific information. DO NOT generate a full SQL query.
    The query will be passed on in the form "SELECT {what} FROM deltatable {modifiers}", where {what} and {modifiers} are the parameters to this tool. DO NOT INCLUDE 'SELECT' or 'FROM deltatable' IN THE PARAMETERS
    
    Parameters:
    what (str): Which columns from the DeltaTable to select. Must reference the schema properly using the `get_delta_schema` tool if 
        needed. Defaults to '*'. Only use the names of schema columns here. All WHERE, ORDER, LIMIT, IN, etc. statements should be entered into the `modifiers` parameter

    modifiers (str): Optional SQL modifiers. Can be anything that's necessary for the query, including but not limited to "WHERE", "ORDER", "LIMIT", and any syntactically-valid SQL code.
    """

    SQLquery = f"SELECT {what} FROM deltatable {modifiers}"

    dt = DeltaTable("datums")

    try:
        mylog.log("SQL Query generated", SQLquery)
        data = QueryBuilder().register('deltatable', dt).execute(SQLquery).read_all()
        json_string = json.dumps(data.to_struct_array().to_pylist())
    except Exception as e:
        mylog.log("SQL query failed", SQLquery)
        mylog.log("Error", str(e))
        raise ModelRetry(
            f'Invalid SQL Query. Please fix any syntax errors and try again. Double-check the schema and consider using the "LIKE" in your WHERE statments. Remember that you do cannot include FROM in your parameters--it will be added for you.'
        )

    return json_string
    

@deltalake_agent.tool_plain
def get_range_from_table(start: int, end: int) -> str:
    """
    Read specified rows from a Delta table at the given path.
    Works with local paths and cloud URIs (s3://, abfs://, gs://).
    Default path is ./datums
    Parameters
    start (int): An inclusive start index
    end (int): An exclusive end index
    """

    dt = DeltaTable("datums")
    mylog.log("Get range tool accssed", f"start={start}, end={end}")
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
    dt = DeltaTable(table_path)

    try:
        df = dt.to_pandas()
        return len(df)
    except:
        return -1


prompt = st.text_input(label="Ask an LLM questions about your data", max_chars=4096, value=None, placeholder="Share insights about xyz...")
output = ""

if prompt is not None:
    output = deltalake_agent.run_sync(user_prompt=prompt).output

st.markdown(output)