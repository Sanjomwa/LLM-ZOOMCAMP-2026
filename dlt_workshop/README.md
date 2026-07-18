# Workshop: Pulling Traces from a Monitoring Service with dlt

**Course:** LLM Zoomcamp 2026
**Taught by:** Alena Astrakhantseva (dltHub)
**Video:** https://www.youtube.com/watch?v=A0LmmZf-ggM
**Real lesson source:** `cohorts/2026/workshops/dlt/` in
`DataTalksClub/llm-zoomcamp` — 7 lesson files, fetched and read in full
2026-07-18 (not inferred from the video transcript alone).

**Status: understanding-building phase. No code has been run yet.**
Sam has not followed along hands-on — that's the next session. This
folder currently holds notes only: what the workshop teaches, why each
stage exists, and how it connects to Module 5. Do not treat anything
here as a completed implementation.

---

## What this workshop is

Every coding agent (Claude Code, Codex, Copilot) already logs full
session metadata — tokens, models, tool calls — locally as nested
JSONL files. This workshop turns that already-existing, unreadable
data into structured tables and dashboards, using dlt (an open-source
Python data-loading library) driven almost entirely through
natural-language prompts to a coding agent, via dlt's own "AI
workbench" (toolkits + skills + an MCP server).

By the end of the workshop (per the real lesson material) you have:

1. A dlt pipeline loading local Claude Code logs into DuckDB.
2. A marimo dashboard over that data.
3. A REST API pipeline pulling agent traces from a hosted API.
4. A scheduled deployment on the dltHub Platform with a shareable
   dashboard.

## Map

- `PROGRESS.md` — current status: which stage we're on, which homework
  questions are answered. Check this first for "where are we now."
- `notes/00_mental_models.md` — the conceptual shifts worth carrying
  forward, independent of dlt-specific syntax.
- `notes/01_workshop_walkthrough.md` — stage-by-stage: what each part
  builds, why it exists, how it connects to the previous stage, what
  artifact it produces, what consumes that artifact next.
- `notes/glossary.md` — new vocabulary (dlt, DuckDB, marimo, skill vs.
  tool, MCP, toolkits, normalization, playground destination, etc.)
- `homework/homework_notes.md` — the real, live homework (fetched
  directly, not predicted): instrument Module 1's FAQ agent with
  Pydantic Logfire, pull the traces back with dlt, analyze them. Ties
  directly back to Module 5's OpenTelemetry work.

## Connection to Module 5

This workshop's homework is explicit about this: Logfire is "an
alternative" to the hand-rolled OpenTelemetry instrumentation Module 5
already built — same underlying spans/traces model, wrapped in a
Pydantic-native SDK. The genuinely new piece on top is: traces now
live in someone else's cloud, and dlt is the tool for pulling them
back to somewhere queryable locally. See `notes/00_mental_models.md`
#8 for the full connection.
