from pydantic import BaseModel, Field, field_validator

class ExecuteDeltaQueryParams(BaseModel):
    sql : str = Field(
        description=
            "A SQL SELECT statement. Reference the table as 'tbl'. "
            "Always prefer aggregation (COUNT, SUM, AVG, MIN, MAX, GROUP BY) "
            "over fetching raw rows. Example: "
            "'SELECT region, COUNT(*) as n, AVG(score) as avg_score FROM tbl "
            "WHERE status = \\'active\\' GROUP BY region'"
            "Always access the schema tool first to avoid errors"
    )

    limit: int = Field(
        default=50,
        le=200,
        description="Max rows returned. Defaults to 50, hard cap at 200."
    )

    @field_validator("sql")
    @classmethod
    def must_be_select(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized.startswith("SELECT"):
            raise ValueError("Only SELECT statements are permitted.")
        forbidden = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"}
        if any(kw in normalized for kw in forbidden):
            raise ValueError(f"SQL contains a forbidden keyword.")
        return v
