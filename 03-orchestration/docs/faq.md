# Module 3 (AI Orchestration with Kestra) — FAQ Additions

These are questions that came up while working through the Module 3 homework — specifically around context engineering, RAG flows, token usage, and when to use agents vs. traditional workflows. None of these touch graded answers, just the concepts and reasoning that tripped things up along the way.

---

### Q: Why does Kestra's AI Copilot generate better flows than a general-purpose assistant given the same prompt?

**A:** It is not a model capability difference. The Copilot is grounded in current Kestra plugin documentation, valid property names, and version-specific schemas before it generates anything. A general-purpose assistant like ChatGPT works from training data, which may reference outdated plugin types, renamed properties, or patterns that stopped working in previous versions.

The output looks plausible either way. The difference is whether the plugin names and property keys it uses actually exist in your running version of Kestra.

---

### Q: What is the "5% rule" mentioned in the AI Copilot lesson?

**A:** The idea that Copilot handles roughly 95% of a flow — the boilerplate structure, correct plugin types, valid property schemas — and you supply the remaining 5% that is specific to your environment: your secrets, your GCS bucket names, your retry preferences, your error handling logic.

It is a practical framing for how to use Copilot effectively. Generate the structure, then make the targeted adjustments rather than building from scratch or trying to specify every detail in the initial prompt.

---

### Q: The RAG flow returned a grounded answer but the non-RAG flow returned something generic. Does this mean the model is different?

**A:** No. The model is the same in both flows. The difference is what information the model receives before generating.

Without retrieval, the model generates from its training distribution — which may not include current or specific Kestra documentation. With retrieval, the relevant documentation is fetched and included in the context. The model then generates from that grounded context rather than from memory.

This is the core RAG mechanism: the model's output quality is determined by what it receives, not by its intrinsic knowledge of the domain.

---

### Q: Why do output tokens matter? I thought the important cost was input tokens.

**A:** Both matter, but output tokens are typically priced higher than input tokens and are directly controlled by your prompt design.

At standard Gemini pricing, output tokens cost significantly more per million than input tokens. Output token count is also a direct function of what you ask for — requesting a "long" summary vs. a "short" one, or "three sentences" vs. "one sentence", produces proportionally more output tokens. This means prompt design is a cost control lever, not just a quality lever.

The homework questions on token usage demonstrate this: changing the output specification produces predictable, proportional changes in token count. In a production system running many queries per day, those multipliers compound into real cost differences.

---

### Q: Why would you ever use traditional task-based workflows instead of AI agents?

**A:** Several reasons, depending on the use case:

**Determinism.** Traditional workflows produce identical outputs on identical inputs. Agents may search with different terms, call tools in different orders, or produce different conclusions across runs on the same input. For anything requiring reproducible results — data pipelines, financial reporting, batch processing — non-determinism is a liability.

**Auditability.** In regulated industries, every step of a workflow may need to be explainable and traceable. A traditional task sequence is inspectable: step A ran, produced this output, step B consumed it. An agent's reasoning process is less auditable by design.

**Cost predictability.** Agents loop internally and may call tools multiple times. Token costs scale with loop depth and tool call volume, and can vary significantly between runs. Traditional workflows have predictable, fixed costs per execution.

**Agents are appropriate when** the right sequence of steps genuinely cannot be predetermined — research tasks, exploratory queries, tasks that require adapting to what is discovered mid-execution. The module's best practices section frames this as a design decision, not a capability question.

---

### Q: What does Kestra's `logRequests: true` / `logResponses: true` configuration actually log?

**A:** When enabled on an `AIAgent` task, Kestra logs the full request sent to the LLM (including the system message, the current conversation history, and any tool call results) and the full response returned (including the model's reasoning, any tool calls it decided to make, and the final output text).

This is the primary debugging tool for agents. When an agent produces an unexpected answer, these logs let you trace exactly what the model received at each reasoning step and what it decided to do with it. Without them, you can only see the final output, which makes diagnosing failures significantly harder.

The trade-off is verbosity — these logs can be large for complex agents with multiple tool calls. Enable them during development and debugging; consider disabling them in stable production flows to reduce log volume.

---

### Q: In a multi-agent system, how does one agent call another?

**A:** In Kestra, an `AIAgent` task can be registered as a tool inside another agent using the `AIAgent` tool type. The outer agent treats the inner agent exactly like any other tool — it invokes it when needed, passes input, and receives output.

The practical pattern from the module's competitor research example: a Research Agent is equipped with web search tools and returns factual findings. A main Analyst Agent has the Research Agent registered as a tool. When the Analyst needs information, it calls the Research Agent as a tool call, the Research Agent performs its web searches and returns results, and the Analyst synthesises those results into the final output.

The key design principle is separation of concerns: each agent has one focused responsibility, making it easier to debug and easier to replace one agent without affecting the other.

---

*Submitted by: Samwel Njogu Mwaniki*
*GitHub: https://github.com/sanjomwa*
*Module: 03-orchestration*
*Course: https://github.com/DataTalksClub/llm-zoomcamp*