# Homework 5: Monitoring — Solutions


**Course:** LLM Zoomcamp 2026 — Module 5


**Full notebook:** `monitoring.ipynb`


**Course material:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring


**Homework instructions:** [DataTalksClub/llm-zoomcamp, cohorts/2026/05-monitoring](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/cohorts/2026/05-monitoring)

---

## Setup

```bash
uv add openai pydantic python-dotenv pandas
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
needs `OPENAI_API_KEY` already in the environment. Importing doesn't
trigger `starter.py`'s own demo query — that only runs under its
`if __name__ == "__main__":` guard.

---

## Approach: instrumenting the RAG pipeline with a tracer

The homework asks for a trace of one RAG call, made of spans. There's
no tracing library used here — a small, dependency-free tracer is built
directly in the notebook: a `Span` dataclass (name, start/end time,
attributes), a `Trace` that holds an ordered list of spans, and a
`SpanRecorder` context manager that times a block and appends the
resulting span to the trace.

`TracedRAG(RAGBase)` adds one method, `rag_traced(query)`, that runs
the same three steps `rag()` already does — `search()`, `build_prompt()`,
`llm()` — wrapping `search()` and `llm()` each in their own span, nested
inside a parent `rag` span that times the whole call. `search()` and
`llm()` themselves are untouched; only the wrapper adds timing.

The trace is returned directly from `rag_traced()` rather than stored
as an attribute on the instance, so nothing about the tracer depends on
only one call being in flight at a time.

---

## Q1. How many spans does the trace produce?

**Answer: 3** (`rag`, `search`, `llm`)

### Why

`rag()` calls exactly two things: `search()` then `llm()`. Wrapping the
whole call in a parent span, plus one child span per sub-call, gives 3
spans total. `build_prompt()` isn't spanned separately — it's pure
string formatting with no meaningful duration to track.

### How

```python
num_spans = len(trace.spans)
print("Q1 - number of spans:", num_spans)
```
```
Q1 - number of spans: 3
```

---

## Q2. How many input tokens do we see for the LLM call?

**Answer: 7,111**

### Why

Read directly off `response.usage.input_tokens` on the `llm` span.

### How

```python
llm_span = next(s for s in trace.spans if s.name == "llm")
input_tokens = llm_span.attributes["input_tokens"]
print("Q2 - llm span input_tokens:", input_tokens)
```
```
Q2 - llm span input_tokens: 7111
```

### What to remember

The retrieved context is 5 full, unchunked lesson pages (`build_context`
concatenates each result's entire `content`), not short snippets — that's
what pushes the token count into the thousands rather than the hundreds.

---

## Q3. Roughly how long does the LLM call take?

**Answer: 6,960.3ms** → the "Over 2000ms" bucket.

### Why

Read directly off the `llm` span's `duration_ms` — wall-clock time
around the request.

### How

```python
llm_duration_ms = llm_span.duration_ms
print("Q3 - llm span duration_ms:", round(llm_duration_ms, 1))
```
```
Q3 - llm span duration_ms: 6960.3
```

### What to remember

~7 seconds is largely a function of the ~7,100 input tokens the model
has to process — a direct cost of retrieving full lesson pages instead
of smaller chunks as context.

---

## Q4. Which span names appear in the spans table?

**Answer: `rag`, `search`, and `llm`**

### Why

The built-in judge (`evaluate_relevance`) is a separate call made after
`rag()` returns, not part of `rag()` itself, so no `judge` span is
produced by this trace.

### How

```python
span_names = [s.name for s in trace.spans]
print("Q4 - span names:", span_names)
```
```
Q4 - span names: ['rag', 'search', 'llm']
```

---

## Q5. Excluding the rag span, which span type takes the most total time?

**Answer: `llm`** — roughly 64x slower than `search` (6,960.3ms vs.
108.9ms).

### Why

`search()` runs in-process against an already-built in-memory index —
no network call. `llm()` is a network round-trip to the OpenAI API
carrying ~7,100 tokens of context. Network latency to a hosted model
processing a large prompt dominates an in-memory keyword search by a
wide margin.

### How

```python
non_rag = [s for s in trace.spans if s.name != "rag"]
by_duration = sorted(non_rag, key=lambda s: s.duration_ms, reverse=True)
print("Q5 - span durations excluding rag:",
      [(s.name, round(s.duration_ms, 1)) for s in by_duration])
```
```
Q5 - span durations excluding rag: [('llm', 6960.3), ('search', 108.9)]
```

---

## Q6. How much do input tokens vary across 4 runs of the same query?

**Answer: Identical (0.00% variance)**

### Why

The keyword search index is a deterministic scorer over a static,
already-built index — the same query text retrieves the same documents
in the same order every time, producing an identical prompt and an
identical input token count.

### How

```python
runs = []
for i in range(4):
    _, run_trace = assistant.rag_traced(query)
    run_llm_span = next(s for s in run_trace.spans if s.name == "llm")
    runs.append(run_llm_span.attributes["input_tokens"])

print("Q6 - input_tokens across 4 runs:", runs)

mean_tokens = statistics.mean(runs)
max_dev = max(abs(t - mean_tokens) for t in runs)
pct_variance = (max_dev / mean_tokens) * 100 if mean_tokens else 0
print(f"Q6 - max deviation from mean: {pct_variance:.2f}%")
```
```
Q6 - input_tokens across 4 runs: [7111, 7111, 7111, 7111]
Q6 - max deviation from mean: 0.00%
```

---

## Summary: All Six Answers

| Q | Question | Answer |
|---|----------|--------|
| 1 | Span count | 3 (`rag`, `search`, `llm`) |
| 2 | LLM input tokens | 7,111 |
| 3 | LLM call duration | 6,960.3ms (Over 2000ms) |
| 4 | Span names | `rag`, `search`, `llm` |
| 5 | Slowest non-rag span | `llm` (64x slower than `search`) |
| 6 | Input-token variance across 4 runs | Identical (0.00%) |

The LLM call is the clear bottleneck in this pipeline — a direct
consequence of retrieving full lesson pages as context rather than
smaller chunks.

---

*Full notebook: [monitoring.ipynb](monitoring.ipynb)*
*Course material: [05-monitoring](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/05-monitoring)*