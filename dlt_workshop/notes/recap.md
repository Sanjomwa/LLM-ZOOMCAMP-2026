# dlt Workshop — Recap (Stage 6 / Lesson 7)

Built from the real lesson file
(`cohorts/2026/workshops/dlt/lessons/07-where-to-go.md`, fetched and
read in full 2026-07-19) plus what was actually built in *this* repo
across Stages 0–5. No build happens in this stage — it's the
conceptual wrap-up, same as the lesson.

**Status: workshop complete.** See `PROGRESS.md` for the authoritative
stage-by-stage record; this file is the "what it all meant" companion.

---

## What we actually built, end to end

| Artifact | Stage | Purpose |
|---|---|---|
| `filesystem_pipeline.py` | 1–2 | Local Claude Code JSONL logs (`~/.claude/projects/**/*.jsonl`) → DuckDB, schema-cleaned from 23 tables to 9 |
| `claude_logs_pipeline_dashboard.py` | 2 | 4-chart marimo usage report (activity over time, message types, token usage by model, top projects) |
| `rest_api_pipeline.py` | 3–5 | `agent_traces` — REST API (`/logs` endpoint, offset pagination, `maximum_offset: 20000`) → DuckDB, then → `playground` S3 lake |
| `agent_traces_dashboard.py` | 3, 5 | 6-chart marimo report, deployed as an interactive job, published then unpublished |
| `__deployment__.py` | 4–5 | Deployment manifest — both jobs registered, no lingering cron schedule |

Every pipeline was described in plain English to the agent; the router
skill resolved the matching toolkit (`filesystem-pipeline`,
`rest-api-pipeline`, `data-exploration`, `dlthub-platform`) on demand —
none of them existed in the project until the conversation actually
needed them. This matches the lesson's own framing exactly: you didn't
hand-write dlt pipelines, you described the goal and the workbench's
toolkits/skills/MCP tools handled the dlt-specific knowledge.

## Incremental loading — deliberately deferred

Both pipelines use `write_disposition="replace"` — full reload every
run. That's fine at this scale, not once there's real volume. dlt's
fix: track the last-loaded cursor value in pipeline state and filter
on it next run.

**Filesystem pipeline** — filter by file modification date:
```python
files = filesystem(
    bucket_url="...",
    file_glob="...",
    incremental=dlt.sources.incremental("modification_date"),
)
```

**REST API pipeline** — filter by the sequential `index`:
```python
"resources": [
    {
        "name": "logs",
        "endpoint": {"path": "/logs", "data_selector": "logs"},
        "primary_key": "index",
        "incremental": dlt.sources.incremental("index"),
    },
]
```

Then switch `write_disposition` to `"merge"` so existing rows update
and new rows insert, without dropping anything.

**One nuance specific to this repo:** the lesson pairs this with
"remove `dev_mode`" — but `dev_mode=True` was already dropped from
`rest_api_pipeline.py`'s deployed function back in Stage 4, out of
necessity (a fresh timestamped dataset every cloud run would have
broken the dashboard's ability to attach to a stable dataset). So only
the actual cursor/merge half of this exercise is still open here, not
the full thing the generic lesson text describes.

## Other sources and destinations (named, not built)

dlt ships other built-in sources beyond `filesystem` and `rest_api`:
`sql_database` (incremental from Postgres/MySQL/etc.), `google_sheets`,
`notion`, and vendor-specific ones (`hubspot`, `salesforce`, `stripe`)
with auth handled for you. Workflow is always the same: configure the
source, create a pipeline, run it.

The same pipeline code also works against Postgres, BigQuery,
Snowflake, or Redshift — only the destination string and credentials
change. This is mental model #6 (`00_mental_models.md`) applied
generally, not just to the `duckdb`/`playground` swap we actually did.

## Key concepts, and where they showed up here

- **Toolkits** — filesystem, rest-api, data-exploration,
  dlthub-platform — each installed on demand, each a guided workflow
- **MCP tools** — inspecting pipelines/schemas/row counts/previews;
  fell back to the Python path (`dlt.attach`) each time since the MCP
  server needed a session restart we didn't take
- **dlt normalization** — nested JSON → typed tables + child tables
  (23→9 tables after schema cleanup on the local-logs pipeline; the
  REST API pipeline stayed flat, only 2 tables, no cleanup needed)
- **REST API source** — offset pagination, `data_selector`,
  `maximum_offset`
- **Named destinations** — `playground` is DuckDB-shaped for dev,
  S3-backed for prod, one code path (mental model #7: it's about
  *where the bytes live*, not what the engine can do)
- **marimo** — reactive notebooks, SQL-first data cells paired with
  altair chart cells, `run mode` (shared, code hidden) vs `edit mode`
  (local, editable)
- **Scheduling and triggers** — cron `trigger.schedule(...)` declared
  on the `@run.pipeline(...)` decorator; demonstrated working, then
  deliberately removed before the session ended (course-only workspace
  — see the `dlt-workshop-no-lingering-cron` memory)

## Where the lesson text and reality diverged

Worth recording explicitly, since it's the main repeatable lesson from
actually doing this hands-on rather than just reading the material —
verifying against live sources caught all three:

1. **Stage 3** — the workshop notes had left the fake test API's URL
   as a placeholder (`[fake test API]`). Pulled the real URL and
   reference code from the course repo, cross-checked live against the
   API's own `/openapi.json` before writing any pipeline code.
2. **Stage 5** — lesson 6's own `dlt.attach(...)` example uses dataset
   name `agent_logs`; our pipeline actually writes to `traces`
   (confirmed from Stage 4's run output). Used the real name, not the
   lesson's.
3. **Stage 5** — lesson 6's literal `__deployment__.py` import pattern
   (`from agent_traces_dashboard import app as agent_traces_dashboard`)
   triggered a real deploy-tooling bug: the deploy scanner treated the
   *entire* `__deployment__` module as one marimo job and silently
   dropped the pipeline job. Caught it via `dlthub deploy
   --show-manifest`; fixed by switching to the `prepare-deployment`
   skill's own convention (`import agent_traces_dashboard`, the
   module, not the app object).

None of these were hard to fix once noticed — the point is that
"noticed" required checking the actual manifest/API/data rather than
trusting the written lesson material as-is.

## To learn more

- [dlt documentation](https://dlthub.com/docs) — the full reference
- [dltHub AI workbench](https://dlthub.com/docs/dlt-ecosystem/llm-tooling/llm-native-workflow) — toolkits, skills, the MCP server
- [Deploy and schedule on the runtime](https://dlthub.com/docs/hub/getting-started/runtime-tutorial) — jobs, schedules, triggers
- [marimo documentation](https://docs.marimo.io) — reactive notebooks
- [Altair encodings](https://altair-viz.github.io/user_guide/encodings/channels.html)

## What's next

The workshop stages (0–6) are done. The **homework** track
(`dlt_homework_materials/homework_notes.md`) is separate and still not
started — it continues Module 1's FAQ agent with Pydantic Logfire
instrumentation, then a dlt pipeline pulling the traces back out. See
mental model #8 (`00_mental_models.md`) for how it connects back to
Module 5's OpenTelemetry work.
