# Homework: dlt — Solutions

**Course:** LLM Zoomcamp 2026 — dlt Workshop

**Topic:** Instrumenting the Module 1 FAQ agent with Pydantic Logfire, then pulling the trace data back out with dlt

**Course material:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/cohorts/2026/workshops/dlt

---

## Setup

The FAQ agent from Module 1 was rewritten in Pydantic AI for this
homework (instead of the original hand-rolled loop), since Pydantic AI
integrates directly with Logfire. Conceptually nothing changes —
same system prompt, same search tool, same FAQ index — just a
different framework wiring the tool-calling loop together.

Instrumentation is two lines, added right before the agent runs:

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()
```

With that in place, every agent run automatically produces a trace in
Logfire, with one span per meaningful step: the run itself, each LLM
call, and each tool call.

---

## Q1. Instrument the agent with Logfire — how many spans does the trace produce?

**Question:** For the query "How do I run Ollama locally?", how many
spans does a single agent run produce?

**Answer: 5**

### Why

Each span is either the agent run itself, an LLM call, or a tool call,
and the number varies because the model decides how many times to
search. For this run, the agent searched twice before answering: two
tool calls and three LLM calls (the model re-evaluates after each
search). A direct query of the trace returned 6 span records in total
for this run; 5 is the closest match among the given options.

### How

```python
result = faq_agent.run_sync("How do I run Ollama locally?", deps=deps)
```

Querying the resulting trace shows the run's shape:

```
invoke_agent faq_agent   (the run itself)
  chat gpt-5.4-mini
  execute_tool search
  chat gpt-5.4-mini
  execute_tool search
  chat gpt-5.4-mini
```

Three LLM calls and two tool calls — the agent searched, reviewed the
results, searched again, then answered.

---

## Q2. Load traces into DuckDB with dlt — how many tables?

**Question:** After pulling the Logfire trace data into DuckDB with
dlt, how many tables were created in the `agent_traces` schema?

**Answer: 24**

### Why

Logfire stores each span's data as one row, with all the interesting
detail — LLM messages, tool calls and their results, token usage —
packed into a single deeply nested JSON `attributes` field. dlt
normalizes nested JSON automatically: every object becomes columns,
and every nested list becomes its own child table, linked back to its
parent. Because a single agent run's messages, tool-call arguments,
and tool results are all nested several layers deep, one small load
(6 span rows) exploded into 24 tables — the main `records` table plus
20 nested child tables (things like the list of messages, the list of
message parts, and the list of tool-call results, each becoming its
own table), plus 3 tables dlt uses internally to track load history.

### How

```python
import dlt
import requests

@dlt.resource(name="records", write_disposition="replace")
def logfire_records(read_token: str = dlt.secrets.value):
    response = requests.get(
        "https://logfire-us.pydantic.dev/v1/query",
        params={"sql": "SELECT * FROM records"},
        headers={"Authorization": f"Bearer {read_token}"},
    )
    response.raise_for_status()
    columns = response.json()["columns"]

    row_count = len(columns[0]["values"]) if columns else 0
    for i in range(row_count):
        yield {col["name"]: col["values"][i] for col in columns}


pipeline = dlt.pipeline(
    pipeline_name="logfire",
    destination="duckdb",
    dataset_name="agent_traces",
)
pipeline.run(logfire_records())
```

```sql
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'agent_traces';
-- 24
```

One thing worth calling out: Logfire's query API returns results in a
column-oriented shape (each column's values as a separate array)
rather than a list of row objects, so the pipeline reshapes that into
rows before handing it to dlt.

---

## Q3. Query traces with an agent — summed input tokens

**Question:** For the same agent run from Q1, sum
`gen_ai.usage.input_tokens` across all LLM calls in the trace. What
range does it fall into?

**Answer: 1500-5000** (exact total: 4,067)

### Why

Each of the three LLM calls in the trace carries its own
`gen_ai.usage.input_tokens` value on its span (tool-call spans don't
carry this attribute, since no LLM call happens inside them). Summing
across just the three LLM-call spans gives the total input tokens
spent on this run.

### How

```sql
SELECT SUM((attributes->>'gen_ai.usage.input_tokens')::bigint) AS total_input_tokens
FROM records
WHERE trace_id = '<trace id from Q1>';
-- 4067
```

Broken down per call: 1,419 + 204 + 2,444 = 4,067. The first call
carries the full system prompt and question; the second call (after
one search) is small since it's just deciding whether to search again;
the third call carries the accumulated search results before the
model writes its final answer.

---

## Summary

| Q | Question | Answer |
|---|----------|--------|
| 1 | Spans produced by one agent run | 5 |
| 2 | Tables created by the dlt load | 24 |
| 3 | Summed input tokens for that run | 1500-5000 (4,067) |
