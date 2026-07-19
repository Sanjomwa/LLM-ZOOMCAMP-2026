# dlt Workshop — Course Progress

**This file is git-tracked (not gitignored).** It's the durable,
authoritative record of where we are in the workshop and homework —
it survives session restarts, new machines, and clean clones on
purpose. Update it every time a stage or question status changes.
Read it at the start of every session before anything else
(see `CLAUDE.md` → Session start checklist).

Last updated: **2026-07-19**

---

## Workshop stages

Reference: `notes/01_workshop_walkthrough.md`. Status reflects actual
work done in *this* repo, not just notes written about the lesson.

| Stage | What it builds | Status |
|---|---|---|
| 0 — Setup | `uvx dlthub-init` scaffolding (`.dlt/`, `.mcp.json`, `.claude/`, venv) | ✅ Done — workspace scaffolded |
| 1 — Local logs → filesystem pipeline | Claude Code JSONL logs → DuckDB via filesystem source | ✅ Done — pipeline built and run |
| 2 — Debug + schema cleanup + first dashboard | debug-pipeline skill, schema pollution fix, marimo dashboard | ✅ Done — cleaned schema, dashboard built and running |
| 3 — Hosted API as source | REST API pipeline (fake test API → DuckDB) | ✅ Done — 20k rows loaded, dashboard built and running |
| 4 — Deploy to cloud | `dlthub login`/`connect`, deploy pipeline, `playground` destination | ✅ Done — deployed, persists to S3 |
| 5 — Deploy dashboard + schedule | Dashboard as interactive job, cron trigger | ✅ Done — published; schedule demoed then deliberately removed |
| 6 — Recap | No build — conceptual recap only | ✅ Done — workshop complete |

**Where exactly we are on Stage 1:** done, end to end (2026-07-19).
The `filesystem-pipeline` toolkit was installed via
`uv run dlthub --non-interactive ai toolkit install filesystem-pipeline`,
then its `create-filesystem-pipeline` entry skill was used to scaffold
and run `filesystem_pipeline.py`. Pipeline reads `**/*.jsonl` from
`file:///home/sanjomwa/.claude/projects` (config: `.dlt/config.toml`
`[sources.filesystem].bucket_url`) with `read_jsonl`, single-table
layout, into DuckDB at
`.dlt/data/dev/claude_logs_pipeline.duckdb`, dataset `claude_logs`
(pipeline uses `dev_mode=True`, so each run creates a fresh
timestamp-suffixed dataset, e.g. `claude_logs_20260719074152` — not a
bug). First run loaded 385 top-level rows across all 5 local session
files into table `sessions`, exploded into nested child tables
(`sessions__message__content`, `sessions__attachment__*`,
`sessions__tool_use_result__*`, etc.) by dlt's normalizer. Verified
directly via DuckDB query (`type` breakdown: assistant 145, user 86,
attachment 33, mode/permission-mode/last-prompt/ai-title/
file-history-* events making up the rest; row counts per `session_id`
all accounted for).

**Where exactly we are on Stage 2:** done, end to end (2026-07-19).
Installed `rest-api-pipeline` toolkit (for its `debug-pipeline` skill)
and `data-exploration` toolkit (for `explore-data` + `build-notebook`).
Schema pollution confirmed: the Stage 1 run produced 23 tables (3 dlt-
internal + `sessions` + 19 child tables), matching the lesson's
diagnosis. Fix applied in `filesystem_pipeline.py` via
`reader.apply_hints(columns={...})` marking `attachment`,
`tool_use_result`, and `message__content__input` as `data_type: json`
instead of unnesting — these are file-diff/tool-payload data with
little value for a usage dashboard. Result: 23 → 9 tables (`sessions`,
`sessions__message__content`, `sessions__message__usage__iterations`,
plus two tiny `AskUserQuestion`-input child tables left structured
since they're small and genuinely tabular). Three columns still can't
be typed because they're all-null in this data so far:
`message__diagnostics`, `message__stop_details`,
`message__stop_sequence` — not a bug, just no data with those fields
yet.

Then wrote `2026-07-19_claude_logs_pipeline_analysis_plan.md` (via
`explore-data`, bulk mode — all 4 charts from the lesson's stated
target planned at once, not one-at-a-time) and built
`claude_logs_pipeline_dashboard.py` (via `build-notebook`): activity
over time, message types breakdown, token usage by model, top projects
by activity (`cwd`). `uvx marimo check` passed (cosmetic warnings
only). Added `altair` to `pyproject.toml` (was missing; `pandas` was
already declared but not yet synced — both installed via `uv add`).
Dashboard launched with `uv run marimo edit
claude_logs_pipeline_dashboard.py --no-token` at `localhost:2718`.

**Where exactly we are on Stage 3:** done, end to end (2026-07-19).
The workshop notes had left the fake test API's URL as a placeholder
(`[fake test API]`) — pulled the real URL and reference code directly
from the course repo (`cohorts/2026/workshops/dlt/lessons/
04-rest-api-pipeline.md` and `code/rest_api_pipeline.py`) rather than
guessing it, and cross-checked live against the API's own
`/openapi.json` before writing any code. Base URL:
`https://test-agent-traces-api-xt2e7ottma-ew.a.run.app`, endpoint
`/logs` (offset/limit pagination, max `limit=1000`/request, `total`
in the response envelope, records under `logs`, primary key `index`,
no auth). Installed `rest-api-pipeline` toolkit already present from
Stage 2. `rest_api_pipeline.py` uses `RESTAPIConfig` with
`maximum_offset: 20000` — capped at 20k rows per the lesson's stated
instruction ("load 20k logs into DuckDB"), not the full 1M-row table.
Pipeline name `agent_traces`, dataset `traces`, DuckDB at
`.dlt/data/dev/agent_traces.duckdb`. Loaded cleanly: 20,000 rows in
`logs` (indices 0–19999, all unique), 19,668 in
`logs__message__content` — no schema pollution here (this API's data
is flatter than the local Claude Code logs from Stage 1).

Built `agent_traces_dashboard.py` (6 charts, mirroring the course's
own reference dashboard adapted for our 20k-row window: logs by type,
activity per hour by type, logs by git branch, output tokens by git
branch, message content block types, messages-per-session
distribution). `uvx marimo check` passed (cosmetic warning only).
Both dashboards now run concurrently: `claude_logs_pipeline_dashboard.py`
at `localhost:2718`, `agent_traces_dashboard.py` at `localhost:2719`.

**Where exactly we are on Stage 4:** done, end to end (2026-07-19).
User ran `uv run dlthub login` (device-code OAuth) and
`uv run dlthub workspace connect` themselves in their own terminal —
interactive browser auth I can't perform. Connected to the auto-created
`playground` workspace (`workspace_id`/`organization_id` now in
`.dlt/config.toml`). Installed `dlthub-platform` toolkit. Skipped
`prepare-deployment`'s prod/dev credential-splitting and named-destination
steps — not applicable here (the API needs no auth, and the lesson
inlines the destination string directly rather than using a named
destination).

Changed `rest_api_pipeline.py`'s `load()` into `ingest_agent_traces()`,
decorated with `@run.pipeline("agent_traces")` from `dlt.hub.run`, and
**dropped `dev_mode=True`** — a deliberate deviation from Stages 1-3.
Reasoning: `dev_mode` stamps a fresh timestamped dataset on every run,
which is fine for local iteration but would break a *deployed* pipeline
(each cloud run would create a new, disconnected dataset the dashboard
could never reliably attach to). The lesson's own reference code
(`code/rest_api_pipeline.py` in the course repo) never used `dev_mode`
here either. `write_disposition` stays `"replace"` — not jumping ahead
to the incremental/merge work Stage 6 explicitly defers.

Registered `ingest_agent_traces` in `__deployment__.py`. `dlthub deploy`
also auto-added a built-in `dashboard` job (dltHub's generic workspace
data-explorer UI — unrelated to our marimo notebooks, always scaffolded
by default).

Confirmed the gotcha directly: first deploy+run with
`destination="duckdb"` succeeded (20,000 rows, no failed jobs) but
loaded to `/tmp/dlt_run_.../prod/agent_traces.duckdb` — a container-local
tmp path. Switched to `destination="playground"`, redeployed, reran —
failed exactly as predicted with `ModuleNotFoundError: No module named
'deltalake'`. Note: `dlthub deploy` did **not** auto-add the dependency
to `pyproject.toml` on its own (contrary to the lesson's wording) — added
`dlt[deltalake]` manually via `uv add`, matching the fix the error
message itself suggested. Redeployed and reran: succeeded, loaded to
`s3://dlthub-prod-sp-eu1-playground/<org>/<workspace>/traces` — S3-backed,
persists across runs.

**Where exactly we are on Stage 5:** done, end to end (2026-07-19).

Caught another lesson-text/reality mismatch before it broke anything:
lesson 6's own snippet shows `dlt.attach("agent_traces",
destination="playground", dataset_name="agent_logs")` — but our
pipeline actually writes to dataset `traces` (confirmed in Stage 4's
run output), not `agent_logs`. Used the correct name from our own
pipeline instead of copying the stale example verbatim.

Hit a real deployment-tooling bug, not a lesson-text gap: following
lesson 6's literal `__deployment__.py` pattern —
`from agent_traces_dashboard import app as agent_traces_dashboard` —
made the deploy scanner treat the *entire* `__deployment__` module as
a single marimo notebook job, silently swallowing
`ingest_agent_traces` entirely (confirmed via `dlthub deploy
--show-manifest`: only one job, `jobs.__deployment__`, showed up).
Switched to the `prepare-deployment` skill's own convention —
`import agent_traces_dashboard` (the module, not the app object) —
which fixed it: manifest correctly showed all 3 jobs
(`ingest_agent_traces`, `agent_traces_dashboard`, the built-in
`workspace.dashboard`).

Deployed and served `agent_traces_dashboard` (`dlthub job serve`) —
confirmed `running` via `dlthub job runs list` (profile `access`, per
`dlthub-platform-profiles.md`: interactive jobs run on `access`).
Published it with `dlthub job publish agent_traces_dashboard` (user
confirmed first, since this creates a real public URL) →
`https://app.dlthub.com/n/28ce9dd9-0538-43b3-a87e-4e45ae115c6d/9186e045-6694-4922-aeec-f4b411916002`.

Added `trigger=trigger.schedule("0 12 * * *")` to `ingest_agent_traces`'s
`@run.pipeline(...)` decorator in `rest_api_pipeline.py` (not in
`__deployment__.py` — the decorator lives where the function is
actually defined; `__deployment__.py` only imports it). Deployed,
confirmed via `dlthub job list` that the trigger showed
`schedule:0 12 * * *`. **Per explicit user instruction — this is a
course-only workspace, not something to leave running unattended —
removed the trigger and redeployed immediately after confirming it
worked**, rather than waiting until session end. Reconfirmed via
`dlthub job list`: trigger is back to manual
(`pipeline_name:agent_traces`), no schedule remains. See
[[dlt-workshop-no-lingering-cron]] memory — same rule applies to any
future scheduling work in this workspace.

**Stage 6 — done (2026-07-19).** Conceptual recap only, no build.
Fetched the real lesson 7 source to confirm scope (same pattern as
Stages 3/5) — matched our repo closely, with artifact names lining up
almost exactly (`filesystem_pipeline.py`, `rest_api_pipeline.py`,
`agent_traces_dashboard.py`, `__deployment__.py`; our
`claude_logs_pipeline_dashboard.py` vs. the lesson's
`claude_logs_dashboard.py` — cosmetic naming difference only, follows
`build-notebook`'s own `<pipeline_name>_dashboard.py` convention).

Confirmed what's deliberately deferred: incremental loading
(`dlt.sources.incremental("modification_date")` for the filesystem
pipeline, `dlt.sources.incremental("index")` for the REST API pipeline,
both switching to `write_disposition="merge"`) was never built — matches
the lesson's own framing as "the obvious next step, deliberately left
as an exercise." One nuance specific to this repo: `dev_mode` was
already dropped from `rest_api_pipeline.py`'s deployed function back in
Stage 4 (out of necessity for the dashboard's dataset attachment to
work), so that half of the lesson's generic incremental-loading
write-up doesn't fully apply here — only the actual cursor/merge part
is still open.

**WORKSHOP COMPLETE (Stages 0–6).** Three real lesson-text/reality
mismatches were caught by verifying against live sources instead of
trusting notes: Stage 3's placeholder API URL, Stage 5's stale dataset
name, and Stage 5's deployment-scanner bug from the lesson's literal
import pattern.

**Next concrete action:** the **homework track** below — separate from
the workshop stages, still not started. Continues Module 1's FAQ agent
with Pydantic Logfire instrumentation + a dlt pipeline pulling the
traces back out.

---

## Homework

Reference: `dlt_homework_materials/homework_notes.md`.

**Status: not started.** Separate track from the workshop stages above
— it continues Module 1's FAQ agent rather than repeating the
workshop's own pipelines.

| Step | Status |
|---|---|
| Read `agent.py`/`main.py` (Pydantic AI rewrite of Module 1's agent) | ⬜ |
| Get Logfire account + write token, configure `.env` | ⬜ |
| Run agent once with "How do I run Ollama locally?", inspect trace in Logfire UI | ⬜ |
| Q1 — count spans in that trace | ⬜ Not answered |
| Build dlt pipeline pulling Logfire traces → DuckDB (ready-made Logfire REST source context) | ⬜ |
| Q2 — count tables in `agent_traces` schema | ⬜ Not answered |
| Q3 — sum `gen_ai.usage.input_tokens` across spans, pick range | ⬜ Not answered |
| Submit at `courses.datatalks.club/llm-zoomcamp-2026/homework/dlt` | ⬜ |

Deadline: not yet confirmed — check the course-management site link
above (wasn't open yet as of 2026-07-18).

---

## How to update this file

When a stage or homework step's status changes, edit the relevant row
directly (⬜ → 🔶 → ✅) and bump **Last updated** at the top. Keep the
"where exactly we are" / "next concrete action" prose under Stage 1
(or whichever stage is current) current — that prose, not just the
table, is what a fresh session actually needs to pick up correctly.
