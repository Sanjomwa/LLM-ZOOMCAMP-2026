# dlt Workshop — Course Progress

**This file is git-tracked (not gitignored).** It's the durable,
authoritative record of where we are in the workshop and homework —
it survives session restarts, new machines, and clean clones on
purpose. Update it every time a stage or question status changes.
Read it at the start of every session before anything else
(see `CLAUDE.md` → Session start checklist).

Last updated: **2026-07-18**

---

## Workshop stages

Reference: `notes/01_workshop_walkthrough.md`. Status reflects actual
work done in *this* repo, not just notes written about the lesson.

| Stage | What it builds | Status |
|---|---|---|
| 0 — Setup | `uvx dlthub-init` scaffolding (`.dlt/`, `.mcp.json`, `.claude/`, venv) | ✅ Done — workspace scaffolded |
| 1 — Local logs → filesystem pipeline | Claude Code JSONL logs → DuckDB via filesystem source | 🔶 **In progress — current stage** |
| 2 — Debug + schema cleanup + first dashboard | debug-pipeline skill, schema pollution fix, marimo dashboard | ⬜ Not started |
| 3 — Hosted API as source | REST API pipeline (fake test API → DuckDB) | ⬜ Not started |
| 4 — Deploy to cloud | `dlthub login`/`connect`, deploy pipeline, `playground` destination | ⬜ Not started |
| 5 — Deploy dashboard + schedule | Dashboard as interactive job, cron trigger | ⬜ Not started |
| 6 — Recap | No build — conceptual recap only | ⬜ N/A until Stage 5 done |

**Where exactly we are on Stage 1:** notes/README/mental-models/glossary
have been written (2026-07-18, from the real lesson files + video
transcript). **No pipeline code has been run yet.** `dlthub ai status`
confirms no toolkit is installed yet — the router skill hasn't been
triggered because we haven't yet asked the agent to build the
pipeline.

**Next concrete action for Stage 1:** ask the agent, in plain English,
to build a dlt pipeline loading local Claude Code logs (raw JSON) into
DuckDB. This is expected to trigger the router skill to install the
`filesystem-pipeline` toolkit (see `.claude/rules/init-dlthub-workspace.md`
toolkit table). Confirm with `uv run dlthub ai status` afterward that
the toolkit landed.

---

## Homework

Reference: `dlt_homework_materials/homework_notes.md`.

**Status: not started.** Separate track from the workshop stages above
— it continues Module 1's FAQ agent rather than repeating the
workshop's own pipelines.

| Step | Status |
|---|---|
| Read `agent.py`/`main.py` (Pydantic AI rewrite of Module 1's agent) | ⬜ |
| Get Logfire account + write token, configure `.env` | ⬜ |
| Run agent once with "How do I run Ollama locally?", inspect trace in Logfire UI | ⬜ |
| Q1 — count spans in that trace | ⬜ Not answered |
| Build dlt pipeline pulling Logfire traces → DuckDB (ready-made Logfire REST source context) | ⬜ |
| Q2 — count tables in `agent_traces` schema | ⬜ Not answered |
| Q3 — sum `gen_ai.usage.input_tokens` across spans, pick range | ⬜ Not answered |
| Submit at `courses.datatalks.club/llm-zoomcamp-2026/homework/dlt` | ⬜ |

Deadline: not yet confirmed — check the course-management site link
above (wasn't open yet as of 2026-07-18).

---

## How to update this file

When a stage or homework step's status changes, edit the relevant row
directly (⬜ → 🔶 → ✅) and bump **Last updated** at the top. Keep the
"where exactly we are" / "next concrete action" prose under Stage 1
(or whichever stage is current) current — that prose, not just the
table, is what a fresh session actually needs to pick up correctly.
