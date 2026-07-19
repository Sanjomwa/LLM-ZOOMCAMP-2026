# Analysis Plan: claude_logs_pipeline

## Connection
pipeline: claude_logs_pipeline
dataset: claude_logs
destination: duckdb

## Profile Summary
| table | rows | key columns | notes |
|-------|------|-------------|-------|
| sessions | 462 | type, timestamp, session_id, cwd, message__model, message__role, message__usage__* | attachment/tool_use_result kept as JSON (schema cleanup, Stage 2); 5 distinct session_id + null (meta/summary rows) |
| sessions__message__content | 267 | type, text, name (tool name), input__* | child table, one row per content block in an assistant/user message |
| sessions__message__usage__iterations | 175 | input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens | child table, one row per model iteration within a turn |
| sessions__message__content__input__questions | 4 | — | AskUserQuestion tool call inputs, small edge case |
| sessions__message__content__input__questions__options | 10 | — | options for the above |
| sessions__message__content__content | 2 | — | rare nested-content edge case |

No PII columns identified (local dev-machine session logs; `cwd` is a local file path, not personal data).

## Questions
1. [x] How does log/message activity vary over time? → Chart 1
2. [x] What's the breakdown of log entries by type? → Chart 2
3. [x] How many tokens (input vs. output) does each model use? → Chart 3
4. [x] Which project directories generate the most activity? → Chart 4

## Data Gaps
(none)

## Chart 1: Activity Over Time
question: How does log/message activity vary over time?
type: line
x: timestamp (hourly)
y: count(*)
source: sessions

```sql
SELECT
    DATE_TRUNC('hour', timestamp) AS hour,
    COUNT(*) AS events
FROM sessions
GROUP BY 1
ORDER BY 1
```

```altair
alt.Chart(df).mark_line(point=True).encode(
    x=alt.X("hour:T", title="Hour"),
    y=alt.Y("events:Q", title="Log entries"),
    tooltip=["hour:T", "events:Q"]
).properties(title="Activity Over Time")
```

## Chart 2: Message Types Breakdown
question: What's the breakdown of log entries by type?
type: bar
x: type
y: count(*)
source: sessions

```sql
SELECT
    type,
    COUNT(*) AS records
FROM sessions
GROUP BY 1
ORDER BY records DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("records:Q", title="Log entries"),
    y=alt.Y("type:N", sort="-x", title="Type"),
    tooltip=["type:N", "records:Q"]
).properties(title="Message Types Breakdown")
```

## Chart 3: Token Usage by Model
question: How many tokens (input vs. output) does each model use?
type: bar (stacked)
x: message__model
y: sum(input_tokens), sum(output_tokens)
source: sessions

```sql
SELECT message__model AS model, 'input' AS token_type, SUM(message__usage__input_tokens) AS tokens
FROM sessions
WHERE message__model IS NOT NULL
GROUP BY 1, 2
UNION ALL
SELECT message__model AS model, 'output' AS token_type, SUM(message__usage__output_tokens) AS tokens
FROM sessions
WHERE message__model IS NOT NULL
GROUP BY 1, 2
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("model:N", title="Model"),
    y=alt.Y("tokens:Q", title="Tokens", stack="zero"),
    color=alt.Color("token_type:N", title="Token type"),
    tooltip=["model:N", "token_type:N", "tokens:Q"]
).properties(title="Token Usage by Model")
```

## Chart 4: Top Projects by Activity
question: Which project directories generate the most activity?
type: bar
x: cwd
y: count(*)
source: sessions

```sql
SELECT
    cwd,
    COUNT(*) AS records
FROM sessions
WHERE cwd IS NOT NULL
GROUP BY 1
ORDER BY records DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("records:Q", title="Log entries"),
    y=alt.Y("cwd:N", sort="-x", title="Project (cwd)"),
    tooltip=["cwd:N", "records:Q"]
).properties(title="Top Projects by Activity")
```
