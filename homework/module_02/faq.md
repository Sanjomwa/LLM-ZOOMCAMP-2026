# Module 2 (Vector Search) — FAQ Additions

These are questions that came up while working through the Module 2 homework — specifically around embeddings, cosine similarity, chunking, and hybrid search. None of these touch graded answers, just the concepts and reasoning behind each step. Posting here in case others hit the same questions.

---

### Q: Why does the homework print the embedding shape and first value?

**A:** The goal is not to inspect the embedding itself but to verify that the embedding pipeline is functioning correctly.

Printing `(384,)` confirms that the expected model (`all-MiniLM-L6-v2`) has been loaded — it always produces 384-dimensional vectors, so the shape is a reliable signal that the right model is running.

Printing the first value acts as a deterministic fingerprint. Because the model, tokenizer, and preprocessing are fixed, the same input always produces the same normalized vector. If the first value changes unexpectedly, it usually means a different model, tokenizer, or preprocessing pipeline is being used.

The individual values of an embedding have no human-interpretable meaning. Only the complete vector, compared against other vectors, represents semantic content.

---

### Q: Why are we comparing the query with only one document in Q2?

**A:** Q2 is not retrieval — it is model validation. By comparing one query against one known document, you build intuition for what cosine similarity actually means before scaling up to 295 chunks.

Retrieval systems simply repeat this same comparison against every document in the corpus and rank by score. Q2 shows you the unit operation; Q3 shows you that operation applied at scale.

---

### Q: Why wasn't the cosine similarity in Q2 close to 1?

**A:** Because the query and the document are related but not the same thing.

The query asks specifically about approximate nearest neighbor search. The SQLite vector search lesson discusses related ideas but spends most of its length on SQLite tables, SQL syntax, persistence, and implementation details. Embedding the whole document compresses all of those topics into one vector — a weighted average of everything. The resulting vector is pulled away from the specific ANN concept the query is asking about.

A cosine similarity of ~0.36 indicates meaningful semantic overlap without the texts expressing the same focused idea. It is not a bad result — it correctly reflects what the document actually contains.

---

### Q: Why does chunking improve retrieval?

**A:** Embedding an entire document forces the model to compress many different topics into one vector. The result is a blurred average that represents everything in the document, making it a weak match for any specific question.

Chunking breaks documents into smaller, focused pieces. Each chunk gets its own embedding representing only its own content. During retrieval, the query is then compared against many specialized vectors instead of one general-purpose one, making it far more likely to find the passage that actually answers the question.

The Q3 result makes this concrete: the whole-document similarity was ~0.36; the best chunk from the same document was ~0.65. That improvement came entirely from better document preparation — no change to the model or the query.

---

### Q: Why chunk before embedding rather than after?

**A:** Embedding happens per unit of text. If you embed first, you already have one vector per whole document, and you cannot split that vector meaningfully after the fact.

Chunking must happen on the raw text, before embedding, so each chunk becomes its own independent vector. The pipeline is always:

```
Raw document
  → Chunk 1 text  →  Embedding 1
  → Chunk 2 text  →  Embedding 2
  → Chunk 3 text  →  Embedding 3
```

Each chunk gets its own place in the vector space.

---

### Q: Why do we use `argmax()` after computing similarities in Q3?

**A:** `X.dot(query_vector)` returns one similarity score per chunk — a vector of 295 numbers. `argmax()` returns the index of the highest score, identifying which chunk is most semantically similar to the query.

This is the entire core of brute-force vector search:

1. Compute similarities between the query and every chunk.
2. Find the highest score.
3. Return the corresponding chunk.

Vector search libraries (minsearch, FAISS, Qdrant, etc.) automate this and add efficiency at scale, but the underlying operation is identical.

---

### Q: Why does `VectorSearch.search()` take a vector instead of raw text?

**A:** `VectorSearch` is only responsible for indexing and ranking vectors. It does not know how to convert text into embeddings, and it should not — that is the embedding model's job.

This separation of concerns keeps the system flexible. You can use any embedding model (ONNX, sentence-transformers, OpenAI, a domain-specific fine-tuned model) as long as it produces vectors of the correct dimension. Switching embedding models does not require touching the search code, and vice versa.

---

### Q: Why did vector search find the pgvector lesson but text search missed it?

**A:** The query asked "How do I store vectors in PostgreSQL?" Keyword search looked for those exact words and found documents that contain "vectors" and "PostgreSQL" together. The pgvector lesson uses different vocabulary — "pgvector", "pg_vector extension", "storing embeddings" — so keyword search did not surface it.

Vector search converted both the query and the pgvector lesson into embeddings capturing their meaning, not their exact words. Because the lesson discusses the same concept as the query (storing embedding vectors inside PostgreSQL), their vectors pointed in similar directions — and the lesson ranked first.

This is the vocabulary mismatch problem, and it is the primary reason vector search exists:

- Text search matches words.
- Vector search matches meaning.

---

### Q: Why does the same filename appear multiple times in vector search results?

**A:** Vector search runs over chunks, not whole documents. A long document is split into overlapping chunks and each gets its own embedding. During retrieval, multiple chunks from the same file can all be highly relevant and appear separately in the results, each with a different `start` value indicating which part of the document they represent.

This is expected behaviour, not an error. The RAG system later decides how many chunks from the same document to include in the prompt.

---

### Q: Why does Reciprocal Rank Fusion (RRF) often outperform either search method individually?

**A:** RRF asks a different question than either individual method. Instead of "which document scored highest?", it asks: "which documents consistently appear near the top across multiple methods?"

A document that ranks well in both text search and vector search receives contributions from both ranked lists. A document that was only strong in one list collects just one contribution. The result is that documents with broad, consistent support across methods tend to outrank documents that were exceptional in just one.

The Q6 result illustrates this: the function-calling lesson ranked second in text search and fifth in vector search — first in neither. But it was the only chunk that ranked highly in both, so RRF placed it first overall.

RRF also sidesteps the problem of incomparable scores. Text search and vector search produce raw scores on completely different scales. Rather than trying to normalise or weight them, RRF discards the raw scores entirely and works only with rank positions, which are always comparable.

---

*Submitted by: Samwel Njogu Mwaniki*
*GitHub: https://github.com/sanjomwa*
*Module: 02-vector-search*
*Course: https://github.com/DataTalksClub/llm-zoomcamp*