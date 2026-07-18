# dlt Workshop — Stage-by-Stage Walkthrough

Built from the real lesson files (`cohorts/2026/workshops/dlt/lessons/01-07`,
fetched and read in full 2026-07-18), cross-checked against the workshop
video transcript. Each stage follows the same format: what it's trying
to accomplish, why it exists, how it connects to the previous stage,
what artifact it produces, and what consumes that artifact next.

**No code has been run against this walkthrough yet.** This is the
explain-first pass — the hands-on session is still ahead.

---

## Stage 0 — Setup (lesson 1)

**What it's trying to accomplish:** get a workspace that already knows
how to talk to a coding agent about dlt, before you write a single line
of pipeline code.

**Why this stage exists:** the whole workshop's premise is that you
never hand-write dlt pipelines — you describe what you want and the
agent builds it, using dlt's own pre-packaged process knowledge. That
only works if the workspace already contains the right scaffolding
(skills, MCP config, dependency files) before you start talking to the
agent.

**The command:** `uvx dlthub-init@latest`, run in an empty folder. This
creates `pyproject.toml`, a `.dlt/` config directory, a `.claude/`
skills folder, `.mcp.json` (the MCP server config), `__deployment__.py`
(empty for now — this is where deployed pipelines/dashboards get
registered later), and a virtual environment (`uv sync` runs
automatically if you say yes).

**Artifact produced:** an otherwise-empty project that already knows
how to route agent requests to the right dlt tooling.

**What consumes it next:** the coding agent, opened inside this folder,
reads the one skill that exists at this point — the **router skill** —
whenever you ask it to build something.

---

## Stage 1 — Local logs → filesystem pipeline (lesson 2)

**What it's trying to accomplish:** turn the JSONL session logs your
coding agent already writes to `~/.claude/projects/` into queryable
tables in DuckDB.

**Why this stage exists:** this is the whole workshop's opening claim —
you already have valuable data (tokens, models, tool calls) sitting on
disk in an unreadable format. This stage is the smallest possible
demonstration that the agent-driven pipeline pattern works, using data
you already have with zero setup (no API keys, no accounts).

**How it connects to the previous stage:** you ask the agent, in plain
English: *"build a dlt pipeline, load data from local Claude logs as
raw JSONs into DuckDB."* The router skill (installed in Stage 0)
inspects this request, recognizes the source is local files, and
installs the **filesystem-pipeline toolkit** — which did not exist in
the project a moment before. This "toolkit arrives only when the
conversation needs it" behavior is the router doing its job.

**What gets built:** a Python script using dlt's `filesystem` source
piped into `read_jsonl`:

```python
from dlt.sources.filesystem import filesystem, read_jsonl

reader = (
    filesystem(file_glob="**/*.jsonl")
    | read_jsonl()
).with_name("messages")
```

...wired into a `dlt.pipeline(...)` call:

```python
pipeline = dlt.pipeline(
    pipeline_name="agent_logs",
    destination="duckdb",
    dataset_name="agent_logs",
    dev_mode=True,
)
load_info = pipeline.run(reader, write_disposition="replace")
```

Two config choices worth understanding, not just copying:
`dev_mode=True` stamps a timestamp onto the dataset name every run, so
each run starts completely fresh — convenient while developing,
wasteful in production (this gets revisited in Stage 6/7).
`write_disposition="replace"` means drop-and-reload every time, not an
incremental append — also flagged in the lesson as something to fix
later, not in this workshop.

**Artifact produced:** a local `.duckdb` file containing your Claude
logs — as **78 separate tables**. This is dlt's normalization behavior,
not a bug: nested JSON gets flattened, and every nested array becomes
its own child table, linked back to its parent via `_dlt_id`/
`_dlt_parent_id`. Deeply nested agent logs → a lot of child tables.

**What consumes it next:** the debug-and-cleanup pass in Stage 2, and
the `dlthub local show` dashboard for a first look at what actually
landed.

---

## Stage 2 — Debug, schema cleanup, and a first dashboard (lesson 3)

**What it's trying to accomplish:** confirm the pipeline from Stage 1
is actually trustworthy, cut the table count down to something
workable, and get a first visual read on the data.

**Why this stage exists:** 78 tables is technically correct but
practically unusable. This stage draws an explicit, important line: a
pipeline **running without errors** and a pipeline **loading the data
you actually meant** are two different claims, and only the first one
is something automation can fully verify.

**How it connects to the previous stage:** you ask the agent to
*"debug my pipeline."* This installs the **debug-pipeline skill**
(part of the toolkit that came in with the filesystem source). The
skill runs the pipeline, inspects the trace, and — in the real run
shown in the workshop — identified the 78-table count as **schema
pollution**: too much unnesting for practical use. Its fix: mark some
deeply nested columns as JSON type instead of flattening them into yet
more child tables. Result: 78 tables → 40. This is a scope decision
about how much structure you want, made *after* the pipeline was
already confirmed to run correctly — debugging and data-shape tuning
are sequential, not the same step.

The lesson is explicit about the boundary here: "debugging... can't
tell you whether the data is correct. That's a judgment only you can
make by looking at the output." So the next move is human review, via
a dashboard.

You then ask the agent to *"build a marimo report with detailed
information about my Claude Code usage."* This pulls in the
**data-exploration toolkit** — skills for profiling data (row counts,
schemas, column stats), planning what charts answer what questions, and
assembling a marimo notebook. The agent writes an analysis plan first
(a markdown file: questions → SQL queries → chart code), then builds
the notebook from that plan.

**What a marimo notebook actually is, and why it's used here:** every
marimo notebook is a plain Python script, not a JSON blob (unlike
Jupyter). Each cell is a Python function. Cells run in a fixed
dependency order — you can't execute out of sequence — which prevents
the classic "I ran cell 7 before cell 3 and now my variables are
stale" bug class entirely. This determinism is exactly why it's a good
fit for a dashboard an agent builds and you don't hand-edit: state
can't silently drift.

Querying pattern used inside the notebook:

```python
pipeline = dlt.attach("agent_logs")
dataset = pipeline.dataset()

df = dataset("""
    SELECT agent, COUNT(*) AS records
    FROM log_records
    GROUP BY 1
    ORDER BY records DESC
""").df()
```

— a SQL cell producing a DataFrame, paired with an Altair chart cell
consuming it.

**Artifact produced:** `code/claude_logs_dashboard.py` — a marimo
dashboard showing activity over time, message types, model usage, and
top projects, run locally with `uv run marimo edit code/claude_logs_dashboard.py`.

**What consumes it next:** nothing downstream yet — this is the "prove
the local loop works end to end" checkpoint before moving to a source
that isn't just files on your own disk.

---

## Stage 3 — A hosted API as the source (lesson 4)

**What it's trying to accomplish:** repeat the same pipeline pattern,
but against data you can't read from disk — because in a real
organization, your agents run in the cloud and their logs live behind
someone else's API (Logfire, Langfuse, Datadog, the Anthropic API
itself).

**Why this stage exists:** this is the stage that generalizes the
workshop from "a nice local demo" to "the actual production shape."
Every logging service has a different trace format — different keys,
different nesting, different field order — which is exactly the
problem dlt's normalization step is built to absorb regardless of
source shape.

**How it connects to the previous stage:** same conversational pattern,
different source. You ask the agent to *"build a dlt pipeline for
[fake test API]/docs, for /logs endpoint, load 20k logs into DuckDB,
and build a similar marimo report."* The router installs the
**rest-api-pipeline toolkit** this time — a different toolkit from
Stage 1's filesystem one, with its own skills for creating a pipeline,
debugging it, exploring the data, and (not used live in the workshop)
applying incremental loading.

The agent inspects the API's OpenAPI spec (the `/docs` URL) and figures
out, without you specifying it, the base URL, the pagination style, and
where in the response body the actual records live. This is real,
non-trivial work that a hand-written pipeline would otherwise require
you to reverse-engineer yourself.

**What gets built:** the source is described as a config dictionary,
not hand-written request/pagination code:

```python
config: RESTAPIConfig = {
    "client": {
        "base_url": base_url,
        "paginator": {
            "type": "offset",
            "limit": page_size,
            "offset": 0,
            "limit_param": "limit",
            "offset_param": "offset",
            "total_path": "total",
        },
    },
    "resources": [
        {
            "name": "logs",
            "endpoint": {"path": "/logs", "data_selector": "logs"},
            "primary_key": "index",
        },
    ],
}
```

`data_selector: "logs"` tells dlt the actual records live under a
`"logs"` key in the response envelope, not at the top level — a detail
that would otherwise require reading the API's response shape by hand.
The paginator is offset-based: dlt requests `limit`/`offset` pairs and
reads a `total` field to know when to stop, capped here at 20,000 rows
via `maximum_offset` so a first pass doesn't try to pull the API's full
1 million fake rows.

**Artifact produced:** the same shape of thing as Stage 1 — a `.duckdb`
file with normalized tables, plus a second marimo dashboard
(`agent_traces_dashboard.py`) — but sourced from an HTTP API instead of
local files. The same normalization rules apply: nested objects like
`message.content` become child tables, and nested scalar objects like
`usage` flatten into columns like `usage__output_tokens`
(double-underscore separator).

**What consumes it next:** Stages 4–5 take this exact pipeline and move
it off your laptop entirely.

---

## Stage 4 — Deploy to the cloud (lesson 5)

**What it's trying to accomplish:** make the pipeline and dashboard
runnable somewhere other than your own machine, so they can be
scheduled and shared rather than depending on your laptop being open.

**Why this stage exists:** a local dashboard only exists while your
computer is running the pipeline. Sharing it with a team, or keeping it
fresh on a schedule, requires the pipeline to live somewhere persistent
— this is the dltHub Platform's actual job.

**How it connects to the previous stage:** first, `uv run dlthub login`
(device-code OAuth) and `uv run dlthub workspace connect` link your
local project to a cloud workspace — every new account gets a free
"playground" workspace automatically. From that point, anything you run
locally stays synced to the platform. `uv run dlthub show` opens the
platform's web UI.

Then you ask the agent to *"deploy this on the dlthub platform, use
duckdb as destination."* This installs the **dlthub-platform toolkit**,
which runs a five-step pre-deployment checklist before registering the
pipeline in `__deployment__.py` (the manifest file scaffolded back in
Stage 0, empty until now) and actually deploying. The same thing can be
done manually with `uv run dlthub deploy` (ship the project as a new
version) and `uv run dlthub run` (execute it in the cloud) — worth
knowing both the agent-driven and manual paths exist for the same
action.

**A real gotcha worth internalizing, not just noting:** deploying with
`destination="duckdb"` still runs — the pipeline succeeds, data loads —
but the platform runs your project inside a container, and when the job
finishes, the container's local filesystem (including that `.duckdb`
file) is torn down. The data doesn't persist across runs. This isn't a
DuckDB limitation; it's a consequence of *where* the file physically
lives once you're in a throwaway cloud container, not what the engine
can do (see mental model #7).

**The fix:** swap `destination="duckdb"` for `destination="playground"`
— a managed S3-backed lake dltHub provides for exactly this purpose
(tests, demos, and anything that needs to survive across runs without
setting up your own warehouse). This requires an extra dependency
(`deltalake`), which `dlthub deploy` adds to `pyproject.toml`
automatically if a run fails because it's missing — redeploy and rerun
after that happens once.

**Artifact produced:** the same pipeline, now running in the cloud
against persistent storage instead of a local ephemeral file.

**What consumes it next:** Stage 5 deploys the *dashboard* alongside
this pipeline and adds scheduling.

---

## Stage 5 — Deploy the dashboard and schedule it (lesson 6)

**What it's trying to accomplish:** get the marimo dashboard itself
running in the cloud, viewable by teammates without them needing the
pipeline running locally, and kept fresh automatically.

**Why this stage exists:** Stage 4 deployed the *data pipeline*.
A pipeline with no way to view its output isn't shareable yet — the
dashboard needs its own deployment step, and someone needs to decide
how often the whole thing reruns.

**How it connects to the previous stage:** the dashboard module gets
imported into `__deployment__.py` and added to `__all__`, which
registers it as a deployable **interactive job** (the platform treats
pipelines and interactive apps — marimo notebooks, Streamlit apps — as
two different kinds of deployable things, both declared in the same
manifest). The dashboard's connection also has to be pointed explicitly
at the `playground` destination and correct dataset name via
`dlt.attach(...)` — when deploying notebooks, that connection info
can't be left implicit the way it can locally.

**A concept worth naming: run mode vs. edit mode.** Once deployed, the
notebook opens in the platform UI in "run mode" — all code hidden, only
the reports and charts visible. This is the sharable view; it's a
different mode from the one you use while building it locally
(`marimo edit`), and the distinction matters: you edit locally, you
share the run-mode version.

**Sharing:** `uv run dlthub job publish agent_traces_dashboard` gets a
public URL, or it can be shared within the workspace via the
platform's own Users/Roles system instead.

**Scheduling:** a cron trigger added directly to the pipeline's
decorator in `__deployment__.py`:

```python
from dlt.hub.run import trigger

@run.pipeline("agent_traces", trigger=trigger.schedule("0 12 * * *"))
def ingest_agent_logs(): ...
```

— and pipelines can be chained with `job.success` triggers ("run the
ingestion pipeline, and if it succeeds, run the dashboard refresh"),
which is the same dependency-graph idea as any orchestrator, just
declared inline rather than in a separate DAG tool.

**Artifact produced:** a scheduled, shareable, hosted dashboard — the
actual end state the whole workshop was building toward, stated at the
very start of lesson 1 ("A scheduled deployment on the dltHub Platform
with a shareable dashboard").

**What consumes it next:** nothing further in the workshop itself —
this is the finished pipeline. Lesson 7 is a recap plus the pointer to
what's genuinely out of scope (incremental loading) and where this
connects to the actual homework.

---

## Stage 6 — Recap and what's deliberately left out (lesson 7)

**What was actually built, end to end:** a filesystem pipeline (local
logs → DuckDB) and its dashboard, a REST API pipeline (hosted traces →
lake) and its dashboard, both deployed and scheduled on the dltHub
Platform — all described in natural language, with dlt-specific
knowledge handled by the workbench's toolkits, skills, and MCP tools
rather than hand-written by you.

**What's explicitly deferred, and why it matters that it's named
rather than silently skipped:** every pipeline in this workshop used
`write_disposition="replace"` + `dev_mode=True` — full reload every
run. That's fine for a workshop, not for anything with real volume.
The real fix (incremental loading) is a one-line addition — a cursor
column (`modification_date` for files, a sequential `index` for the
REST source) wrapped in `dlt.sources.incremental(...)`, combined with
switching `write_disposition` to `"merge"` and dropping `dev_mode` so
data actually persists across runs instead of resetting. Worth reading
as "this is the obvious next step, deliberately left as an exercise,"
not as a gap in the workshop's design.

**Also named but not built:** other pre-built dlt sources
(`sql_database`, `google_sheets`, `notion`, and vendor-specific ones
like `hubspot`/`salesforce`/`stripe`), and that the exact same pipeline
code works against Postgres, BigQuery, Snowflake, or Redshift by
changing only the destination string and credentials — the "one
pipeline, many destinations" idea from Stage 4, generalized.

---

## Where this connects to the real homework

The homework (`homework/homework_notes.md` in this folder) is **not**
"repeat this workshop on your own data." It's a direct continuation:
take Module 1's FAQ agent (rewritten in Pydantic AI for this homework),
instrument it with Pydantic Logfire — genuinely new material, not
covered in the course lessons — then use dlt to pull the resulting
traces back out of Logfire's cloud storage into DuckDB, using almost
exactly the REST-API-pipeline pattern from Stage 3 above, just pointed
at a real logger instead of the workshop's fake test API. See mental
model #8 in `00_mental_models.md` for the full connection back to
Module 5's OpenTelemetry work.
