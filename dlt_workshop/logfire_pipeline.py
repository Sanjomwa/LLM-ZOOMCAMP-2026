"""dlt pipeline: Pydantic Logfire trace data -> DuckDB.

Homework Q2 (dlt_homework_materials/homework.md). Source: Logfire's
query API, `GET https://logfire-<region>.pydantic.dev/v1/query`, bearer
auth with a read token. Confirmed live via manual curl testing before
writing this pipeline (dltHub's Logfire context page
https://dlthub.com/context/source/logfire only gives a generic
RESTAPIConfig sketch, not real Logfire-specific values).

Not a standard rest_api_resources() pipeline: /v1/query returns data
column-oriented (`{"columns": [{"name", "datatype", "values": [...]}]}`
— parallel arrays sharing a row index), not the row-array shape
data_selector expects. So this reshapes columns -> row dicts in a plain
@dlt.resource generator instead of forcing it through RESTAPIConfig.

dataset_name is the literal "agent_traces" (not dev_mode-timestamped)
because the homework's own verification query targets that exact
schema name:
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'agent_traces';
"""

import dlt
import requests

BASE_URL = "https://logfire-us.pydantic.dev/v1/query"


@dlt.resource(name="records", write_disposition="replace")
def logfire_records(read_token: str = dlt.secrets.value):
    """All span records currently in the Logfire project.

    attributes (and the other JSON-typed columns) are passed through
    as nested dicts/lists, not flattened -- the point of this exercise
    is observing how many tables dlt's normalizer creates from that
    nesting (deeply nested LLM messages, tool calls, token usage).
    """
    response = requests.get(
        BASE_URL,
        params={"sql": "SELECT * FROM records"},
        headers={"Authorization": f"Bearer {read_token}"},
    )
    response.raise_for_status()
    columns = response.json()["columns"]

    row_count = len(columns[0]["values"]) if columns else 0
    for i in range(row_count):
        yield {col["name"]: col["values"][i] for col in columns}


def load() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="logfire",
        destination="duckdb",
        dataset_name="agent_traces",
    )
    load_info = pipeline.run(logfire_records())
    print(load_info)
    print(pipeline.last_trace.last_normalize_info)


if __name__ == "__main__":
    load()
