# dlt Homework — Notes

Real, live homework fetched directly from
`cohorts/2026/workshops/dlt/homework.md` on 2026-07-18. Not predicted
from lesson text — this is the actual graded assignment.

**Status: not started.** Both this and the Module 5 monitoring homework
were announced together on the course Telegram channel: "we have
prepared the homework for the dlt workshop as well as the monitoring
module... both about monitoring and observability." Module 5's is
done. This one is next.

**Deadline:** check `courses.datatalks.club/llm-zoomcamp-2026/homework/dlt`
for the live date — not yet confirmed/recorded here since this hasn't
been opened in the course-management site yet.

---

## What it's actually testing

Not a repeat of the workshop's own filesystem/REST-API pipeline
exercises. It's a continuation of **Module 1's FAQ agent**, run through
two new pieces: **Pydantic Logfire** for instrumentation (genuinely new
material — Module 5 built OpenTelemetry by hand, this homework uses a
higher-level SDK that wraps the same span/trace model), and **dlt** for
pulling the resulting trace data back out of Logfire's cloud storage
into something locally queryable (DuckDB) — reusing almost exactly the
REST-API-pipeline pattern from workshop lesson 4, just pointed at a
real logging service instead of the workshop's fake test API.

See `notes/00_mental_models.md` #8 for the full reasoning connecting
this back to Module 5.

## Setup

Starter files fetched via `wget` from
`cohorts/2026/workshops/dlt/homework/`: `agent.py`, `ingest.py`,
`main.py`, `.env.example`. The FAQ agent itself is rewritten in
**Pydantic AI** for this homework (not the original hand-rolled
loop/toyaikit from Module 1) — the stated reason is that Pydantic AI
integrates directly with Logfire.

Dependencies:
```
uv init
uv add openai minsearch requests python-dotenv pydantic-ai logfire
uv add "dlt[duckdb]"
```

Instrumentation is two lines on top of the Pydantic AI agent:
```python
logfire.configure()
logfire.instrument_pydantic_ai()
```

## The three questions

**Q1 — span count.** Run the agent once with the question "How do I run
Ollama locally?" and count how many spans the resulting trace contains
in Logfire. Options: 1 / 5 / 15 / 30.

**Q2 — table count after the dlt pull.** Use dlt to pull the Logfire
trace data into DuckDB (via dltHub's ready-made Logfire REST source
context, `https://dlthub.com/context/source/logfire`), then run:
```sql
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'agent_traces';
```
Options: 1 / 3 / 24 / 100.

**Q3 — summed input tokens.** For the same Q1 run, sum
`gen_ai.usage.input_tokens` across the spans that carry it, and report
which range it falls in. Options: 100-500 / 1500-5000 / 10000-20000 /
50000-100000.

**Submission:** `https://courses.datatalks.club/llm-zoomcamp-2026/homework/dlt`

## What to actually do before running anything

1. Read `agent.py`/`main.py` first — understand what's different about
   the Pydantic AI rewrite vs. Module 1's original agent (course style:
   understand before running, not just execute).
2. Get a Logfire account/write token before configuring
   `logfire.configure()` — check `.env.example` for what's expected.
3. Run the Q1 query once, look at the trace in the Logfire UI directly
   before writing any dlt pipeline — same "validate the data yourself"
   discipline the workshop's lesson 3 was explicit about (automated
   pulls don't replace looking at the actual output).
4. Only then build the dlt pipeline pulling from Logfire's API, using
   the ready-made source context as a starting point rather than
   hand-rolling the REST API config from scratch — this homework
   supplies a known-good `RESTAPIConfig` source, unlike the workshop
   itself which built one from an OpenAPI spec by hand.

Nothing above has been run yet. No numeric answers exist to record.
