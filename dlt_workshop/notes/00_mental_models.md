# dlt Workshop — Mental Models

Built from the real lesson files (`cohorts/2026/workshops/dlt/lessons/01-07`)
and the workshop video transcript. Read this before touching code —
per the standing rule for this workspace, understanding first.

---

## 1. The data already exists — the problem is the format, not missing observability

Every coding agent you already use (Claude Code, Codex, Copilot) writes
full session metadata to disk right now: token counts, model names,
tool calls, one JSON object per line in `~/.claude/projects/*.jsonl`.
Nothing needs to be instrumented from scratch to get this data — lesson
1 is explicit that the workshop's starting point is "valuable data
trapped in an awkward nested format," not an absence of data. This
reframes the whole first half: the task is *structuring* existing
data, not *generating* new telemetry.

## 2. The agent-driven pipeline loop is a skill/toolkit resolution loop, not code-writing-by-hand

You describe a goal in plain English ("build a dlt pipeline, load data
from local Claude logs into DuckDB"). A router skill — the only thing
installed when the workspace is first scaffolded — inspects what you're
asking for and installs the matching toolkit **on demand**: a
filesystem source gets the filesystem-pipeline toolkit, a URL gets the
rest-api-pipeline toolkit, deployment gets the dlthub-platform toolkit.
None of these toolkits exist in the project until the conversation
actually needs them. This "resolve capability on demand from a router"
pattern is transferable to any agent-tooling ecosystem, not specific
to dlt.

## 3. Skills teach *how*; MCP tools provide pre-built, deterministic *what*

A **skill** is a markdown document of process knowledge — it tells the
agent what steps to take and in what order (confirm the plan, scaffold,
configure credentials, run). An **MCP tool** is actual reusable code
the agent calls instead of regenerating boilerplate from scratch every
time — read a table, count rows, preview a schema. The reasoning for
splitting them this way: repetitive, well-solved code shouldn't be
reinvented (and possibly hallucinated) by the agent on every request;
it should be a deterministic function call. Skills handle judgment and
sequencing; tools handle repetition.

## 4. Debugging a pipeline and validating its data are two different jobs — only one is automatable

The debug-pipeline skill can confirm a pipeline runs without erroring,
and it can even self-correct real problems (the 78→40 table
schema-pollution fix happened during an explicit "debug my pipeline"
step). But lesson 3 is direct about the boundary: debugging "can't tell
you whether the data is correct. That's a judgment only you can make by
looking at the output." Automated debugging is a necessary but
insufficient check — human review of the actual data stays mandatory
no matter how good the tooling gets.

## 5. Many tables from nested JSON is correct dlt behavior, not a bug

dlt normalizes on load: it infers types, flattens nested objects, and
creates a **child table per nested array**, linked back to the parent
via `_dlt_id`/`_dlt_parent_id`. Heavily nested agent logs produced 78
tables on the first run — genuinely correct behavior given the input
shape, not something to "fix" as an error. The actual lever you pull
(schema pollution control — marking some columns as JSON type instead
of unnesting them) is a **scope decision** about how deep you want
structure to go, made explicitly and after debugging confirmed the
pipeline itself was already working.

## 6. One pipeline, many destinations — only a string changes

`destination="duckdb"` vs. `destination="playground"` (or Postgres,
BigQuery, Snowflake, LanceDB) is the entire difference between a
disposable local dev pipeline and a production one — same pipeline
code, same source config, same `pipeline.run()` call. This is the same
shape as Module 5's span-exporter swap (`ConsoleSpanExporter` →
`SQLiteSpanExporter`, same processor wiring, different destination) —
one layer up the stack, applied to whole tables instead of individual
spans.

## 7. Ephemeral vs. persistent storage is where the file lives, not what the engine can do

DuckDB itself is a perfectly capable analytical database. The reason
`destination="duckdb"` loses its data after a cloud deployment finishes
isn't a DuckDB limitation — it's that the `.duckdb` file sits inside a
container's throwaway filesystem, and the container gets torn down
when the job ends. Swapping to `playground` (a managed S3 lake) doesn't
change the query engine's capability, it changes *where the bytes
physically persist*. Worth remembering before assuming a destination
"doesn't work" for production — the question is usually about
storage lifetime, not the engine.

## 8. This workshop's homework is Module 5's OpenTelemetry work, one layer up

The real homework (`homework/homework_notes.md`) is explicit: Pydantic
Logfire is "an alternative" to the hand-rolled OpenTelemetry
instrumentation Module 5 already built. Same underlying model — spans,
traces, span attributes carrying token usage — just wrapped in a
Pydantic-native SDK that auto-instruments a Pydantic AI agent with two
lines (`logfire.configure()`, `logfire.instrument_pydantic_ai()`)
instead of manual `tracer.start_as_current_span(...)` wrapping. The
genuinely new skill this workshop adds on top: the traces now live in
someone else's cloud (Logfire's own storage), and dlt is the tool for
pulling them back out to somewhere locally queryable — which recreates,
almost exactly, the REST-API-pipeline pattern from lesson 4, just
pointed at a real logger's API instead of the workshop's fake test
API.
