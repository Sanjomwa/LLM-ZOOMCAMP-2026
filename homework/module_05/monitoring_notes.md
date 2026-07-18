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
anatomy — the trace, built with the real industry-standard framework
(OpenTelemetry), not a stand-in for it.

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
[Trace: rag > search, llm]  <-- THIS HOMEWORK, via OpenTelemetry
       |
       v
[SQLite spans table: names, timestamps, token counts]
```

The parent `rag` span times the whole call; `search` and `llm` are its
two children. No `judge` span, because the built-in judge
(`evaluate_relevance`, lesson 09) is called separately by `app.py`
*after* `rag()` returns — it was never part of `rag()`'s own call graph
to begin with.

**Note on the corpus:** the real cohort-specific `starter.py`
(`cohorts/2026/05-monitoring/`) builds the index over the same 72
unchunked lesson pages Module 4 used (`GithubRepositoryDataReader`,
commit `8c1834d`) — not the FAQ dataset the general course lessons
reuse elsewhere. The span *shape* above (`rag` → `search`, `llm`) is
unaffected by which corpus sits underneath it, but the actual token
counts (Q2) scale very differently depending on which one is in play —
full unchunked pages push input tokens into the thousands rather than
the hundreds an FAQ-snippet context would produce.

**Correction, 2026-07-18:** this document originally described a
hand-rolled tracer (`Span`/`Trace`/`SpanRecorder`, no external
library), built because every fetch of the real homework file
(`cohorts/2026/05-monitoring/homework.md`) returned a stale, cached
`## Homework: TODO` placeholder. The real, live file requires actual
`opentelemetry-api`/`opentelemetry-sdk` — a full "OpenTelemetry setup"
section with `TracerProvider`, `ConsoleSpanExporter`, and
`start_as_current_span` is part of the graded assignment, not
optional. Rewritten below around the real implementation. The
hand-rolled pass is kept as a "what we tried first" note where it's
still useful, since it genuinely mirrors this course's own
teach-the-primitive-before-naming-the-framework pattern (see "Two
passes, not a mistake to erase" below) — it's just not what the graded
answers come from.

**Confirmed by the real OpenTelemetry run (2026-07-18):** Sam ran
`monitoring.ipynb` with a real API key. All six answers landed as
predicted, and the console output confirmed the span-export-order
finding exactly — every printed trace came out `search`, `llm`, `rag`,
child-first, not parent-first. `llm` again dominated total time by a
wide margin (2,604.5ms vs. `search`'s 35.1ms on the run measured for
Q5), and input tokens were identical (7,111) across all 4 repeated
runs in Q6 — 0.00% deviation. Full numbers and reasoning per question
in `monitoring.md`.

---

## Major Concepts

### Distributed tracing, spans, and traces (the real OpenTelemetry vocabulary)

A **trace** represents one end-to-end operation (here, one `rag()`
call). A **span** represents one unit of work inside that trace — a
function call, a network request, anything with a start and an end
time. Spans nest: entering `tracer.start_as_current_span(...)` inside
an already-open span automatically makes the new span a child of it —
no manual parent-linking required, OpenTelemetry tracks this via
context propagation. **Attributes** are key-value pairs attached to a
span (`span.set_attribute("input_tokens", ...)`) for anything worth
recording beyond timing.

The real setup, registered *before* `starter` is imported (the
homework is explicit about this ordering):

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("llm-zoomcamp")
```

`TracerProvider` is the SDK's central config object; `SimpleSpanProcessor`
forwards each finished span synchronously to whatever exporter it wraps
(here, `ConsoleSpanExporter`, which prints); `trace.set_tracer_provider`
registers it globally so any later `trace.get_tracer(...)` call is
backed by it.

### Instrumenting the pipeline: subclass and wrap

```python
class RAGTraced(RAGBase):
    def rag(self, query):
        with tracer.start_as_current_span("rag"):
            return super().rag(query)

    def search(self, query, num_results=5):
        with tracer.start_as_current_span("search") as span:
            results = super().search(query, num_results=num_results)
            span.set_attribute("num_results", len(results))
            return results

    def llm(self, prompt):
        with tracer.start_as_current_span("llm") as span:
            response = super().llm(prompt)
            usage = response.usage
            span.set_attribute("input_tokens", usage.input_tokens)
            span.set_attribute("output_tokens", usage.output_tokens)
            span.set_attribute("cost", calculate_cost(self.model, usage))
            return response
```

Same subclass-and-override seam lesson 04's `RAGWithMetrics` used —
this homework just widens the wrapped region from "the llm call" to
"the whole rag() call," so `search` and `llm` each get their own span
nested inside `rag`'s.

### Span export order: children finish before parents

Verified with a real (pip-installed, not mocked) `opentelemetry-sdk`
run: `ConsoleSpanExporter` prints — and any exporter receives — each
span when it *finishes*, not when it starts. A parent span's own
`with` block can't exit until everything nested inside it has already
returned, so the child spans (`search`, `llm`) always finish, and
therefore export, before the parent (`rag`) does. Console output and
database row order both come out **child-first**: `search`, `llm`,
`rag` — not `rag` first, the way you might expect from it being the
"outer" operation. This doesn't change which spans exist or how many
there are (Q1, Q4 are unaffected — neither depends on row order), just
the order you'll see them printed or inserted.

### Persisting spans: a custom `SpanExporter`

The console exporter only prints; nothing is kept once the terminal
scrolls past it. The homework's own given `SQLiteSpanExporter`
subclasses `SpanExporter` and implements `export(spans)` (insert each
`ReadableSpan`'s name/timestamps/attributes as a row, return
`SpanExportResult.SUCCESS`), `shutdown()`, and `force_flush()`. Added
as a *second* span processor alongside the console one — OTel doesn't
require picking one exporter, any number of processors can each get
every finished span.

### Sanity-checking the instrumentation

A parent span's duration should land close to the sum of its
children's durations, plus whatever un-spanned work happens between
them (here, `build_prompt()` — pure string formatting, not spanned).
Every `ReadableSpan` carries `start_time`/`end_time` as nanosecond
Unix timestamps, so this is one line of arithmetic:
`(rag.end_time - rag.start_time)` vs.
`(search.end_time - search.start_time) + (llm.end_time - llm.start_time)`.
If they don't land close, that's a sign of a wiring bug — a span not
closing where expected, or a step happening outside any span — not a
sign the pipeline itself is doing something unusual.

### Non-determinism as a thing to test, not assume

Q6 asks whether input tokens vary across 4 identical runs of the same
query. The naive expectation is "no" — `minsearch`'s keyword index is
a deterministic TF-IDF-style scorer over an already-built, static
index, so the same query string should retrieve the same documents in
the same order every time, producing an identical prompt and token
count. But "should be identical" is a hypothesis about the pipeline's
architecture, not a guarantee — the only way to actually know is to
run it four times and look, the same discipline Module 4's central
lesson taught (intuition is a hypothesis generator, not a verification
method) applied to a different kind of claim: not "is this design
good" but "is this system actually deterministic."

### Two passes, not a mistake to erase

The real homework's own opening line: "In the module we built all of
this by hand ... In this homework, we will explore an alternative:
OpenTelemetry." That's the exact pattern this session ended up
following, just by accident rather than design — a hand-rolled
`Span`/`Trace`/`SpanRecorder` tracer was built first (while working
from a stale cached copy of the homework file that appeared to show no
OTel requirement), then the real OpenTelemetry implementation replaced
it once the live file was actually read. The hand-rolled pass wasn't
wasted: building the smallest possible version of "a timed unit of
work, nested in a tree" by hand first made the real API
(`start_as_current_span`, `ReadableSpan`, exporters) immediately
legible rather than a pile of new vocabulary — the same value the
course gets from having students hand-build metrics tracking (lesson
04) before naming Langfuse and Arize Phoenix. The graded answers,
though, only come from the real OTel run.

---

## Connections to Real Projects (incl. the Civil Liberties Knowledge Assistant)

- **The subclass-and-override pattern generalizes directly to an
  agent.** `RAGTraced` overrides the same seam `RAGWithMetrics` did
  (lesson 04) — an agent with multiple tool calls would extend this the
  same way: one span per tool call, nested under a parent span for the
  whole agent turn.
- **Directly informs `project/project_monitoring_plan.md`'s "what to
  capture per request" section.** That doc already lists citations and
  an evidence-thinness flag as project-specific additions to the
  course's own five-item capture list. OpenTelemetry spans are a
  natural home for those too — e.g., a `citation_check` span wrapping
  whatever step verifies a citation against corpus content, timed and
  attributed the same way `llm` is here, exported to whatever backend
  the project eventually uses (SQLite for a prototype, a real
  collector/backend like Jaeger or Tempo for production — see the
  homework's own "Going further" section).
- **The judge-latency pitfall (lesson 09, already in
  `03_common_pitfalls.md` #4) is reinforced, not contradicted, by this
  homework's design.** No `judge` span exists here because an automated
  judge call is a real latency/cost add-on, not a free part of the core
  `rag()` path — consistent with that pitfall note's own reasoning.
- **Auto-instrumentation is the realistic production path**, per the
  homework's own "Going further" section:
  `opentelemetry-instrumentation-openai` and similar libraries add LLM
  spans automatically, no manual subclassing required. Worth knowing
  the manual version (this homework) before reaching for that — same
  reasoning as building `RAGTraced` by hand before trusting an
  auto-instrumentation library to do it invisibly.

---

## Lessons Learned

- A trace is the smallest unit of "online evaluation" this module ever
  produces — smaller than a dashboard, smaller than an aggregate
  metric, down to one single request's internal shape. Worth treating
  as a debugging tool in its own right (which sub-step is slow, right
  now, for this one query), not just dashboard raw material.
- Span export order is child-first, not parent-first — a real,
  verified OpenTelemetry behavior (not an assumption), worth knowing
  before eyeballing console output or a spans table for the first
  time.
- A parent span's own duration is a free correctness check on the
  instrumentation: it should land close to the sum of its children's
  durations. If it doesn't, that's a wiring bug, not an exotic finding
  about the pipeline.
- The corpus underneath a pipeline matters more than the pipeline
  *shape* — full unchunked lesson pages vs. FAQ-snippet context change
  Q2's answer by roughly 10x even though `search → prompt → llm` looks
  identical either way. Not a detail to assume from a similar-looking
  earlier module.
- **Primary sources can be stale without looking stale.** The single
  biggest error this round: `raw.githubusercontent.com` served a
  cached `## Homework: TODO` placeholder on every fetch for a stretch,
  even after the real file had gone live — indistinguishable from the
  file genuinely not being ready yet unless checked against the
  rendered `github.com` page or fetched with a cache-busting query
  parameter. Worth treating "this file looks unfinished" and "this
  file is unfinished" as separate claims going forward, not the same
  one.

---

## Key Takeaways

- Trace = one request's full call graph; span = one timed unit of work
  inside it, possibly nested — OpenTelemetry tracks nesting
  automatically via context, no manual parent-linking needed.
- Register `TracerProvider` and the tracer *before* importing/using the
  code you're instrumenting, so nothing creates a span before the
  provider exists.
- Spans export in finish order (child-first), not start order — don't
  read row/print order as call order.
- Sanity-check instrumentation with real span timestamps: a parent's
  duration ≈ sum of its children's, or something's wired wrong.
- Test determinism claims about a pipeline the same way you'd test any
  other claim about it: run it and look, don't assume from the
  architecture alone.
- Check whether a source file is actually current, not just whether it
  looks finished — a CDN cache can serve a stale placeholder
  indefinitely.

---

*Submission doc: [monitoring.md](monitoring.md)*
*Full notebook: [monitoring.ipynb](monitoring.ipynb)*
*Course material: [05-monitoring](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring)*