# Homework 2: Vector Search — Solutions & Notes

**Course:** LLM Zoomcamp 2026 — Module 2
**Knowledge base:** Course lesson pages (pulled from GitHub, commit `8c1834d`)
**Full notebook:** https://github.com/Sanjomwa/LLM-ZOOMCAMP-2026/blob/main/homework/module_02/vector_search.ipynb
**Course material:** https://github.com/DataTalksClub/llm-zoomcamp/tree/main/02-vector-search

---

## Setup

This homework uses the ONNX-based embedder rather than sentence-transformers. Both produce identical vectors, but the ONNX runtime is roughly 30x smaller — no PyTorch, no CUDA dependency, runs anywhere.

```bash
mkdir llm-zoomcamp-hw2 && cd llm-zoomcamp-hw2
uv init --no-workspace
uv add onnxruntime tokenizers numpy tqdm minsearch gitsource
uv add --dev huggingface-hub jupyter

PREFIX=https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main/02-vector-search/embed
wget $PREFIX/download.py
wget $PREFIX/embedder.py

uv run python download.py
```

The download fetches `Xenova/all-MiniLM-L6-v2` — the ONNX version of the same model used in the module lessons.

---

## Q1. Embedding a Query

**Answer: -0.02**

### Why

Embedding converts a text string into a fixed-length vector of numbers. The shape `(384,)` confirms that the correct model was loaded — `all-MiniLM-L6-v2` always produces 384-dimensional vectors. The first value is a deterministic fingerprint: same model, same input, same output, every time.

### How

```python
from embedder import Embedder

embed = Embedder()

query = "How does approximate nearest neighbor search work?"
query_vector = embed.encode(query)

print(f"Embedding shape: {query_vector.shape}")   # (384,)
print(f"First value: {query_vector[0]}")           # -0.02058203437252893
```

### What to remember

The individual numbers in an embedding have no standalone meaning. Only the complete vector, compared against other vectors, encodes semantic information. Printing the shape and first value is a pipeline sanity check, not insight into the embedding itself.

---

## Q2. Cosine Similarity

**Answer: 0.37**

### Why

The embedder returns normalized vectors, meaning each vector has been scaled to unit length. For normalized vectors, the dot product between two of them equals their cosine similarity — the cosine of the angle between them. An angle of zero means identical direction (similarity = 1.0); a right angle means unrelated (similarity = 0); opposite directions mean semantically opposite (similarity = -1.0).

A similarity of ~0.36 between the ANN query and the full SQLite vector search lesson reflects genuine but diluted relevance. The lesson discusses vector search concepts, but the full-page embedding is an average across all its topics — SQLite tables, SQL queries, persistence, implementation details — which pulls the vector away from the specific ANN question.

### How

```python
from gitsource import GithubRepositoryDataReader

reader = GithubRepositoryDataReader(
    repo_owner="DataTalksClub",
    repo_name="llm-zoomcamp",
    commit_id="8c1834d",
    allowed_extensions={"md"},
    filename_filter=lambda path: "/lessons/" in path,
)

documents = [file.parse() for file in reader.read()]

sqlite_doc = next(
    doc for doc in documents
    if doc["filename"] == "02-vector-search/lessons/07-sqlitesearch-vector.md"
)

doc_vector = embed.encode(sqlite_doc["content"])
similarity = query_vector.dot(doc_vector)

print(similarity)   # 0.36107027225589694
```

### What to remember

This exercise builds intuition before retrieval at scale. At search time, this same dot product is computed between the query and every document in the index. The highest dot product wins.

---

## Q3. Chunking and Search by Hand

**Answer: `02-vector-search/lessons/07-sqlitesearch-vector.md`**

### Why

The full-page embedding gave similarity ~0.36. After chunking, the best chunk from the same lesson gave ~0.65 — nearly double, with no change to the embedding model or query. Chunking creates smaller, focused semantic units. Instead of embedding "everything this lesson covers," each chunk embeds "what this specific passage is about." The relevant passage gets its own vector, undiluted by the rest of the document.

The winning chunk was chunk index 94, starting at character position 1000 within that lesson — the passage most directly about vector search and ANN, isolated from the SQLite boilerplate around it.

### How

```python
from gitsource import chunk_documents

chunks = chunk_documents(documents, size=2000, step=1000)
print(len(chunks))   # 295

texts = [chunk["content"] for chunk in chunks]
X = embed.encode_batch(texts)

print(X.shape)   # (295, 384)

scores = X.dot(query_vector)

print(scores.shape)   # (295,)
print(scores.max())   # 0.6489017718578813

best_idx = scores.argmax()

print(best_idx)                          # 94
print(chunks[best_idx]["filename"])      # 02-vector-search/lessons/07-sqlitesearch-vector.md
print(chunks[best_idx]["start"])         # 1000
```

### What to remember

`X.dot(query_vector)` is the entire brute-force vector search operation. It is a matrix multiplication: each of the 295 rows in X (one row per chunk embedding) is dot-producted against the query vector, producing 295 similarity scores simultaneously. `argmax()` returns the index of the highest score.

The step=1000 parameter means consecutive chunks overlap by 1000 characters. This prevents relevant passages from being silently split across chunk boundaries.

---

## Q4. Vector Search with minsearch

**Answer: `04-evaluation/lessons/05-search-metrics.md`**

### Why

`VectorSearch` from minsearch wraps the matrix multiplication into a proper search library interface: fit once, search many times, return ranked results with their payloads attached. The query "What metric do we use to evaluate a search engine?" semantically matched the lesson literally titled "Search Evaluation Metrics" — which covers Hit Rate and MRR, the exact metrics the question asks about. This is vector search working correctly.

### How

```python
from minsearch import VectorSearch

vector_index = VectorSearch()
vector_index.fit(X, chunks)

query = "What metric do we use to evaluate a search engine?"
query_vector = embed.encode(query)

results = vector_index.search(query_vector)

print(results[0]["filename"])   # 04-evaluation/lessons/05-search-metrics.md
```

### What to remember

`VectorSearch.search()` takes a query vector, not raw text. This is an intentional separation of concerns: the library handles indexing and ranking; the embedding model handles text-to-vector conversion. You can swap either component independently without touching the other. This is the design pattern that makes retrieval systems maintainable.

---

## Q5. Text Search vs Vector Search

**Answer: `02-vector-search/lessons/08-pgvector.md`**

### Why

Keyword search matched words: "vectors", "PostgreSQL", "store" found documents with those terms. The pgvector lesson uses different vocabulary — "pgvector", "embeddings", "pg_vector extension" — so keyword search missed it. Vector search matched meaning: both the query and the pgvector lesson discuss the same concept (storing embedding vectors inside PostgreSQL), so their vectors pointed in similar directions regardless of exact phrasing.

This is the vocabulary mismatch problem. Text search is not wrong — it found documents that contain the query's exact words. The pgvector lesson simply does not use those exact words. Vector search has no such limitation.

### How

```python
from minsearch import Index

text_index = Index(text_fields=["content"], keyword_fields=["filename"])
text_index.fit(chunks)

query = "How do I store vectors in PostgreSQL?"

text_results = text_index.search(query=query, num_results=5)

query_vector = embed.encode(query)
vector_results = vector_index.search(query_vector, num_results=5)

print("TEXT SEARCH")
for result in text_results:
    print(result["filename"])

# 02-vector-search/lessons/02-embeddings.md
# 03-orchestration/lessons/05-rag.md
# 02-vector-search/lessons/01-intro.md
# 03-orchestration/lessons/05-rag.md
# 02-vector-search/lessons/01-intro.md

print("VECTOR SEARCH")
for result in vector_results:
    print(result["filename"])

# 02-vector-search/lessons/08-pgvector.md  <-- appears here, not in text results
# 02-vector-search/lessons/08-pgvector.md
# 03-orchestration/lessons/05-rag.md
# 02-vector-search/lessons/08-pgvector.md
# 02-vector-search/lessons/08-pgvector.md
```

### What to remember

Neither method is wrong. Each performs correctly given its design. The pgvector lesson dominates the vector results (appearing four times) because multiple chunks within that lesson are all highly similar to the query — which also shows why chunk deduplication by document can matter in practice.

---

## Q6. Hybrid Search with RRF

**Answer: `01-agentic-rag/lessons/13-function-calling.md`**

### Why

For "How do I give the model access to tools?", text search and vector search produced different top results:

**Text search top 5:**
```
0  01-agentic-rag/lessons/14-agentic-loop.md       start: 0
1  01-agentic-rag/lessons/13-function-calling.md   start: 4000
2  01-agentic-rag/lessons/13-function-calling.md   start: 5000
3  01-agentic-rag/lessons/13-function-calling.md   start: 1000
4  04-evaluation/lessons/02-ground-truth.md        start: 3000
```

**Vector search top 5:**
```
0  01-agentic-rag/lessons/01-intro.md              start: 2000
1  04-evaluation/lessons/02-ground-truth.md        start: 1000
2  01-agentic-rag/lessons/16-other-frameworks.md   start: 0
3  01-agentic-rag/lessons/15-frameworks.md         start: 2000
4  01-agentic-rag/lessons/13-function-calling.md   start: 4000
```

The function-calling lesson ranked second in text search and fifth in vector search — neither was first. But it was the only chunk that appeared high in both lists. RRF surfaces this: the chunk accumulated RRF contributions from two lists, which no other chunk did at the same rank positions. The consensus signal outweighed any single method's top result.

**RRF results:**
```
1  01-agentic-rag/lessons/13-function-calling.md   start: 4000
2  01-agentic-rag/lessons/01-intro.md              start: 2000
3  01-agentic-rag/lessons/14-agentic-loop.md       start: 0
4  04-evaluation/lessons/02-ground-truth.md        start: 1000
5  01-agentic-rag/lessons/16-other-frameworks.md   start: 0
```

### How

```python
def rrf(result_lists, k=60, num_results=5):
    scores = {}
    docs = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            key = (doc["filename"], doc["start"])
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            docs[key] = doc

    ranked = sorted(scores, key=scores.get, reverse=True)
    return [docs[key] for key in ranked[:num_results]]


query = "How do I give the model access to tools?"

text_results = text_index.search(query, num_results=5)

query_vector = embed.encode(query)
vector_results = vector_index.search(query_vector, num_results=5)

results = rrf([vector_results, text_results])

for i, doc in enumerate(results):
    print(i + 1, doc["filename"], doc["start"])
```

### What to remember

RRF uses ranks, not raw scores. Raw scores from text search (TF-IDF weights) and vector search (cosine similarities between 0 and 1) are not on comparable scales and cannot be summed directly. RRF sidesteps this entirely — only position matters. A document ranked first contributes `1/(60+0) = 0.0167`; ranked fifth contributes `1/(60+4) = 0.0156`. Appearing in two lists accumulates both contributions. k=60 is the paper's default and works well across most retrieval tasks without tuning.

---

## Summary: Which Search Method to Use?

The answer is always empirical. Module 4 (Evaluation) will provide the tools to measure this properly. The intuition from this homework:

| Method | Strong when | Weak when |
|---|---|---|
| Text search | Users know exact terminology; error codes, names, IDs | Users paraphrase; synonyms; different vocabulary from documents |
| Vector search | Vocabulary mismatch between queries and documents | Rare exact terms that general models may not embed well |
| Hybrid (RRF) | You want the benefits of both; the domain has both exact and semantic query patterns | You need to tune for very specific query distributions |

---

*Full notebook: [vector_search.ipynb](vector_search.ipynb)*
*Course material: [vector_search](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/02-vector-search)*