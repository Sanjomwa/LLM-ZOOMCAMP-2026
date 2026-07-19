"""dlt REST API pipeline: Claude Code Agent Logs API -> DuckDB.

Source: https://test-agent-traces-api-xt2e7ottma-ew.a.run.app
Endpoint: GET /logs — offset/limit pagination (max limit=1000/request),
records under `logs`, response envelope carries `total` (1,000,000). No auth.

Capped at 20,000 rows via maximum_offset, per the workshop's lesson 4
instruction ("load 20k logs into DuckDB") rather than a full 1M-row load.
"""

import dlt
from dlt.hub import run
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources

BASE_URL = "https://test-agent-traces-api-xt2e7ottma-ew.a.run.app"


@dlt.source(name="agent_logs_api")
def agent_logs_source(base_url: str = dlt.config.value, page_size: int = 1000):
    """Claude Code Agent Logs API.

    Args:
        base_url: API base URL. Auto-loaded from config.toml ([sources.agent_logs_api]).
        page_size: records per page for the offset paginator (API max: 1000).
    """
    config: RESTAPIConfig = {
        "client": {
            "base_url": base_url,
            "paginator": {
                "type": "offset",
                "limit": page_size,
                "offset": 0,
                "limit_param": "limit",
                "offset_param": "offset",
                "total_path": "total",  # read total record count from the envelope
                "maximum_offset": 20000,  # cap the load at 20k rows
            },
        },
        "resource_defaults": {
            "write_disposition": "replace",
        },
        "resources": [
            {
                "name": "logs",
                "endpoint": {
                    "path": "/logs",
                    "data_selector": "logs",  # records live under the "logs" key
                },
                "primary_key": "index",
            },
        ],
    }
    yield from rest_api_resources(config)


@run.pipeline("agent_traces")
def ingest_agent_traces() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="agent_traces",
        destination="playground",  # managed S3 lake — persists across runtime jobs
        dataset_name="traces",  # persistent dataset (distinct from catalog name)
    )
    source = agent_logs_source(base_url=BASE_URL)
    info = pipeline.run(source)
    print(info)
    print(pipeline.last_trace.last_normalize_info)


if __name__ == "__main__":
    ingest_agent_traces()
