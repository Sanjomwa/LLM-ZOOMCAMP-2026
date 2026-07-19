"""dlt filesystem pipeline: load Claude Code JSONL session logs into DuckDB."""

import dlt
from dlt.sources.filesystem import filesystem, read_jsonl


def load_sessions() -> None:
    """Load Claude Code session logs from ~/.claude/projects into DuckDB.

    bucket_url is read from .dlt/config.toml under [sources.filesystem].
    file_glob is set inline so it lives next to the code that depends on it.
    """
    pipeline = dlt.pipeline(
        pipeline_name="claude_logs_pipeline",
        destination="duckdb",
        dataset_name="claude_logs",
        dev_mode=True,  # fresh dataset on every run during dev
    )

    reader = (filesystem(file_glob="**/*.jsonl") | read_jsonl()).with_name("sessions")

    # Schema cleanup: attachment/tool_use_result/tool-call input are deeply
    # nested and low-value for a usage dashboard (file diffs, tool payloads).
    # Keep them as single JSON columns instead of exploding into ~16 child
    # tables of file-diff lines and tool-call option arrays.
    reader.apply_hints(
        columns={
            "attachment": {"data_type": "json"},
            "tool_use_result": {"data_type": "json"},
            "message__content__input": {"data_type": "json"},
        }
    )

    load_info = pipeline.run(reader, write_disposition="replace")
    print(load_info)
    print(pipeline.last_trace.last_normalize_info)


if __name__ == "__main__":
    load_sessions()
