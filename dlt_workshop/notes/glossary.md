# dlt Workshop — Glossary

New vocabulary from `cohorts/2026/workshops/dlt/lessons/01-07`, defined
against what the lessons actually say, not generic docs language.

**dlt (data load tool)** — open-source Python library for building data
pipelines. Takes a source (files, an API, a database) and loads it into
a destination (DuckDB, Postgres, BigQuery, ...), automatically
normalizing nested JSON into typed relational tables along the way.

**dltHub AI workbench** — the agent-facing layer on top of dlt: a
router skill, on-demand toolkits, and an MCP server, all scaffolded by
`uvx dlthub-init@latest`. Lets a coding agent build a working dlt
pipeline from a plain-English request instead of you writing the
pipeline by hand.

**Router skill** — the one skill present in a freshly scaffolded
project. Reads your request and installs the matching toolkit
(filesystem-pipeline, rest-api-pipeline, data-exploration,
dlthub-platform) on demand — nothing pre-loaded, nothing unused sitting
around.

**Toolkit** — a bundle of related skills + MCP tools for one job (e.g.
the rest-api-pipeline toolkit bundles skills for building, debugging,
and exploring a REST-sourced pipeline). Installed by the router, not
present from the start.

**Skill (in this context)** — a markdown document of process knowledge:
what steps to take, in what order, for a given job (e.g. "debug my
pipeline" → run it, inspect the trace, check for schema pollution).
Contrast with an MCP tool.

**MCP tool** — pre-built, deterministic code the agent calls instead of
regenerating boilerplate every time (read a table, count rows, preview
a schema). Skills handle sequencing/judgment; tools handle repeatable
execution.

**Normalization** — dlt's automatic step of turning arbitrary nested
JSON into typed relational tables: infers column types, flattens
nested objects into columns (double-underscore-joined names, e.g.
`usage__output_tokens`), and creates a **child table per nested
array**, linked to its parent via `_dlt_id`/`_dlt_parent_id`.

**Schema pollution** — too many tables produced by normalization for
practical use (78 tables from one JSONL source in the workshop's first
run). Not an error — a scope decision to fix by marking some columns as
JSON type instead of unnesting them further (78 → 40 in the workshop).

**`write_disposition`** — how a pipeline run relates to previous runs.
`"replace"` (used throughout this workshop): drop and fully reload
every run. `"merge"`: update/insert incrementally, paired with
`dlt.sources.incremental(...)` — the deferred "next step" from lesson 7.

**`dev_mode=True`** — timestamps the dataset name on every run, so each
run starts from a fresh dataset. Convenient in development, wasteful/
non-persistent in production — removed once you switch to incremental
loading.

**DuckDB** — in-process analytical database, no server to run, backed
by a single local file. Default local destination for this workshop's
pipelines; ships as a dependency of dlt itself, no separate setup.

**marimo** — reactive Python notebook framework used for the
dashboards. Every notebook is a plain `.py` script (not JSON like
Jupyter), each cell is a Python function, and cell execution order is
enforced by the framework — no out-of-order execution, easier to diff
in git.

**Filesystem source** — dlt's source type for reading local/remote
files. Pattern used: `filesystem(file_glob="**/*.jsonl") |
read_jsonl()` — a file-listing source piped into a JSONL parser.

**REST API source (`RESTAPIConfig`)** — dlt's config-dictionary-driven
way of describing an HTTP API source: `client.base_url`,
`client.paginator` (pagination strategy, e.g. offset-based with
`limit_param`/`offset_param`/`total_path`), and `resources` (each with
an `endpoint.path`, a `data_selector` for pulling records out of a
response envelope, and a `primary_key`).

**`data_selector`** — the key path inside an API response body where
the actual records live (e.g. `"logs"`, if the API wraps records as
`{"logs": [...], "total": N}`).

**Destination** — where a pipeline writes data. Only this string
changes between environments: `"duckdb"` (local dev), `"playground"`
(dltHub's managed cloud lake), or a named production warehouse
(Postgres, BigQuery, Snowflake, Redshift, ...). Pipeline code otherwise
identical.

**Playground destination** — dltHub's managed, S3-backed data lake,
auto-provisioned for every new platform account. Used to fix the
ephemeral-storage problem: unlike `"duckdb"` in a cloud deployment,
data written here survives after the job's container is torn down.
Requires the `deltalake` package (auto-added by `dlthub deploy` if
missing).

**Ephemeral vs. persistent storage** — a DuckDB file deployed inside a
cloud job's container disappears when the container exits (ephemeral)
— a storage-location property, not a limitation of the DuckDB engine
itself. The playground destination is persistent because it's backed
by an actual managed lake, not a container-local file.

**`dlt.attach(pipeline_name)`** — reconnects to an already-created
pipeline's dataset from a separate script/notebook (used inside marimo
dashboards to query data an ingestion pipeline already loaded), without
rerunning the pipeline itself.

**Run mode** — the state a deployed marimo notebook opens in on the
dltHub Platform: all code hidden, only reports/charts visible. Distinct
from the local `marimo edit` mode used while building it.

**`__deployment__.py`** — the manifest file (scaffolded empty by
`dlthub-init`) where deployable pipelines and interactive apps
(dashboards) get registered via imports and `__all__`, so
`dlthub deploy`/`dlthub run` know what to ship.

**`trigger.schedule(...)`** — cron-style decorator wiring
(`@run.pipeline(..., trigger=trigger.schedule("0 12 * * *"))`) for
running a pipeline on a recurring schedule once deployed.

**`job.success` trigger** — chains one deployed job to run automatically
after another succeeds (e.g. ingestion pipeline → dashboard refresh).

**Incremental loading (`dlt.sources.incremental(...)`)** — named but not
built in this workshop; the mechanism for loading only new/changed
records using a cursor column (a file's modification date, or a
sequential `index` field), paired with `write_disposition="merge"` and
no `dev_mode`, so data persists and updates rather than fully
reloading every run.
