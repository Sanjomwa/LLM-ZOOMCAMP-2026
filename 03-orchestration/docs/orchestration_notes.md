# Module 3: AI Orchestration with Kestra — Engineering Notes

**Course:** LLM Zoomcamp 2026
**Module:** 03 — AI Orchestration
**Stack:** Kestra, Gemini, RAG, Agents, Multi-Agent Systems

---

## The Central Idea

Every technique in this module is an answer to the same question: *how do you get an LLM to produce useful output instead of plausible-sounding noise?*

The answer is always the same: give it better context. The techniques just differ in how that context is acquired, structured, and managed. Context engineering is not a single lesson in the module — it is the thread that connects every lesson. Everything else is implementation detail.

This shifted how I think about LLM systems. Before this module, I thought the primary design decisions were model selection and prompt phrasing. After it, I think those are secondary. The primary decision is: *what information does the model receive, from where, and how?* That question is the architecture.

---

## Why Generic LLMs Fail at Domain Tasks

The module opens with a deliberate experiment: give ChatGPT a Kestra-specific prompt in a private window and observe what happens. The result is syntactically convincing YAML that contains outdated plugin names, invented property names, and deprecated patterns that stopped working in previous versions.

This is not a GPT failure — it is a training data failure. GPT was trained on Kestra documentation that existed at training time. Since then, plugins have been renamed, APIs have changed, and best practices have evolved. The model cannot know what it was never shown.

The broader point applies to any domain-specific system: a model trained on the general internet does not have reliable knowledge of your organisation's data schemas, your API's current authentication patterns, or the civil liberties reporting conventions that your RAG system needs to understand. Generic knowledge is not the same as current, grounded knowledge.

The practical consequence: **model selection is a second-order decision. Context design is the first-order decision.** A smaller model with the right context will outperform a larger model working from stale training data. The Copilot experiment makes this concrete: Kestra's Copilot uses the same underlying model capabilities as ChatGPT, but retrieves current plugin documentation before generating. The output is directly usable. ChatGPT's output is not.

---

## Context Engineering to RAG: The Natural Progression

Once you accept that context determines output quality, the next question is: where does context come from?

For Kestra's AI Copilot, the answer is: embedded plugin documentation, valid property names, and version-specific best practices, retrieved automatically when you invoke the Copilot. You describe what you want — "create a flow that downloads a CSV and loads it to BigQuery" — and the Copilot generates YAML that references real, current task types and correct property schemas. The "5% rule" that the module introduces is honest: Copilot handles the 95% of the work that is just knowing the right plugin names. You handle the 5% that is specific to your environment, your secrets, your error handling preferences.

This is context engineering in its simplest form: make sure the model has the relevant documentation before it generates. But it works because the context is static — the plugin documentation changes slowly and can be embedded directly.

RAG exists for when context cannot be embedded in advance because it is too large, too dynamic, or too specific to the query. If you need to answer "what did Kestra release in version 1.1?" you cannot embed every possible question's answer at design time. Instead, you store the release notes in a vector index and retrieve the relevant passages at query time.

The module's Q2 experiment makes the RAG value proposition concrete. The non-RAG flow produces output that is "vague, generic, or fabricated — the model guesses from training data." The RAG flow retrieves the actual release notes and grounds the answer in evidence. Same model, same prompt structure, completely different reliability. The difference is not intelligence. It is information access.

**This is the lesson that transfers directly to the Civil Liberties Evidence Assistant.** The assistant needs to answer questions like "what evidence exists for network interference in Kenya?" No general-purpose LLM has reliable, current, specific knowledge of OONI measurements and Access Now reporting. The answer must come from retrieved documents. The architecture is determined by that constraint, not by any property of the LLM itself.

---

## From RAG to Agents: When Static Retrieval Is Not Enough

RAG solves the problem of grounding answers in specific documents. But RAG assumes something: that you know what to retrieve before you start. The query goes in, retrieval happens, the result is passed to the model, an answer comes out. That sequence is fixed.

This works well for factual lookup questions. It breaks down when the right retrieval strategy depends on what you discover mid-task. A research question like "compare OONI measurements with Access Now reporting on Uganda" may require retrieving OONI reports first, understanding what methodology they use, then retrieving Access Now reports, then retrieving a methodology explanation document to reconcile the two. The retrieval sequence cannot be predetermined — it depends on what each retrieval returns.

This is the problem that agents solve. Instead of a fixed sequence, an agent operates on a reasoning loop: observe the goal, decide what tool to use, execute it, observe the result, decide what to do next. The Kestra `AIAgent` plugin implements this loop for you — you define the goal, the tools, and optionally a system message, and Kestra drives the loop until the model produces a final answer with no more tool calls.

The module's web research agent demonstrates this concretely. The agent receives a research prompt, decides to use Tavily web search, evaluates the results, decides whether to search again with different terms, synthesises the findings, and saves the report. You specified the goal. The agent determined the path.

The shift from RAG to agents is not an upgrade — it is a trade. Agents gain flexibility; they lose predictability. A RAG flow will produce deterministic results on identical inputs. An agent may search with different queries, find different documents, and produce different conclusions across runs. For research tasks, this flexibility is valuable. For production data pipelines that must be auditable, it is a liability.

---

## Multi-Agent Systems: Decomposing Complexity

Single agents work well when a task has one kind of reasoning to do. Complex tasks often require several different kinds: one agent is good at gathering information from the web; another is good at synthesising findings into a structured report. Making one agent do both produces a generalist that does neither particularly well.

Multi-agent systems solve this through specialisation. The module's competitor research example uses two agents: a Research Agent equipped with web search tools, whose sole job is finding factual current information, and an Analyst Agent whose sole job is synthesising what the Research Agent returns into a structured output. The Analyst Agent calls the Research Agent as a tool, the same way it would call a database lookup.

The key design insight is that `AIAgent` can be registered as a tool inside another agent. This creates composable agent systems without requiring a new architectural pattern — the mechanism is the same as any other tool call.

The main benefit of this pattern is debuggability. When the system produces a wrong answer, you can isolate whether the failure was in the Research Agent (bad retrieval), the Analyst Agent (bad synthesis), or the interface between them (misspecified tool output format). That isolation is valuable and becomes increasingly important as systems grow.

The main cost is multiplicative LLM usage. Two agents means at least two LLM calls per execution, often more as each agent may loop internally. Token costs scale with agent count and loop depth. The module's cost table makes this tangible: output tokens at the standard Gemini tier cost 6x more than input tokens. Agents that produce verbose outputs can become expensive quickly. `maxOutputTokens` is not just a configuration option — it is a cost control mechanism.

---

## Token Usage as a Design Tool

The homework's Q3, Q4, and Q5 experiments — which require reading execution logs and comparing output token counts — teach something more important than the specific numbers. They demonstrate that token usage is a direct, measurable consequence of prompt design.

Switching from a "short" to a "long" summary prompt produced 2–5x more output tokens. Changing one output sentence to three produced 2–4x more tokens. These are not random fluctuations. They are predictable, proportional responses to changes in the output specification.

This means token counts are a design signal, not just a billing artifact. When I see a 5x increase in output tokens between two agent runs on similar inputs, I know to look at whether the prompt's output constraint changed, whether the agent looped more times than expected, or whether a tool returned unexpectedly large results. The execution logs tell this story if you know to read them.

For the Civil Liberties Evidence Assistant, this matters practically. A RAG flow that returns full synthesis across multiple documents will consume significantly more tokens than one that returns focused factual answers. That difference compounds across many queries. Designing with token budgets from the start — rather than discovering costs after deployment — is the professional approach.

---

## Orchestration: The Thing That Makes Systems Observable

Kestra is the orchestration layer in this module, but the lesson about orchestration generalises beyond Kestra. The question orchestration answers is not "how do I connect these components?" — you can connect them with Python functions. The question is: *how do I see what is happening inside a running system, and how do I recover when something fails?*

Without orchestration, a multi-step LLM pipeline is a black box. You see the input and the final output. If the output is wrong, you do not know whether the retrieval step returned poor results, whether the synthesis step misread good results, or whether a token limit truncated the context midway through. With orchestration, every task in every flow produces structured execution logs with timestamps, token counts, tool call records, and output values — all inspectable after the fact.

The `logRequests: true` / `logResponses: true` configuration options in the `AIAgent` task are a specific example of this principle. When an agent produces an unexpected answer, you can see exactly what the model received and what it returned at every reasoning step. That visibility is what separates a debuggable system from a mystery.

The implication for architecture: **orchestration is not the goal. It is what makes the goal achievable at scale.** The goal is grounded, reliable answers. Orchestration is the infrastructure that makes it possible to verify reliability, diagnose failures, and maintain the system over time. Building orchestration from the start — even for a simple pipeline — creates the visibility foundation that everything else depends on.

---

## When Not to Use Any of This

The module's best practices section is the most underappreciated part of the lesson. The table that maps scenarios to techniques is not just a guide to which tool to reach for. It is a guide to when to put the tools away.

**Use traditional deterministic task-based workflows when:**
- The sequence of steps is fixed and known
- Results must be identical across identical inputs (reproducibility)
- Outputs must be auditable to a regulator, compliance officer, or QA process
- Cost per run must be predictable
- The failure mode of non-determinism is unacceptable

**Use AI agents when:**
- The right sequence of steps cannot be predetermined
- Decisions genuinely depend on what is discovered mid-task
- Flexibility matters more than reproducibility
- The task is exploratory by nature

For the Civil Liberties Evidence Assistant specifically: the ingestion pipeline is a deterministic process. Download, archive, extract, validate, chunk — every step has a fixed input/output contract and must produce the same results on the same inputs across every run. The evaluation framework is equally deterministic: the same question against the same corpus should return the same retrieval results and the same judge scores. Neither of these should be agentic.

The retrieval and synthesis layer — where the system answers open-ended questions about civil liberties evidence — is where agent reasoning adds genuine value. Which documents to retrieve, how to combine them, when to acknowledge contradictory evidence: these decisions depend on the specific question and the specific corpus state. That is the appropriate place for dynamic tool use.

The mistake would be applying agent complexity uniformly rather than precisely. An agent-driven ingestion pipeline would be harder to test, harder to debug, and impossible to evaluate rigorously. A deterministic retrieval pipeline would be unable to handle the genuine ambiguity in civil liberties research questions.

---

## The Architecture This Module Clarifies

Reading this module in sequence with Modules 1 and 2, the full system architecture becomes visible:

```
Documents
    ↓
Ingestion (deterministic pipeline — never agentic)
    ↓
Chunking + Embeddings
    ↓
Vector Store
    ↓
                    ← User question
Retriever (RAG) → selects relevant chunks
    ↓
[Optional: Agent loop if multi-hop reasoning required]
    ↓
LLM Generation (grounded in retrieved context)
    ↓
Grounded Answer + Citations + Evidence Quality Indicators
    ↓
Orchestration layer records: token usage, retrieval hits, latency, cost
```

Orchestration wraps the whole system. It is not one of the stages — it is the operational infrastructure that makes every stage observable, restartable, and measurable.

Context engineering is not a stage either. It is the design philosophy that governs every decision about what information flows into each stage. Better context at every stage produces better outputs at every stage, and that is more valuable than choosing a more capable model.

---

## What to Return to When Building the CLIO Integration

When the Civil Liberties Evidence Assistant eventually becomes the AI layer of the CLIO platform, the lessons from this module that will matter most:

**Observability from the start.** Log token usage, retrieval results, and synthesis decisions from the first working version. Retrofitting observability into a running production system is significantly harder than building it in.

**Determinism for the data layer, agent reasoning for the query layer.** The corpus ingestion pipeline must be reproducible. The question-answering layer can and should use agent reasoning for multi-hop evidence synthesis.

**Context engineering over model selection.** When retrieval quality is poor, improve the corpus, the chunking strategy, or the retrieval mechanism before considering a model upgrade. The model is rarely the bottleneck.

**Token budget as a system constraint.** Design prompts and output specifications with token counts in mind. The token cost table in the Best Practices lesson is worth revisiting when making decisions about output verbosity and agent loop depth.

**The 5% rule applies everywhere.** Generated flows, retrieved answers, synthesised reports — AI handles the 95% that is pattern-matching. The 5% that requires your specific domain knowledge, your specific corpus design decisions, and your specific quality standards is your responsibility. Design systems that make that 5% easy to apply and easy to audit.