Module 4: Evaluation — Study Notes
Course: LLM Zoomcamp 2026 Module: 04 — Evaluation Purpose: Long-term study reference. Return to this before evaluating any retrieval or generation system in production.

Module Overview
Modules 1–3 built things: an agentic RAG pipeline, a vector/hybrid search layer, an orchestrated pipeline. Each of those modules ended with a working system and a reasonable-sounding set of design choices — a chunk size, an embedding model, a boost configuration, an RRF k. Each choice was made provisionally, the way most people make it: try something, read a few outputs, decide it looks fine.

Module 4 exists because "looks fine" is a judgment about the handful of examples you happened to check, and it says nothing about the other 355 questions you didn't. The core idea is deceptively simple: convert a judgment call ("is this the right document," "did we find it") into a number, computed the same way, twice, so two configurations can be compared on evidence instead of impression.

Homework 2 (vector search) ended on an explicitly open question: keyword, vector, or hybrid search — which one is actually best for this corpus? Module 4 supplies the missing tool to finally answer it: a ground-truth dataset and a metric that doesn't change definition between runs.

How Module 4 fits into the overall RAG pipeline
[User Question]
       |
       v
[Retrieval Layer]    <-- built in Module 2 (text/vector/hybrid search)
       |
       v
[Evaluation Layer]   <-- THIS MODULE
  - Ground truth: {question, correct filename}, generated A -> Q*
  - Hit Rate: did we find the right page at all?
  - MRR: how close to the top did we rank it?
  - evaluate(ground_truth, search_function): reusable across all 3 methods
       |
       v
[Context Assembly] -> [LLM Generation] -> [Answer]
Module 2 built three retrieval methods with no way to compare them. Module 4 is where you go back and actually check — which reframes Module 2's choices retroactively: they weren't final designs, they were hypotheses waiting for an evaluation method that didn't exist yet.

Major Concepts
Ground Truth by Structured Output (the A → Q* pattern)
You can't measure "did search find the right document" without first knowing, for a given question, what the right document is. Ground truth is manufactured by running the answer-to-question process backwards: take a document you already have (an "A"), ask an LLM to generate realistic questions it would answer (a "Q*"), and label each generated question with the document it came from.

Structured output (a Pydantic Questions model passed as text_format to client.responses.parse) removes an entire class of parsing bugs — no regex-scraping a numbered list out of free text, no silent truncation. This homework adapts the module's own FAQ-record prompt to lesson pages: instead of "emulate a student reading a FAQ," it's "emulate a student reading a lesson page," explicitly instructed to use different wording than the page itself. That instruction matters — an LLM generating a question from a document naturally reuses some of the document's own vocabulary even when told not to, which inflates retrieval metrics relative to how real users actually phrase questions (see "Why keyword search won," below).

Hit Rate and MRR
Both metrics start from the same raw material: a relevance list, one row per ground-truth question, each row a list of 0s and 1s marking which of the top-k results actually matched.

Hit Rate answers "did we find it anywhere in the top k": the fraction of questions where at least one 1 appears in the row. It's forgiving — rank 1 and rank 5 count identically.

MRR (Mean Reciprocal Rank) answers "how close to the top": for each question, 1 / (rank + 1) if found, contributing less the further down the correct result landed; 0 if never found. MRR is always ≤ Hit Rate on the same data, because it penalizes correct-but-buried results that Hit Rate credits fully.

Both metrics assume a single relevant document per question — a simplification worth noticing (real questions can have multiple valid sources) rather than forgetting.

The Generic search_function Evaluation Harness
The single most important design decision in this module's code: evaluate never mentions text_index, vector_index, or any specific search method by name. It takes a search_function parameter and calls search_function(question). This is why the exact same three functions — compute_relevance, hit_rate, mrr — score text_search, vector_search, and hybrid_search in this homework without a single line changing between Q4, Q5, and Q6. The only adaptation this homework needed at all was swapping the relevance check from d["id"] == q["document"] (module's FAQ ground truth) to d["filename"] == q["filename"] (this homework's page-level ground truth) — a one-line change, because the harness was written generically on purpose.

Reciprocal Rank Fusion, Revisited: k as a Tunable Parameter
Homework 2 introduced RRF with a fixed k=60 (the paper's default) and showed hybrid search surfacing a consensus result neither individual method ranked first. This homework treats k itself as something to measure rather than assume: sweeping k over {1, 50, 100, 200} and comparing MRR is a small, direct instance of the same grid-search-by-evaluation pattern the course uses for field boosts, just applied to a fusion parameter instead. A smaller k sharpens the score gap between rank 1 and rank 2 (top positions dominate more); a larger k flattens it (consistent mid-ranking across both lists matters relatively more). Neither is universally correct — it's a property of the corpus and query distribution, exactly like a boost value.

Token Cost as a First-Class Engineering Concern
Every ground-truth-generation call in this module returns token usage alongside the actual output, and the homework asks you to look at it before running the expensive version (all 72 pages) by first checking 3. This isn't incidental bookkeeping — an evaluation practice that's too expensive to rerun after every change stops being a practice and becomes a one-time report. Checking cost on a small sample before scaling up is the same discipline whether the base unit is 3 lesson pages or 3,000 support tickets.

Homework Walkthrough
Q1 — Generating Questions
Objective: Generate 5 questions per lesson page for the first 3 pages, using structured output, and report the average input token cost.

Why this question exists: Before running ground-truth generation across all 72 pages (a real cost), check the cost on a small, cheap sample. This mirrors exactly how the module's own batch-generation lesson approaches scale: never run the expensive version blind.

What to remember: The reported number is real API usage, not an estimate — usage.input_tokens is authoritative, and estimating from character counts would be answering a different, less trustworthy question.

Common mistake: Treating the four multiple-choice options as needing an exact match. They're ~10x apart specifically because the question tests order-of-magnitude reasoning, not precision — a sign the assignment expects run-to-run variance.

Q2 & Q3 — First Result, Text Search vs. Vector Search
Objective: Run one ground-truth question through both retrieval methods and compare their top result.

Why this question exists: This is a single, concrete instance of the vocabulary-mismatch idea from Module 2, deliberately surfaced before the full-dataset evaluation in Q4/Q5. Seeing the two methods disagree on one real example makes the abstract "you have to measure, not assume" argument personal before the aggregate numbers make it statistical.

What to remember: Vector search won this specific comparison (found the actual source page; text search didn't) — but one query proves nothing about which method is better in general. That's not a caveat, it's the entire reason Q4 and Q5 exist.

Common mistake: Generalizing from this one result ("vector search is better") without checking the full-dataset numbers — which, in this homework, turn out to say the opposite for Hit Rate and MRR overall (see Q5).

Q4 & Q5 — Evaluating Text Search and Vector Search
Objective: Run the generic evaluate() harness against text_search (Q4, reporting Hit Rate) and vector_search (Q5, reporting MRR) across all 360 ground-truth questions.

Why this question exists: This is the module's central deliverable applied for real: replace "vector search felt better in Q3" with an actual number, computed identically for both methods, on a dataset neither method was tuned against.

What to remember: Text search's Hit Rate (0.76) and MRR (measured 0.594) both beat vector search's (0.73 / 0.55) here. This is a genuinely useful, slightly uncomfortable result — not a mistake to explain away. The likely cause: LLM-generated ground-truth questions tend to echo the source page's own vocabulary despite instructions not to, which narrows the gap keyword search is normally weak at.

Common mistake: Assuming a "more sophisticated" method (embeddings, a trained model) must outperform a "simpler" one (keyword matching) without checking. This is the same lesson the course's own question-field-boost story teaches, applied to method choice instead of a boost weight.

Q6 — Tuning Hybrid Search
Objective: Sweep RRF's k over {1, 50, 100, 200} and find which value maximizes MRR across the full ground truth.

Why this question exists: Turns "hybrid search is a good idea" into a tunable, measurable design decision, exactly like the module's own boost grid-search — just with one parameter instead of three, and against retrieval quality instead of a demo query.

What to remember: k=1 won clearly, and k=50/100/200 were indistinguishable to four decimal places. That plateau is itself informative: once k is large enough, further increases stop changing which chunks land at the top for this dataset. The RRF paper's k=60 default — right in that flat region — would have been an unremarkable middle-of-the-pack choice here, not the optimum.

Common mistake: Assuming ties need the documented tie-break rule (smallest k) to apply. Here k=1 wasn't tied with anything — the rule exists for a scenario that didn't occur in this specific run, and blindly invoking it without checking would produce the right answer by accident rather than by reading the actual numbers.

Connections to Real Projects
A/B Testing Infrastructure
The evaluate(ground_truth, search_function) pattern is precisely a controlled experiment: hold the dataset fixed, vary one thing (the function), attribute any score difference to that one variable. This is the same logic behind feature-flagged A/B tests in production systems — a fixed evaluation set is a test suite for a system whose outputs aren't deterministic, the same way a fixed traffic split is a test suite for a system whose users aren't identical.

Search Infrastructure Decisions at Scale
A team choosing between Elasticsearch's native hybrid support, a self-rolled RRF layer, or a managed vector database should be making that choice the way this homework does: build each option behind an identical interface, evaluate all of them against the same frozen ground truth, and let the numbers pick the winner — not vendor marketing, not "vector search sounds more modern."

Evaluation-Driven Corpus Growth (CLIO)
This is the most directly transferable lesson for the Civil Liberties Knowledge Assistant (a future CLIO component). Once that project's ingestion pipeline produces real chunks, the exact harness built here — {question, correct_chunk_id} ground truth, compute_relevance, hit_rate, mrr, evaluate — transfers with zero conceptual change, because it was already written generically against a search_function parameter. The one thing that must change deliberately: the ground-truth generation prompt. This homework's data_gen_instructions is tuned to "emulate a student asking about a lesson page" — CLIO's equivalent needs to emulate a researcher or journalist investigating internet freedom evidence, not a generic FAQ-reading student, because the query style is different enough to change which retrieval method actually wins (as this homework's Q4/Q5 result demonstrates: the "obviously better" method isn't always better, and that only shows up when you measure the specific domain, not a proxy for it).

Cost-Aware Evaluation Design
Q1's "check the cost on 3 pages before running all 72" habit scales directly to CLIO's future ground-truth generation across a much larger corpus (40–60 documents, hundreds of chunks). Knowing the per-document cost before committing to a full batch run is what makes evaluation something you can afford to rerun after every meaningful pipeline change, rather than a one-time report that goes stale the moment anything changes.

Lessons Learned
Intuition is a hypothesis generator, not a verification method. Q4/Q5's result — keyword search beating vector search on this specific dataset — is the concrete proof, not a slogan. Most engineers, including ones who just finished Module 2, would have guessed vector search wins. The only way to find out was to measure it.

A generic evaluation harness pays for itself immediately. evaluate() was written once, in the module's own lessons, against a search_function parameter. Reusing it for text_search, vector_search, and hybrid_search — three structurally different retrieval methods — required exactly one line changed (filename instead of id). That's not a coincidence; it's the payoff of the design decision made before this homework even existed.

A single example query is a demonstration, not evidence. Q2/Q3 show the two methods disagreeing on one question. That's useful for building intuition about why methods differ, but Q4/Q5's aggregate numbers are what actually answers "which is better" — and they don't agree with what Q2/Q3 alone would suggest.

Tunable parameters should be measured across their range, not assumed at their default. RRF's k=60 default is a reasonable starting point, not a law. Sweeping it here revealed both a clear winner (k=1) and a flat region (k≥50) that a single fixed value would never have surfaced.

Synthetic ground truth has a known bias, and it's visible here, not just theoretical. LLM-generated questions reusing source vocabulary is a documented caution in this module's own materials — and this homework's Q4/Q5 result is a live instance of that bias actually shaping which retrieval method looks best, not just a footnote to remember.

Key Takeaways
Evaluation converts a judgment call ("is this the right document") into a repeatable number by fixing a dataset and a scoring function, then applying both identically across configurations.
Ground truth is manufactured by running the answer-to-question process backwards (A → Q*), using structured output to avoid free-text parsing bugs.
Hit Rate measures "did we find it anywhere in the top k"; MRR measures "how close to the top." MRR ≤ Hit Rate always, on the same data.
Writing evaluation code generically against a search_function parameter — not a specific index — means the same harness scores every retrieval method without modification.
A single example query can demonstrate that methods disagree; it cannot tell you which method is better. Only aggregate evaluation across a full ground-truth set can.
The "obviously better" method isn't always better — this homework's own numbers show keyword search beating vector search, which is the point: measure the specific corpus and query distribution, don't assume based on sophistication.
Tunable parameters (RRF's k, field boosts, top-k) should be chosen by measured sweep, not left at a paper's default or a library's suggestion.
Token/cost tracking on a small sample before a full run is what makes evaluation cheap enough to actually rerun after every meaningful change — which is the difference between a practice and a one-time report.
Every idea in this homework — generic evaluation harness, cost-aware sampling, measuring instead of assuming — transfers directly to the Civil Liberties Knowledge Assistant's future retrieval layer, with only the ground-truth generation prompt needing domain-specific adaptation.

