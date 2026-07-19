# Analysis Plan: agent_traces

## Connection
pipeline: agent_traces
dataset: traces
destination: duckdb

## Profile Summary
| table | rows | key columns | notes |
|-------|------|-------------|-------|
| logs | 20000 | index (PK), type, timestamp, session_id, cwd, git_branch, message__model, usage__input_tokens, usage__output_tokens | flat schema, no schema pollution (unlike Stage 1's local logs) |
| logs__message__content | 19668 | type, text/tool fields | child table for nested `message.content`; type breakdown: text 13024, tool_use 6644 |

No PII columns identified (synthetic test-API data).

## Questions
1. [x] What's the breakdown of logs by type? → Chart 1
2. [x] How does log activity vary over time, by type? → Chart 2
3. [x] How is work distributed across git branches? → Chart 3
4. [x] How many output tokens does each git branch consume? → Chart 4
5. [x] What's the breakdown of message content block types? → Chart 5
6. [x] How are messages distributed across sessions? → Chart 6

## Data Gaps
(none)

## Chart 1: Logs by Type
question: What's the breakdown of logs by type?
type: bar
x: type
y: count(*)
source: logs

```sql
SELECT type, COUNT(*) AS records
FROM logs
GROUP BY 1
ORDER BY records DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("type:N", sort="-y"),
    y="records:Q",
    color="type:N",
    tooltip=["type:N", "records:Q"],
).properties(title="Logs by Type")
```

## Chart 2: Log Activity per Hour by Type
question: How does log activity vary over time, by type?
type: line
x: timestamp (hourly)
y: count(*), grouped by type
source: logs

```sql
SELECT
    DATE_TRUNC('hour', timestamp) AS hour,
    type,
    COUNT(*) AS records
FROM logs
GROUP BY 1, 2
ORDER BY 1, 2
```

```altair
alt.Chart(df).mark_line().encode(
    x="hour:T",
    y="records:Q",
    color="type:N",
    tooltip=["hour:T", "type:N", "records:Q"],
).properties(title="Log Activity per Hour by Type")
```

## Chart 3: Logs by Git Branch
question: How is work distributed across git branches?
type: bar
x: git_branch
y: count(*)
source: logs

```sql
SELECT git_branch, COUNT(*) AS records
FROM logs
GROUP BY 1
ORDER BY records DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("git_branch:N", sort="-y"),
    y="records:Q",
    color="git_branch:N",
    tooltip=["git_branch:N", "records:Q"],
).properties(title="Logs by Git Branch")
```

## Chart 4: Output Tokens by Git Branch
question: How many output tokens does each git branch consume?
type: bar
x: git_branch
y: sum(usage__output_tokens)
source: logs

```sql
SELECT git_branch, SUM(usage__output_tokens) AS output_tokens
FROM logs
WHERE usage__output_tokens IS NOT NULL
GROUP BY 1
ORDER BY output_tokens DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("git_branch:N", sort="-y"),
    y="output_tokens:Q",
    color="git_branch:N",
    tooltip=["git_branch:N", "output_tokens:Q"],
).properties(title="Output Tokens by Git Branch")
```

## Chart 5: Message Content Block Types
question: What's the breakdown of message content block types?
type: bar
x: type
y: count(*)
source: logs__message__content

```sql
SELECT type, COUNT(*) AS blocks
FROM logs__message__content
GROUP BY 1
ORDER BY blocks DESC
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("type:N", sort="-y"),
    y="blocks:Q",
    color="type:N",
    tooltip=["type:N", "blocks:Q"],
).properties(title="Message Content Block Types")
```

## Chart 6: Distribution of Messages per Session
question: How are messages distributed across sessions?
type: bar
x: msgs_per_session
y: count of sessions
source: logs

```sql
SELECT cnt AS msgs_per_session, COUNT(*) AS sessions
FROM (
    SELECT session_id, COUNT(*) AS cnt
    FROM logs
    GROUP BY 1
)
GROUP BY 1
ORDER BY 1
```

```altair
alt.Chart(df).mark_bar().encode(
    x=alt.X("msgs_per_session:O", title="messages per session"),
    y=alt.Y("sessions:Q", title="number of sessions"),
    tooltip=["msgs_per_session:O", "sessions:Q"],
).properties(title="Distribution of Messages per Session")
```
