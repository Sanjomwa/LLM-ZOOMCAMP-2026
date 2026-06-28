# Module 2: Vector Search — Study Notes

**Course:** LLM Zoomcamp 2026
**Module:** 02 — Vector Search
**Purpose:** Long-term study reference. Return to this before building any production RAG retrieval layer.

---

## Module Overview

Module 1 built a working RAG system. It retrieved documents using keyword search, which matches words. That is fast, simple, and often good enough — but it has a fundamental limitation: it only finds what you literally typed, not what you meant.

Module 2 fixes that. The core idea is deceptively simple: convert text into numbers that encode meaning, and then find the numbers closest to your question. Two phrases that mean the same thing produce similar numbers, even when they share no words. This is called semantic search.

Everything in Module 2 serves that single objective — turning text into meaning-aware numbers, searching those numbers efficiently, and then reasoning about when to use semantic search versus keyword search versus both.

### How Module 2 fits into the overall RAG pipeline

```
[User Question]
       |
       v
[Retrieval Layer]  <-- THIS MODULE
  - Embed the question
  - Search the vector index (or text index, or both)
  - Return the most relevant chunks
       |
       v
[Context Assembly]
       |
       v
[LLM Generation]
       |
       v
[Answer + Citations]
```

Module 1 was about the full pipeline with a basic retrieval step. Module 2 goes deep on that retrieval step — making it significantly more capable while also giving you the tools to measure whether it is actually better.

---

## Major Concepts

### Embeddings

An embedding is a list of numbers that represents the meaning of a piece of text.

When you embed the sentence "How do I store vectors in PostgreSQL?", you get back something like:

```
[-0.12, 0.81, -0.34, 0.07, ..., 0.22]
```

384 numbers. That vector is not random. It is the result of a model — trained on enormous amounts of text — learning to place sentences with similar meanings close together in a high-dimensional space, and sentences with different meanings far apart.

The individual numbers have no human-interpretable meaning on their own. You cannot look at position 47 and say "this is the 'database' dimension." The meaning is distributed across all 384 values collectively.

**Why does this work?**

During training, the embedding model learned that sentences like "store vectors in PostgreSQL" and "save embeddings in pgvector" tend to appear in similar contexts — in documentation, in tutorials, around the same technical concepts. It adjusted its weights so that both produce similar vectors. The model learned statistical patterns of co-occurrence across billions of sentences and encoded that knowledge into the vector representations.

**The map analogy**

Think of a map where every sentence is a pin. The map is not geographic — it is a meaning map. Sentences with similar meanings cluster together. "Cats", "kittens", and "felines" all sit close to each other. "Python programming" and "machine learning" cluster together, far from the animal cluster. The embedding model constructs this map, and placing a question on the map means finding which cluster of sentences it lands closest to.

---

### Embedding Dimensions: Why 384?

The model used in this module is `all-MiniLM-L6-v2`. It produces 384-dimensional vectors.

A dimension is like a coordinate. A city uses two coordinates (latitude, longitude). A room uses three (x, y, z). Language is far more complex than physical space, so the model needs far more room to describe it. 384 dimensions give the model enough freedom to encode the nuanced semantic relationships between words, phrases, topics, and styles.

Why 384 specifically and not 512 or 768? This is a design choice reflecting a trade-off:

- More dimensions → richer representations, but larger storage, slower computation, more memory
- Fewer dimensions → faster and cheaper, but potentially less expressive

`all-MiniLM-L6-v2` was specifically designed to be small and fast without sacrificing too much quality. 384 dimensions is the point where its designers found a good balance. Larger models like `all-mpnet-base-v2` use 768 dimensions.

The practical consequence: every chunk in a corpus of 295 chunks becomes a vector of shape `(384,)`. The entire index is a matrix of shape `(295, 384)`. That matrix is what you search against.

---

### Cosine Similarity

Once you have two vectors — one for the query, one for a document — you need to measure how similar they are. The standard measure is cosine similarity.

**The geometric intuition**

Think of each vector as an arrow pointing in some direction from the origin. Two arrows pointing in the same direction represent texts with similar meanings. Two arrows pointing in very different directions represent texts about different things.

Cosine similarity measures the angle between two arrows:

```
Same direction    → similarity ≈  1.0   (highly similar meaning)
Perpendicular     → similarity ≈  0.0   (unrelated)
Opposite          → similarity ≈ -1.0   (semantically opposite)
```

**Why the dot product works here**

The embedder returns normalized vectors — each vector has been scaled so its total length is exactly 1.0. For normalized vectors, the dot product equals the cosine similarity:

```
similarity = query_vector · doc_vector
```

This is a very cheap computation. For 384-dimensional vectors, it is just 384 multiplications and 383 additions. For a corpus of 295 chunks, that is 295 dot products — trivially fast.

**What the Q2 result of 0.36 means**

A similarity of 0.36 between "How does approximate nearest neighbor search work?" and the full SQLite vector search lesson is a moderate positive match. The lesson is genuinely related — both are about vector search — but the lesson covers many other topics (SQL, persistence, table schemas). Embedding the whole document averaged across all those topics, diluting the similarity to the specific query. This is exactly the motivation for chunking.

---

### Chunking

Chunking is often more important than the choice of embedding model.

**Why whole-document embeddings are weaker**

Embedding an entire document creates one vector that must represent everything in the document. A lesson covering "introduction, background, implementation, examples, and exercises" produces an embedding that is a rough average of all five topics. When you query about "examples specifically," this diluted embedding competes poorly against a chunk that contains only the examples section.

Think of mixing five paint colours. The result is an indistinct brown regardless of how vivid the original colours were. You cannot un-mix them.

**What chunking does**

Instead of embedding the whole document, you split it into smaller, overlapping windows and embed each one independently.

```
Full document
      |
      |---> Chunk 1: characters   0-2000  [embedding 1]
      |---> Chunk 2: characters 1000-3000  [embedding 2]
      |---> Chunk 3: characters 2000-4000  [embedding 3]
```

Each chunk gets its own focused embedding. Chunk 2 knows about its 2000-character window, not about the whole document. When you query, you compare against focused embeddings and retrieve focused passages.

**The Q3 demonstration**

Embedding the whole SQLite lesson against the ANN query gave similarity 0.36. The best chunk from the same lesson gave similarity 0.65. Nearly double — from better document preparation alone, with no change to the embedding model.

**Overlap (the step parameter)**

The `step=1000` parameter means the window slides forward 1000 characters each time, while the window itself is 2000 characters wide. This means consecutive chunks overlap by 1000 characters.

Overlap matters because passages do not respect arbitrary character boundaries. A key sentence explaining a concept might fall right at the boundary between two non-overlapping chunks, appearing in neither chunk in full. With overlap, it will appear fully in at least one chunk. The cost of overlap is a larger index; the benefit is that no passage is silently cut in half.

**The trade-off**

Smaller chunks → more focused embeddings, more precise retrieval, but more chunks to store and search, and answers may lose context because each chunk is too short.

Larger chunks → richer context per chunk, but more diluted embeddings, and more irrelevant content pulled into the LLM's context window (increasing cost and noise).

The right chunk size is domain-dependent and should be determined by evaluation, not intuition.

---

### Vector Search

**Brute-force search**

The most straightforward approach: embed the query, then compute the similarity between the query vector and every document vector in the index. Return the highest-scoring documents.

```python
scores = X.dot(query_vector)   # X is (295, 384), query_vector is (384,)
# scores is now (295,) — one similarity score per chunk
best_idx = scores.argmax()
```

For 295 chunks this is nearly instantaneous. For 295 million chunks, it is still mathematically identical — just slower.

**Why libraries exist**

At scale, brute-force search over millions or billions of vectors is impractically slow. Libraries like FAISS, Qdrant, Chroma, pgvector, and minsearch exist to perform approximate nearest neighbor (ANN) search — finding vectors that are probably the closest without checking every single one. They use data structures (tree-based, graph-based, cluster-based) to prune the search space.

For this module's 295 chunks, brute-force is fine. Understanding when you need ANN — when your corpus grows into millions of chunks — is the engineering judgment that matters.

**What VectorSearch adds over manual dot products**

`minsearch.VectorSearch` handles the matrix algebra, manages the payload (the chunk dictionaries), and returns ranked results with their associated metadata. It separates concerns: you provide vectors, it handles indexing and search. This matters because it makes it trivially easy to swap in a different embedding model — as long as the dimensions match, the search library does not care.

---

### Text Search vs Vector Search

| Property | Text Search | Vector Search |
|---|---|---|
| Matching method | Exact word overlap (TF-IDF / BM25) | Semantic similarity (dot product of embeddings) |
| Vocabulary | Must match terms in the index | Handles synonyms and paraphrases naturally |
| Exact terms | Excellent — finds error codes, names, IDs | Can miss rare or domain-specific exact terms |
| Speed | Very fast | Fast for small corpora; needs ANN at scale |
| Domain specialisation | Works well out of the box | Quality depends on embedding model |
| Infrastructure | Minimal | Requires embedding model and vector store |

**When to use text search**

When users know the exact terminology. Error codes, product names, legal citations, technical identifiers — if someone searches "PostgreSQL error 42883", you want the result that contains those exact characters.

**When to use vector search**

When users might phrase queries differently from how the content is written. "How do I save embeddings?" might need to find documentation that says "store vectors in pgvector." The vocabulary differs; the meaning does not.

**The Q5 demonstration**

Searching "How do I store vectors in PostgreSQL?" showed this difference concretely. Text search returned lessons about embeddings and RAG — documents containing the words "vectors" and "PostgreSQL." Vector search returned the pgvector lesson at the top, even though the query's exact phrasing didn't perfectly match the lesson's text — because the lesson's meaning matched the query's meaning.

**The key engineering principle**

Neither method is universally superior. The right choice depends on your data and your users' query patterns. This is why Module 4 (evaluation) exists: you measure which method actually works better for your specific corpus and query distribution, rather than guessing.

---

### Hybrid Search and Reciprocal Rank Fusion (RRF)

**The motivation**

Text search is good at exact terms. Vector search is good at meaning. Hybrid search asks: which documents do both methods think are relevant?

Documents that rank well in multiple retrieval systems are likely genuinely relevant, regardless of how they performed in any single system.

**Reciprocal Rank Fusion**

RRF ignores raw similarity scores — which live on different scales and are not directly comparable — and works only with ranks. For each document in each result list, its RRF contribution is:

```
score += 1 / (k + rank)
```

where `rank` starts at 0 (first position) and `k = 60` is a smoothing constant from the original RRF paper.

The effect: a document ranked first contributes `1 / (60 + 0) = 0.0167`. A document ranked fifth contributes `1 / (60 + 4) = 0.0156`. The difference is modest. A document that appears in both lists accumulates contributions from both, which is why cross-list consistency matters more than any single top ranking.

**Why k=60 specifically?**

It is the empirically validated default from the original 2009 RRF paper. It works well across a wide range of retrieval tasks and should not be tuned without a proper evaluation set. Lowering k makes top-ranked documents more dominant; raising k flattens the ranking curve and rewards documents that appear consistently across many lists without necessarily ranking first in any of them.

**The Q6 insight**

For "How do I give the model access to tools?", `01-agentic-rag/lessons/13-function-calling.md` was not first in either text search or vector search individually — but it ranked high in both lists. RRF surfaced it as the consensus best result. This is exactly what RRF is designed to do: find the document that multiple independent signals agree on, rather than the one that a single signal ranked highest.

---

### ONNX Runtime

**The development vs. production gap**

During development, `sentence-transformers` is convenient — a high-level library that handles model loading, tokenization, and embedding in one call. In production, its footprint is significant: it requires PyTorch (several gigabytes) and a compatible CUDA setup if you want GPU acceleration.

ONNX Runtime solves this. The same model weights can be exported to the ONNX format and run with the ONNX Runtime, which has no PyTorch dependency. The deployment footprint drops from ~4.8 GB to ~147 MB. The vectors produced are numerically identical — this is not an approximation.

**Why this matters for real systems**

- Docker images are dramatically smaller, which means faster CI/CD, lower storage costs, and simpler deployment pipelines.
- The runtime can run on any machine with a CPU — no GPU, no CUDA, no driver compatibility nightmares.
- Fewer dependencies mean fewer security surface areas and simpler dependency auditing.

**The conceptual lesson**

Development tooling and production tooling serve different goals. Development values ergonomics and iteration speed. Production values reliability, predictability, and minimalism. Knowing that these are different concerns — and that you can swap the serving layer without changing the model — is an engineering judgment that pays dividends across many systems, not just embeddings.

---

## Homework Walkthrough

### Q1 — Embedding a Query

**Objective:** Embed a query and inspect the resulting vector.

**Why this question exists:** Before building any retrieval system, you need to verify that your embedding pipeline is working correctly. The shape of the vector `(384,)` confirms the right model is loaded. The first value acts as a deterministic fingerprint — because tokenization, inference, pooling, and normalization are all fixed for a given model and input, the same input always produces the same first value.

**What to remember:** The individual values of an embedding have no human-interpretable meaning. You cannot inspect them and understand what they represent. Only the complete vector, in comparison with other vectors, carries meaning. The shape and first value checks are sanity checks on the pipeline, not insight into the embedding itself.

**Common mistake:** Trying to interpret individual embedding values. They are distributed representations — the meaning emerges from the pattern across all dimensions together.

---

### Q2 — Cosine Similarity with a Single Document

**Objective:** Embed a document and compute its similarity with the Q1 query.

**Why this question exists:** This exercise builds intuition for what cosine similarity measures before you use it at scale across hundreds of chunks. Comparing one query to one document lets you understand what a specific number like 0.36 actually means about the relationship between two texts.

**What to remember:** A moderate similarity (0.36) between a focused query about approximate nearest neighbor search and a long lesson about SQLite vector search reflects two genuinely related but non-identical ideas. The lesson discusses vector search concepts but buries them among implementation details about SQLite, SQL tables, and persistence — all of which dilute the embedding.

**Why the similarity was not higher:** The document covers many topics. Its embedding is a compromise across all of them.

---

### Q3 — Chunking and Manual Search

**Objective:** Chunk all documents, embed every chunk, and find the best chunk for the Q1 query by computing dot products manually.

**Why this question exists:** This is the most important conceptual demonstration in the module. The improvement from 0.36 (whole document) to 0.65 (best chunk) is a direct, empirical proof that document preparation quality matters as much as — often more than — model selection.

**What to remember:** The best chunk still came from the same document as Q2. The lesson was always the right answer. The problem in Q2 was that the whole document's embedding was too diluted to rank the lesson high enough. Chunking solved the problem by giving the relevant passage its own focused embedding.

**What `scores.argmax()` does:** After computing one similarity score per chunk, `argmax()` returns the position (index) of the highest score. This is the core retrieval step — compute similarities, find the best, return it. Vector search libraries do exactly this at scale.

---

### Q4 — Vector Search with minsearch

**Objective:** Use VectorSearch from minsearch to run a semantic query, verifying the library returns correct results.

**Why this question exists:** Manual dot products teach the concept. Libraries are what you use in practice. Understanding the interface separation — the embedding model produces vectors, the search library indexes and ranks them — is the engineering principle that makes these systems maintainable.

**What to remember:** `VectorSearch.search()` takes a query vector, not raw text. This is intentional. The library is agnostic about how the vector was produced. You could swap in any embedding model — OpenAI's ada, a multilingual model, a domain-fine-tuned model — without touching the search code. The interface boundary between "embedding" and "search" is a clean, principled separation of concerns.

**The result:** Searching "What metric do we use to evaluate a search engine?" retrieved `04-evaluation/lessons/05-search-metrics.md` — the lesson literally about search metrics. This is vector search working correctly: the semantic content of the query matched the semantic content of the lesson.

---

### Q5 — Text Search vs Vector Search

**Objective:** Run the same query against both keyword search and vector search, and identify what vector search finds that text search misses.

**Why this question exists:** This is the clearest possible demonstration of the vocabulary mismatch problem. The query asks about "storing vectors in PostgreSQL." The pgvector lesson discusses storing embeddings using pgvector — related vocabulary, but not identical vocabulary. Text search could not bridge that gap; vector search could.

**What to remember:** Text search is not wrong for missing the pgvector lesson. It worked correctly given its design — it found documents containing the query's words. The pgvector lesson uses different words to discuss the same concept. Vector search handles this by operating on meaning rather than literal text.

**The deeper lesson:** This is why you cannot decide which retrieval method to use based on one example. Text search may be the right answer for your domain if users consistently use exact terminology. The choice is an empirical question, answered by evaluation.

---

### Q6 — Hybrid Search with RRF

**Objective:** Combine text and vector search results using Reciprocal Rank Fusion and observe that the top result was not first in either individual method.

**Why this question exists:** The result — `function-calling.md` winning despite not ranking first in either individual search — is a perfect illustration of what hybrid search achieves and why it works. It demonstrates that retrieval quality is not always about which method scores highest, but about which documents multiple methods consistently consider relevant.

**What to remember:** RRF works on ranks, not scores. This matters because raw similarity scores from text search (TF-IDF weights) and vector search (cosine similarities) are not on comparable scales. You cannot simply add them. RRF sidesteps this problem entirely by discarding the raw scores and working only with position information.

**The k=60 parameter:** Do not tune this without a proper evaluation set. The default from the original paper works well across many retrieval tasks and tuning it based on a single example query is overfitting.

---

## Connections to Real Projects

### Internal Documentation Search

A company with thousands of internal documents — engineering wikis, runbooks, architecture decisions — benefits immediately from vector search. Engineers rarely remember the exact terminology used in documentation. Semantic search finds the relevant runbook even when the query uses different phrasing.

### Legal Document Retrieval

Legal documents require both semantic search (finding conceptually relevant precedents regardless of exact phrasing) and keyword search (finding exact citations, case numbers, statutory references). Hybrid search is the natural architecture for this domain.

### Research Assistants

Scientific literature uses highly specialised vocabulary that shifts between disciplines. An embedding model trained on general text may not handle domain vocabulary well, but hybrid search partially compensates: vector search handles paraphrased concepts while keyword search handles technical terms. This is a strong argument for the value of domain-specific embedding models — and for always evaluating retrieval quality before choosing a method.

### Intelligence Analysis Platforms (KCLIO)

An analyst asking "show me reports discussing restrictions on digital rights during elections" does not want to enumerate every possible synonym: censorship, internet shutdown, communications blackout, network disruption, digital repression. Vector search can retrieve reports that use any of these phrasings. Adding keyword search via RRF preserves precision for cases where the analyst knows exact terminology — a specific law number, organisation name, or event date. This is exactly the retrieval architecture that would make KCLIO's document layer significantly more capable than keyword search alone.

The ONNX point is also directly relevant to KCLIO: a monitoring platform deployed in resource-constrained environments (smaller cloud instances, edge deployments) benefits considerably from a 147 MB embedding runtime instead of a 4.8 GB PyTorch installation.

---

## Lessons Learned

**The conceptual shift is the most important thing.**
Module 1 matched text to text. Module 2 matches meaning to meaning. That shift — from "find documents with these words" to "find documents with this meaning" — is what makes RAG systems genuinely useful rather than just fancy keyword search.

**Chunking often matters more than model choice.**
The jump from 0.36 to 0.65 similarity in Q3 came entirely from splitting the document into chunks — no change to the embedding model, no change to the query. In practice, investing time in better chunking strategies (boundary-aware splitting, semantic chunking) often returns more retrieval quality improvement than switching to a larger embedding model.

**No single retrieval method is universally best.**
This module deliberately gives you three methods and then tells you that Module 4 will teach you how to evaluate which one is actually better for your data. That ordering is intentional. The lesson is: collect methods, then measure.

**Interface boundaries matter.**
The design where `VectorSearch.search()` accepts a vector (not raw text) is a small decision with large consequences. It means the embedding model is completely swappable. Engineering systems with clean, narrow interfaces between components is what makes them maintainable over time.

**Development and production tooling are different concerns.**
ONNX Runtime producing identical vectors to sentence-transformers at 30x smaller deployment size is not a trick — it is a principled engineering decision about what belongs in a deployed service versus a development notebook. Recognising these as separate concerns, and designing for the transition between them, is a mark of production engineering thinking.

---

## Key Takeaways

- Embeddings convert text into lists of numbers that encode semantic meaning, not literal words.
- Similar meanings produce vectors that point in similar directions; dissimilar meanings produce vectors pointing in different directions.
- Cosine similarity measures the angle between two vectors. For normalized vectors (which `all-MiniLM-L6-v2` produces), the dot product equals cosine similarity directly.
- The 384 dimensions in `all-MiniLM-L6-v2` are a design choice reflecting a quality-vs-cost trade-off; the dimensions have no individual human-interpretable meaning.
- Chunking documents before embedding them dramatically improves retrieval because each chunk gets a focused embedding rather than a diluted average of the whole document.
- Overlapping chunks ensure no passage is silently split across a chunk boundary.
- Brute-force vector search is `query_vector.dot(all_chunk_vectors)` — mathematically trivial, computationally manageable at small scale, requiring ANN libraries at large scale.
- Text search matches words. Vector search matches meaning. Each has strengths the other lacks.
- Hybrid search (RRF) combines ranked result lists rather than raw scores, finding documents that consistently rank well across multiple retrieval methods.
- RRF often surfaces documents that ranked second or third in each individual method but ranked highly and consistently across both — which is usually a better signal of true relevance.
- The k=60 constant in RRF is the empirical default from the original paper. Do not tune it without a proper evaluation set.
- ONNX Runtime produces identical embeddings to sentence-transformers at roughly 30x smaller deployment size, making it the right choice for production systems.
- Choosing between text search, vector search, and hybrid search is an empirical question answered by retrieval evaluation — not by intuition or convention.
- The question to ask about any retrieval design decision is: "does this measurably improve retrieval quality on my specific corpus and query distribution?" Everything else is speculation.
- Clean interface separation between embedding model and search library makes retrieval systems maintainable and extensible — swap either component without touching the other.