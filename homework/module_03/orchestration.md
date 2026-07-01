# Homework 3: AI Orchestration with Kestra

**Course:** LLM Zoomcamp 2026 — Module 3

**Topic:** AI Orchestration with Kestra

**Course material:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/03-orchestration

---

## Homework Overview

Module 3 homework is observational and conceptual rather than purely code-based. The questions test understanding of context engineering, RAG grounding, token economics, and the appropriate use of agents vs. deterministic workflows. Several questions require running live Kestra flows and reading execution logs.

All flows were imported from `03-orchestration/flows/` and executed against a locally running Kestra instance with API keys configured via `.env`.

---

## Question 1: Context Engineering

**Question:** After running the same prompt in ChatGPT vs Kestra's AI Copilot ("Create a Kestra flow that loads NYC taxi data from BigQuery"), what is the primary reason the Copilot generates better Kestra flows?

**Answer:** AI Copilot has access to current Kestra plugin documentation.

**Explanation:** The Copilot produces valid, version-specific YAML because it retrieves current plugin schemas and property names before generating. ChatGPT generates plausible-sounding output from training data, which may reference outdated or invented plugin names. This is a direct demonstration of context engineering: the same model architecture produces verifiably better output when supplied with grounded, current documentation rather than relying on memorised patterns.

---

## Question 2: RAG vs No RAG

**Question:** After running `1_chat_without_rag.yaml` and `2_chat_with_rag.yaml`, the non-RAG response about Kestra 1.1 features is best described as:

**Answer:** Vague, generic, or fabricated — the model guesses from training data.

**Explanation:** Without retrieval, the model generates responses consistent with its training distribution rather than actual Kestra 1.1 release notes. The output is syntactically coherent but factually unreliable. The RAG version retrieves the actual documentation before generating, producing a response grounded in evidence. The experiment illustrates the fundamental RAG proposition: retrieval is a system design choice about what information the model receives, not a model capability.

---

## Question 3: Token Usage — Short Summary

**Question:** After running `4_simple_agent.yaml` with `summary_length = short`, what is the approximate output token count for `multilingual_agent`?

**Answer:** 60–100 tokens.

**Explanation:** A short summary prompt constrains the output scope tightly. The token count reflects the actual output specification — a brief summary produces a brief output. This baseline matters for Q4: it establishes what "short" costs before comparing against "long."

---

## Question 4: Token Usage — Long Summary

**Question:** Compared to the short summary result from Q3, how many times more output tokens does the long summary use?

**Answer:** 2–5x more.

**Explanation:** Increasing summary length from short to long expands the output scope substantially. The 2–5x multiplier follows predictably from the output specification change. This is a measurable consequence of prompt design, not an unpredictable model behaviour. Token counts are a design tool: if you know the multiplier, you can budget for it. If a long summary costs 5x more tokens than a short one, an agent that always produces long summaries costs 5x more per execution.

---

## Question 5: Modifying a Flow

**Question:** After changing the `english_brevity` task prompt from 1 sentence to 3 sentences and running with `summary_length = long`, how does the output token count compare to the original 1-sentence version?

**Answer:** 2–4x more.

**Explanation:** Tripling the required output length from 1 to 3 sentences increases token usage by roughly 2–4x rather than exactly 3x, because the model includes connecting language and context beyond the raw sentence count. The experiment demonstrates that small, specific changes to output constraints have predictable and measurable token cost implications. Prompt engineering for production systems requires treating token counts as a first-class design constraint, not an afterthought.

---

## Question 6: Best Practices

**Question:** For production workflows requiring deterministic, repeatable results with strict compliance requirements (financial reporting, regulated industries), which approach is most appropriate?

**Answer:** Use traditional task-based workflows for predictability and auditability.

**Explanation:** AI agents introduce non-determinism at the tool selection step — the model chooses which tools to call and in what order, and that decision may vary across runs with identical inputs. For workflows that must produce identical outputs on identical inputs, must be auditable to a regulator, or must satisfy compliance requirements, this non-determinism is a fundamental disqualifier. Traditional task-based workflows execute a fixed, inspectable graph and produce traceable outputs. The module's best practices section frames this not as a limitation of agents but as a design principle: match the tool to the requirement, and determinism is a requirement in regulated contexts.

---

