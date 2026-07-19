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
and it can even self-correct real problems (the schema-pollution fix
below happened during an explicit "debug my pipeline" step). But
lesson 3 is direct about the boundary: debugging "can't tell you
whether the data is correct. That's a judgment only you can make by
looking at the output." Automated debugging is a necessary but
insufficient check — human review of the actual data stays mandatory
no matter how good the tooling gets.

## 5. Many tables from nested JSON is correct dlt behavior, not a bug

dlt normalizes on load: it infers types, flattens nested objects, and
creates a **child table per nested array**, linked back to the parent
via `_dlt_id`/`_dlt_parent_id`. The lesson's own example (a larger,
longer-running Claude Code history than ours) produced 78 tables on
first load, cut to 40 after the same schema-pollution fix described
below. **Our own hands-on reproduction, on a smaller 5-session log
set, produced 23 tables on first load — cut to 9** after marking two
deeply nested, low-value fields (`attachment`, `tool_use_result`) as
JSON type instead of letting them unnest further (see `PROGRESS.md`
Stage 2). Same phenomenon, different scale — table count is a function
of how much data and how deeply nested it is, not a fixed number to
memorize. Either way: this is genuinely correct behavior given the
input shape, not something to "fix" as an error. The actual lever you
pull (schema pollution control) is a **scope decision** about how deep
you want structure to go, made explicitly and after debugging
confirmed the pipeline itself was already working.

The homework pushed this further in the other direction: a *single*
Logfire trace — just 6 span rows — exploded into **24** DuckDB tables,
because one span's `attributes` field alone carries deeply nested LLM
messages, tool-call arguments, and tool-call results. Small input,
large structural surface — the nesting was always there, most people
just never load it somewhere that forces them to see it.

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

The part worth naming explicitly: building your *own* tracer by hand
in Module 5 is precisely what makes Logfire legible now, rather than a
new black box. Having already implemented "a span is a named block of
time with a parent and some attributes" yourself, seeing Logfire's UI
show `invoke_agent` → `chat` → `execute_tool` spans isn't new
information to decode — it's a familiar shape wearing a nicer
interface. The manual version wasn't wasted effort superseded by a
better tool; it's what turns the better tool from unfamiliar into
recognizable.

## 9. Written material — course lessons, vendor docs, dltHub's own context pages — is a starting point, not ground truth

Three separate, real instances in this module, not a hypothetical
caution: the workshop notes had left the fake test API's URL as an
unfilled placeholder; the deployment lesson's own `dlt.attach(...)`
example named the wrong dataset (`agent_logs` instead of the pipeline's
actual `traces`); and following the deployment lesson's literal
`__deployment__.py` import pattern triggered a real tool bug that
silently dropped a job from the deploy manifest. None of these were
found by reading more carefully — they were found by checking against
something that couldn't lie: the live API's own `/openapi.json`, the
actual `dlthub deploy --show-manifest` output, the real query results
from a running pipeline. Every one would have shipped silently broken
(or not shipped at all) if the written instructions had been trusted
as authoritative instead of treated as a claim to verify. This
generalizes past dlt: any time an AI-assisted or documentation-driven
workflow tells you what *should* happen, the live system is the only
source that tells you what *actually* happens.

---

## Post seeds — learning-in-public angles

Working notes for turning this module into public posts (course
requirement: 7 on X, 1 longer one on LinkedIn). Each seed below is
self-contained: **hook** (the one-line surprise), **stakes** (why a
reader should care, not just find it neat), **audience** (who this
actually lands for), **artifact** (the concrete number/error/file that
proves it, so the post isn't just an assertion). Seeds map back to the
numbered mental models above and to `PROGRESS.md` for exact figures —
this section doesn't repeat the mechanics, only the framing.

1. **Hook:** Your coding agent has been logging everything it does —
   tokens, models, every tool call — the whole time. You just never
   had a way to read it. **Stakes:** most engineers assume "we don't
   have observability" when the real problem is "we have observability
   we can't query." **Audience:** anyone using an AI coding agent daily
   who has never looked at what it's writing to disk. **Artifact:**
   `~/.claude/projects/**/*.jsonl` → a queryable DuckDB table, zero
   instrumentation added. (Mental Model 1)

2. **Hook:** A cloud pipeline can report "success, no failed jobs" and
   still lose every row you loaded. **Stakes:** "it ran without
   erroring" and "my data is safe" are different claims, and the gap
   between them is exactly where production incidents live.
   **Audience:** anyone deploying to ephemeral compute (serverless,
   containers, CI-triggered jobs) for the first time. **Artifact:** the
   same pipeline, same code, loaded to
   `/tmp/dlt_run_.../agent_traces.duckdb` (gone) vs.
   `s3://dlthub-.../traces` (persisted) — one destination-string change.
   (Mental Model 7)

3. **Hook:** Loading 5 small log files produced 23 database tables.
   That's not a bug — it's your data's real shape, finally visible.
   **Stakes:** nested JSON *looks* like "one record" until something
   forces it flat; most data people have never actually seen how much
   structure their "simple" JSON blob was hiding. **Audience:** data
   engineers who've only ever glanced at a JSON payload, never fully
   unnested one. **Artifact:** 23 tables → 9 after a deliberate
   scope decision (not a fix) to stop unnesting two fields. (Mental
   Model 5)

4. **Hook:** I hand-built a tracer from scratch in an earlier module —
   and that's the only reason a managed observability product made
   sense to me two lines of code later. **Stakes:** counterintuitive
   claim worth a real audience reaction — that skipping the "hard way"
   sometimes makes the "easy way" *harder* to actually understand, not
   easier. **Audience:** engineers deciding whether to learn a
   primitive by hand or just adopt the managed product. **Artifact:**
   `tracer.start_as_current_span(...)` (Module 5, by hand) vs.
   `logfire.instrument_pydantic_ai()` (this module, two lines) —
   same span/trace model underneath both. (Mental Model 8)

5. **Hook:** One AI agent's single question-and-answer exchange — 6
   logged events — unpacked into 24 database tables. **Stakes:** this
   is what "AI agents produce a lot of hidden data" actually looks
   like in numbers, not vibes. **Audience:** anyone building or
   evaluating AI agents who hasn't looked at what a single trace
   actually contains. **Artifact:** 6 span rows →
   `SELECT COUNT(*) FROM information_schema.tables` → 24. (Mental
   Model 5, homework extension)

6. **Hook:** I caught three real errors in official course material —
   not by reading more carefully, but by refusing to trust it and
   checking the live system instead. **Stakes:** this is the actual
   skill "AI-assisted development" requires and rarely gets named —
   verification discipline, not faster typing. **Audience:** anyone
   worried AI coding tools make people sloppier, or anyone using
   AI-generated/documented workflows at work. **Artifact:** a
   placeholder API URL, a wrong dataset name in a lesson's own code
   sample, a deploy tool silently dropping a job — three separate
   catches, three separate live-system checks. (Mental Model 9)

7. **Hook:** I didn't install a single data tool before I needed it —
   I described what I wanted in English, and the right toolkit
   appeared mid-conversation. **Stakes:** this is a real, different
   way of working, not a gimmick — the tooling footprint stays
   proportional to what's actually being built, not front-loaded.
   **Audience:** engineers skeptical that "agentic" tooling is more
   than a chat wrapper. **Artifact:** an empty project scaffold at the
   start of the session, four different toolkits installed on demand
   by the time it ended, each triggered by a plain-English ask.
   (Mental Model 2)

### LinkedIn arc (the thread connecting all seven)

The throughline across the whole module is **recursive observability**:
an AI coding agent (Claude Code) generates logs about its own work →
dlt structures them into something queryable. Then a *second*, separate
AI agent (the course's own FAQ bot) generates traces about its own
work → gets shipped to a vendor's cloud via a two-line SDK → and the
*same* dlt pattern from earlier in the module is what pulls that data
back out into something queryable again. The tools watching the AI are
themselves producing exactly the kind of messy, deeply-nested,
high-volume data that AI-adjacent data engineering exists to tame — the
module isn't really "here's a data tool," it's "here's what it looks
like when the discipline of structuring data gets pointed at the
tooling that's now everywhere in how we build software." The
verification thread (seed 6) is the closing beat: none of this was
trustworthy by default, including the instructions for building it —
the actual skill was checking, not following.
