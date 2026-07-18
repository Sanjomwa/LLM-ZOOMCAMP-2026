# Module 5: Monitoring — Study Notes

**Course:** LLM Zoomcamp 2026
**Module:** 05 — Monitoring
**Purpose:** Long-term study reference. Return to this before instrumenting any production RAG or agent pipeline.

---

## Module Overview

Module 4 answered "is retrieval any good" with a number, computed
offline against a fixed ground-truth set, before anyone used the
system. Module 5 exists because that number goes stale the moment real
traffic starts — Hit Rate and MRR don't tell you how long an answer
took, what it cost, or whether the person who asked it was satisfied.
This homework is the sharpest version of that shift: not a dashboard
aggregating many requests, but a single request's own internal
anatomy — the trace.

### How this fits into the pipeline

```
[User Question]
       |
       v
[RAGBase.rag(query)]        <-- built in earlier modules, untouched
       |
       +--> search()        <-- 1 span: in-memory minsearch lookup
       |
       +--> build_prompt()  <-- not spanned: pure string formatting
       |
       +--> llm()           <-- 1 span: network call to OpenAI
       |
       v
[Trace: rag > search, llm]  <-- THIS HOMEWORK
       |
       v
[Answer + span table: names, durations, token counts]
```

The parent `rag` span times the whole call; `search` and `llm` are its
two children. No `judge` span, because the built-in judge
(`evaluate_relevance`, lesson 09) is called separately by `app.py`
*after* `rag()` returns — it was never part of `rag()`'s own call graph
to begin with.

**Note on the corpus:** the real cohort-specific `starter.py`
(`cohorts/2026/05-monitoring/`, confirmed live 2026-07-18) builds the
index over the same 72 unchunked lesson pages Module 4 used
(`GithubRepositoryDataReader`, commit `8c1834d`) — not the FAQ dataset
the general course lessons reuse elsewhere. The span *shape* above
(`rag` → `search`, `llm`) is unaffected by which corpus sits underneath
it, but the actual token counts (Q2) scale very differently depending
on which one is in play — see `monitoring.md`'s "Corrections" section.

**Confirmed by the real run (2026-07-18):** all six predictions in this
document held exactly. The `llm` span alone took 6,960.3ms against
`search`'s 108.9ms — a 64x gap, not a marginal one — and input tokens
were bit-for-bit identical (7,111) across 4 repeated runs of the same
query. Full numbers and reasoning per question in `monitoring.md`.

---

## Major Concepts

### Distributed tracing, spans, and traces

A **trace** represents one end-to-end operation (here, one `rag()`
call). A **span** represents one unit of work inside that trace — a
function call, a network request, anything with a start and an end
time. Spans can nest: a parent span's duration covers its children's
combined duration plus whatever the parent itself does outside of them.
This module's own lessons (01–14) never build this machinery — it's
only named in lesson 14 as the concept underlying Langfuse, Arize
Phoenix, and OpenTelemetry generally. This homework builds the smallest
possible version by hand: a `Span` dataclass, a `Trace` that holds an
ordered list of them, and a `SpanRecorder` context manager that times a
block and appends the span. No OpenTelemetry SDK, no exporter, no
external service — just enough structure to answer the six graded
questions the same way a real tracing tool's UI would show them.

### Why the parent span still needs to be tracked as its own row

It would be easy to only track `search` and `llm` and skip a `rag`
wrapper entirely, treating "the trace" as just those two spans. Q1's
answer options (1/3/5/7) and Q4's options (which all include "rag" in
every plausible answer) both signal that the parent operation itself
counts as a span in its own right, not just a container. This mirrors
how real tracing tools work: the top-level operation gets its own span
so you can see total end-to-end time, separate from any one child's
time.

### Span-append timing: enter vs. exit

`SpanRecorder` appends its `Span` to `trace.spans` on `__enter__`, not
`__exit__`. This is a small but real design choice: a parent span
(`rag`) that wraps two children (`search`, `llm`) finishes *last*, so
appending on exit would put the parent at the *end* of the spans list,
after its own children — confusing to read. Appending on entry gives a
natural parent-first, depth-first ordering (`rag`, `search`, `llm`)
that matches how you'd actually want a trace displayed.

### Fixing the shared-mutable-state pitfall, not just noting it

`05-monitoring/notes/03_common_pitfalls.md` #1 flagged
`RAGWithMetrics.last_call` as unsafe under concurrent calls — a shared
instance attribute two overlapping requests would fight over. This
homework's `TracedRAG.rag_traced()` returns `(answer, trace)` directly
instead of stashing anything on `self`. This isn't a hypothetical
improvement — it's the same fix that pitfall note already recommended,
now actually applied in code rather than just written down as a "should
fix" item.

### Non-determinism as a thing to test, not assume

Q6 asks whether input tokens vary across 4 identical runs of the same
query. The naive expectation is "no" — `minsearch`'s keyword index is a
deterministic TF-IDF-style scorer over an already-built, static index,
so the same query string should retrieve the same documents in the same
order every time, producing an identical prompt and an identical token
count. But "should be identical" is a hypothesis about the pipeline's
architecture, not a guarantee — the only way to actually know is to run
it four times and look. This is the same discipline Module 4's central
lesson taught (intuition is a hypothesis generator, not a verification
method), applied here to a completely different kind of claim: not "is
this design good" but "is this system actually deterministic."

---

## Connections to Real Projects (incl. the Civil Liberties Knowledge Assistant)

- **The subclass-and-override pattern generalizes directly to an
  agent.** `TracedRAG` overrides the same seam `RAGWithMetrics` did
  (lesson 04) — this homework just widens the wrapped region from "the
  llm call" to "the whole rag() call" so both `search` and `llm` get
  their own spans. An agent with multiple tool calls would extend this
  the same way: one span per tool call, nested under a parent span for
  the whole agent turn. This is the concrete version of what
  `05-monitoring/homework/homework_notes.md`'s superseded "monitor an
  agent" option would have required, has it turned out to be the real
  assignment.
- **Directly informs `project/project_monitoring_plan.md`'s "what to
  capture per request" section.** That doc already lists citations and
  an evidence-thinness flag as project-specific additions to the
  course's own five-item capture list. A `Trace`/`Span` structure is a
  natural home for those too — e.g., a `citation_check` span wrapping
  whatever step verifies a citation against corpus content, timed and
  scored the same way `llm` is timed and scored here.
- **The judge-latency pitfall (lesson 09, already in
  `03_common_pitfalls.md` #4) is reinforced, not contradicted, by this
  homework's design.** Choosing not to add a `judge` span here isn't an
  oversight — it's consistent with the same reasoning that pitfall note
  already made: an automated judge call is a real latency/cost add-on,
  not a free part of the core `rag()` path, so it shouldn't be silently
  folded into the same trace as if it were.

---

## Lessons Learned

- A trace is the smallest unit of "online evaluation" this module ever
  produces — smaller than a dashboard, smaller than an aggregate
  metric, down to one single request's internal shape. Worth treating
  as a debugging tool in its own right (which sub-step is slow, right
  now, for this one query), not just dashboard raw material.
- Writing your own minimal tracer, once, makes the commercial
  tools (Langfuse, Phoenix, OpenTelemetry) legible later — the concepts
  (span, trace, parent/child, attributes) transfer directly, just with
  more infrastructure (exporters, storage, UI) around the same basic
  idea.
- Predicting answers from reading the actual pipeline source
  (`RAGBase.rag()`) before running anything is a stronger check than it
  sounds — Q1 and Q4 are close to fully determined by the code itself,
  which is a good sanity check to run before trusting a live result:
  if the real trace doesn't show `rag`, `search`, `llm`, something in
  the instrumentation is wrong, not the prediction. Confirmed here: all
  six predictions held on the real run, including the two (Q3/Q5's
  latency dominance, Q6's determinism) that were genuine hypotheses
  rather than facts read off the code.
- A parent span's own duration is a free correctness check on the
  tracer itself: `rag`'s 7069.3ms matched `search` + `llm`
  (108.9 + 6960.3 = 7069.2ms) almost exactly. If a parent span's
  duration doesn't roughly equal the sum of its children plus whatever
  un-spanned work happens between them, that's a sign the tracer has a
  bug, not a sign the pipeline is doing something exotic.
- The corpus-choice correction (FAQ dataset vs. full unchunked lesson
  pages) changed Q2 by roughly 10x (hundreds vs. 7,111) — a concrete
  reminder that "which data is actually underneath this pipeline" is
  not a detail to assume from a similar-looking earlier module, even
  when the RAG *shape* (search → prompt → llm) is identical.

---

## Key Takeaways

- Trace = one request's full call graph; span = one timed unit of work
  inside it, possibly nested.
- Append spans to a trace on entry, not exit, if you want a
  parent-first, human-readable ordering.
- Return trace/metrics data explicitly rather than storing it as
  mutable instance state — cheap to get right from the start, annoying
  to retrofit once anything concurrent exists.
- Test determinism claims about a pipeline the same way you'd test any
  other claim about it: run it and look, don't assume from the
  architecture alone.

---

*Submission doc: [monitoring.md](monitoring.md)*
*Full notebook: [monitoring.ipynb](monitoring.ipynb)*
*Course material: [05-monitoring](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring)*