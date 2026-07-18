# Homework 5: Monitoring — Solutions

**Course:** LLM Zoomcamp 2026 — Module 5

**Full notebook:** `monitoring.ipynb`

**Course material:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring

**Homework instructions:** [DataTalksClub/llm-zoomcamp, cohorts/2026/05-monitoring/homework.md](https://github.com/DataTalksClub/llm-zoomcamp/blob/main/cohorts/2026/05-monitoring/homework.md)

---

## Setup

```bash
uv add gitsource minsearch openai python-dotenv opentelemetry-api opentelemetry-sdk
```

Download the starter files:

```bash
PREFIX=https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main/cohorts/2026/05-monitoring
wget ${PREFIX}/rag_helper.py
wget ${PREFIX}/starter.py
```

`starter.py` is imported as a module (`import starter`) rather than run
directly — its module-level code builds the search index
(`GithubRepositoryDataReader` over the 72 course lesson pages, commit
`8c1834d`) and the OpenAI client. `load_dotenv()` runs before
`import starter`, since `starter.py`'s own `client = OpenAI()` line
needs `OPENAI_API_KEY` already in the environment.

---

## Approach: instrumenting the RAG pipeline with OpenTelemetry

A `TracerProvider` is set up with a `ConsoleSpanExporter` before
`starter` is imported, so any spans created anywhere are ready to be
captured from the start:

```python
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(console_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("llm-zoomcamp")
```

`RAGTraced(RAGBase)` overrides `rag()`, `search()`, and `llm()`, wrapping
each in its own span via `tracer.start_as_current_span(...)`. Span
nesting is automatic: when `rag()` calls `self.search()` from inside its
own span's `with` block, `search`'s span becomes a child of `rag`
without any manual parent-linking. Token usage and cost are attached to
the `llm` span as attributes (`span.set_attribute(...)`).

For persistence, a custom `SQLiteSpanExporter(SpanExporter)` writes each
finished span's name, start/end time, and attributes to a `spans` table
in `traces.db`, added as a second span processor alongside the console
one.

---

## Q1. First trace — how many spans does the trace produce?

**Answer:** 3

### Why

`RAGTraced.rag()` wraps `search()` and `llm()`, each producing its own
span nested under `rag`'s. Three method calls, three spans.

### How

```python
num_spans = len(console_exporter.spans)
print("Q1 - number of spans:", num_spans)
```

### What to remember

OpenTelemetry exports finished spans in the order they *complete*, not
the order they started — children finish before their parent, so the
captured list comes back as `[search, llm, rag]`, not `[rag, search,
llm]`. The count and the set of names are unaffected; only the order is
different from what a naive parent-first assumption would predict.

---

## Q2. Capturing metrics as span attributes — how many input tokens?

**Answer:** 7,111 (closest option: 7,000)

### Why

`response.usage.input_tokens` is read inside `llm()` and attached to the
span with `span.set_attribute("input_tokens", ...)` — attributes are
OpenTelemetry's mechanism for putting arbitrary data (tokens, cost) on a
span, not just timing.

### How

```python
llm_span = next(s for s in console_exporter.spans if s.name == "llm")
input_tokens = dict(llm_span.attributes)["input_tokens"]
print("Q2 - llm span input_tokens:", input_tokens)
```

### What to remember

The retrieved context is 5 full, unchunked lesson pages, not short
snippets — that's what pushes the token count into the thousands.

---

## Q3. Span timing — how long does the LLM call take?

**Answer:** Over 2000ms (measured: `llm` = 9,619.7ms, `search` = 126.5ms)

### Why

Each `ReadableSpan` carries `start_time`/`end_time` as nanosecond
timestamps; duration is `(end_time - start_time) / 1_000_000` for
milliseconds.

### How

```python
for s in console_exporter.spans:
    duration_ms = (s.end_time - s.start_time) / 1_000_000
    print(f"Q3 - span '{s.name}' duration_ms: {duration_ms:.1f}")
```

### What to remember

The LLM call dominates by roughly two orders of magnitude over search
(9,619.7ms vs. 126.5ms on this run) — a network round-trip carrying
several thousand tokens of context vs. an in-process index lookup.
Later runs in this notebook show shorter `llm` durations (call latency
varies run to run), but all land well past the 2000ms threshold.

---

## Q4. Saving traces to SQLite — which span names appear?

**Answer:** `rag`, `search`, and `llm`

### Why

The custom `SQLiteSpanExporter` inserts one row per finished span into
`traces.db`'s `spans` table, so every span name that was created shows
up as a row.

### How

```python
df = pd.read_sql("SELECT * FROM spans", sqlite3.connect("traces.db"))
span_names = sorted(df["name"].unique().tolist())
print("Q4 - span names in traces.db:", span_names)
```

---

## Q5. Querying trace data — excluding rag, which span type is slowest?

**Answer:** `llm` (2,604.5ms total vs. `search`'s 35.1ms, on the run measured for this question)

### Why

`search()` runs in-process against an already-built index; `llm()` is a
network round-trip carrying several thousand tokens of context. Summing
duration by span name (excluding the `rag` parent, whose duration
already includes both children) shows which step actually dominates
total time.

### How

```python
df["duration_ms"] = (df["end_time"] - df["start_time"]) / 1_000_000
totals = df[df["name"] != "rag"].groupby("name")["duration_ms"].sum()
print(totals)
```

---

## Q6. Token stability across runs

**Answer:** They're identical (7,111 input tokens on all 4 runs, 0.00% deviation)

### Why

The same query run four times through the same static, already-built
search index should retrieve the same documents in the same order every
time — producing an identical prompt and an identical input token
count, if the retrieval step is genuinely deterministic.

### How

```python
for i in range(3):
    assistant.rag(query)

df = pd.read_sql("SELECT * FROM spans WHERE name = 'llm'", sqlite3.connect("traces.db"))
print("Q6 - input_tokens per run:", df["input_tokens"].tolist())
```

---

## Summary: All Six Answers

| Q | Question | Answer |
|---|----------|--------|
| 1 | Span count | 3 |
| 2 | LLM input tokens | 7,111 (→ 7,000 bucket) |
| 3 | LLM call duration | Over 2000ms (9,619.7ms) |
| 4 | Span names | `rag`, `search`, `llm` |
| 5 | Slowest non-rag span | `llm` |
| 6 | Input-token variance across 4 runs | They're identical (0.00%) |

---

*Full notebook: [monitoring.ipynb](monitoring.ipynb)*
*Course material: [05-monitoring](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring)*