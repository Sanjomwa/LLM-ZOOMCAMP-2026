# Homework 4: Evaluation — Solutions & Summary.

## Course: LLM Zoomcamp 2026 — Module 4

**Knowledge base:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/04-evaluation (72 lesson pages across the whole course, pinned at commit 8c1834d).

**Full notebook: LLM-ZOOMCAMP-2026/homework/module_04/evaluation.ipynb**

Continues from: Homework 2 — same chunks, same project, same search functions.

**Course material: https://github.com/DataTalksClub/llm-zoomcamp/tree/main/04-evaluation**

### Setup
This homework continues directly from Homework 2 — same project, same kernel, no new environment needed beyond a couple of extra libraries for structured-output ground truth generation:

bash
 ```
uv add openai pydantic python-dotenv pandas
```

Download the two helper files the module's ground-truth generation depends on:
bash
```
PREFIX=https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main
wget ${PREFIX}/01-agentic-rag/code/rag_helper.py
wget ${PREFIX}/04-evaluation/code/evaluation_utils.py
```

The embedding model (embedder.py + the ONNX all-MiniLM-L6-v2 files) is fetched by the notebook itself, idempotently (wget -nc), so the notebook runs standalone even without Homework 2's project directory present.

## Q1. Generating questions
Answer: 1400 (measured average: 1354.0)

### Why
Token usage is reported directly on the API response object (usage.input_tokens) — not something to estimate from character counts. Generating ground truth for all 72 lesson pages costs real money, so checking the per-page cost on a small sample (3 pages) before committing to the full batch is the same cost-awareness habit the module's own batch-ground-truth lesson demonstrates.

### How
python
```
first_three = [
    "01-agentic-rag/lessons/01-intro.md",
    "01-agentic-rag/lessons/02-environment.md",
    "01-agentic-rag/lessons/03-rag.md",
]

docs_by_filename = {doc["filename"]: doc for doc in documents}

usages = []
for filename in first_three:
    doc = docs_by_filename[filename]
    user_prompt = json.dumps({"filename": doc["filename"], "content": doc["content"]})
    _, usage = llm_structured(openai_client, data_gen_instructions, user_prompt, Questions)
    usages.append(usage)
    print(filename, usage.input_tokens)

avg_input_tokens = sum(u.input_tokens for u in usages) / len(usages)
print("Q1 average input tokens:", avg_input_tokens)
01-agentic-rag/lessons/01-intro.md 1021
01-agentic-rag/lessons/02-environment.md 1287
01-agentic-rag/lessons/03-rag.md 1754
Q1 average input tokens: 1354.0
```

### What to remember
The four answer options are roughly 10x apart, so a correct order of magnitude is what's being tested, not a precise value — the assignment says explicitly these numbers vary run to run even with the same model. Prompt length here is dominated by the lesson page's own content, not the instructions — the longest of the three pages (03-rag.md) produced proportionally more input tokens.

## Q2. First result with text search
Answer: 01-agentic-rag/lessons/03-rag.md

### Why
Keyword search over the chunked lesson pages — same Index class and same chunking (size=2000, step=1000 → 295 chunks) as Homework 2, just built over lesson-page chunks instead of FAQ records, and matched on filename instead of a document id.

### How
python
```
q = ground_truth[0]["question"]
# "What exactly is a retrieval-augmented generation system, and why does it
#  help with answers that the model wouldn't know on its own?"

text_results = text_search(q)
text_results[0]["filename"]
'01-agentic-rag/lessons/03-rag.md'
```

### What to remember
This question was generated from 01-intro.md, not 03-rag.md — text search's top hit is plausible (both pages are foundational RAG concept pages sharing a lot of vocabulary) but wrong. That gap between "plausible" and "correct" is exactly why Q4 evaluates across the full 360-question set instead of trusting this one result.

## Q3. First result with vector search
Answer: 01-agentic-rag/lessons/01-intro.md

### Why
Same query, same 295 chunks, ranked instead by cosine similarity between the ONNX MiniLM query embedding and each chunk's embedding.

### How
python
```
vector_results = vector_search(q)
vector_results[0]["filename"]
'01-agentic-rag/lessons/01-intro.md'
```
### What to remember
Vector search found the actual source page; text search didn't. Neither method is "wrong" — each did exactly what it's designed to do. The value of running both against the same query is seeing them disagree, which is precisely why evaluating across the whole ground truth set (Q4/Q5), not trusting one query, is the only way to know which method is actually better overall.

## Q4. Evaluating text search
Answer: 0.76 (measured: hit_rate = 0.7583, mrr = 0.5943)

### Why
Hit Rate answers a coarse question: across all 360 ground-truth questions, did the correct page appear anywhere in the top 5 results? This is the retrieval-only evaluation the module insists on running before touching generation — it isolates whether the search layer can find the right page at all.

### How
python
```
def compute_relevance(q, search_function):
    filename = q["filename"]
    results = search_function(q["question"])
    return [int(d["filename"] == filename) for d in results]

def compute_relevance_total(ground_truth, search_function):
    return [compute_relevance(q, search_function) for q in tqdm(ground_truth)]

def hit_rate(relevance):
    return sum(1 for line in relevance if 1 in line) / len(relevance)

def mrr(relevance):
    total = 0.0
    for line in relevance:
        for rank, val in enumerate(line):
            if val == 1:
                total += 1 / (rank + 1)
                break
    return total / len(relevance)

def evaluate(ground_truth, search_function):
    relevance_total = compute_relevance_total(ground_truth, search_function)
    return {"hit_rate": hit_rate(relevance_total), "mrr": mrr(relevance_total)}

result_text = evaluate(ground_truth, text_search)
result_text
{'hit_rate': 0.7583333333333333, 'mrr': 0.5942592592592594}
```

### What to remember
The only change from the module's own compute_relevance is what counts as a hit: filename match instead of id match. hit_rate, mrr, and evaluate themselves are untouched — proof that writing evaluation code generically against a search_function parameter, rather than a specific index, pays off exactly as intended: the same three functions score all three retrieval methods in this homework without modification.

## Q5. Evaluating vector search
Answer: 0.55 (measured: hit_rate = 0.7250, mrr = 0.5486)

### Why
Same harness, same ground truth, vector_search instead of text_search — the first time this evaluation code runs against the ONNX vector index rather than the keyword index.

### How
python
```
result_vector = evaluate(ground_truth, vector_search)
result_vector
{'hit_rate': 0.725, 'mrr': 0.5486111111111112}
```

### What to remember
Worth stating plainly, not glossed over: keyword search beat vector search on both metrics in this run (text: 0.76 / 0.59 vs. vector: 0.73 / 0.55). That's not the intuitive outcome, and it isn't a bug — the ground-truth questions here were generated by an LLM reading the lesson pages directly, which tends to reuse some of the source page's own vocabulary even when explicitly told not to. That keeps keyword overlap unusually informative for this specific dataset. This is the module's core lesson (measure, don't assume) landing on real data instead of a lesson anecdote.

## Q6. Tuning hybrid search
Answer: k = 1 (not a tie — clearly the best, no tie-break needed)

### Why
RRF's k controls how sharply rank position is weighted. A small k makes the score gap between rank 1 and rank 2 large, so each individual method's top pick matters more. A large k flattens that gap and rewards chunks that show up anywhere near the top of both lists, even without ranking first in either. The paper's default of 60 is a default, not a property of this corpus — which is exactly why it's swept instead of assumed.

### How
python
```
results_by_k = {}
for k in [1, 50, 100, 200]:
    result = evaluate(ground_truth, lambda query, k=k: hybrid_search(query, k=k))
    results_by_k[k] = result
    print(f"k={k}: {result}")

best_k = max(results_by_k, key=lambda k: (results_by_k[k]["mrr"], -k))
best_k
k=1:   {'hit_rate': 0.8388888888888889, 'mrr': 0.6481944444444449}
k=50:  {'hit_rate': 0.8361111111111111, 'mrr': 0.637916666666667}
k=100: {'hit_rate': 0.8361111111111111, 'mrr': 0.637916666666667}
k=200: {'hit_rate': 0.8361111111111111, 'mrr': 0.637916666666667}
```

### What to remember
k=50/100/200 are identical to four decimal places on this dataset — past a certain point, raising k stops changing which chunk lands on top, so the metric flattens out completely. Only the sharpest setting moved the number, and it moved it in the direction of trusting each method's own top pick more heavily.

### Summary: Which Search Method Actually Won?
text_search	Hit Rate 0.7583	MRR 0.5943

vector_search	Hit Rate 0.7250	MRR 0.5486

hybrid_search (k=1)	Hit Rate 0.8389	MRR 0.6482

Hybrid wins outright over either method alone, on both metrics — the RRF consensus signal (a chunk that shows up credibly in both rankings) beats trusting either ranking on its own. The more interesting result is that plain keyword search beat vector search here, on both metrics, which isn't what most people would predict going in. That's the entire point of this homework: replace the guess with a number.

Full notebook: evaluation.ipynb — LLM-ZOOMCAMP-2026/homework/module_04/evaluation.ipynb 

Study notes: evaluation_notes.md
Course material: 04-evaluation 
Homework instructions: DataTalksClub/llm-zoomcamp, cohorts/2026/04-evaluation/homework.md

