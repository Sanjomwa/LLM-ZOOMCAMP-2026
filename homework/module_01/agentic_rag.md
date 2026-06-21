# Homework 1: Agentic RAG — Solutions & Notes

**Course:** LLM Zoomcamp 2026 — Module 1  
**Knowledge base:** Course lesson pages (pulled from GitHub, commit `8c1834d`)  
**Full notebook:** `<https://github.com/Sanjomwa/LLM-ZOOMCAMP-2026/blob/main/homework/01-agentic-rag.ipynb>`
**Course material:** `<https://github.com/DataTalksClub/llm-zoomcamp/tree/main/01-agentic-rag>`

---

## Q1. How many lesson pages are in the dataset?

**Answer: 72**

### Why

The `GithubRepositoryDataReader` pulled every markdown file whose path contains `/lessons/`. There are 7 modules, each with a `lessons/` folder of numbered `.md` files. The `filename_filter` excludes READMEs and other non‑lesson markdown.

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

files = reader.read()
documents = [file.parse() for file in files]

print(len(documents))  # 72
```

### Explanation

7 modules × varying numbers of lessons per module = 72 total.

The filter guarantees we only index the actual lesson content, not repo metadata.

## Q2. Indexing and searching

**Query: "How does the agentic loop keep calling the model until it stops?"**

**Answer: 01-agentic-rag/lessons/14-agentic-loop.md**

### Why

minsearch tokenizes the content field and ranks by relevance. The phrase "agentic loop" appears prominently in only one lesson — the one explicitly titled 14-agentic-loop.md. Keyword search correctly surfaces it as the top result.

### How

```
from minsearch import Index

index = Index(
    text_fields=["content"],
    keyword_fields=["filename"]
)
index.fit(documents)

results = index.search(
    query="How does the agentic loop keep calling the model until it stops?",
    num_results=5
)

print(results[0]["filename"])
# 01-agentic-rag/lessons/14-agentic-loop.md
```

### Explanation

Text_fields are tokenized and weighted by TF‑IDF (or similar).

Keyword_fields allow exact‑match filtering but don't affect ranking here.

No embeddings, no vector database — just structured keyword search.

## Q3. RAG — input tokens with full‑page retrieval

**Query: "How does the agentic loop keep calling the model until it stops?"**

**Model: gpt-5.4-mini**

**Answer: ~7,000 input tokens**

### Why

With 5 full lesson pages retrieved, each potentially thousands of characters long, the combined prompt is large. Most of the text is irrelevant to the specific question, but the RAG pipeline stuffs everything into context.

### How

```python
def search(query):
    return index.search(query=query, num_results=5)

def build_context(search_results):
    parts = []
    for doc in search_results:
        parts.append(f"FILE: {doc['filename']}\n\n{doc['content']}")
    return "\n".join(parts)

def rag(query):
    search_results = search(query)
    context = build_context(search_results)
    prompt = f"QUESTION:\n{query}\n\nCONTEXT:\n{context}"
    response = client.responses.create(model="gpt-5.4-mini", input=prompt)
    return response

result = rag("How does the agentic loop keep calling the model until it stops?")
print(result.usage.input_tokens)  # approximately 7,000
```

### Explanation

5 full pages × ~1,400 characters average → ~7,075‑character prompt → ~7,000 tokens (roughly 1 token ≈ 1 character for English text with this model).

The cost in tokens is almost entirely from irrelevant content dragged in by full‑page retrieval.

## Q4. Chunking — how many chunks?

**Parameters: size=2000, step=1000**

**Answer: 295**

### Why

Each lesson page is split into overlapping windows. With size=2000 and step=1000, consecutive chunks overlap by 1,000 characters. Long pages produce many chunks; short pages produce one or two. 72 pages become 295 chunks.

### How

```python
from gitsource import chunk_documents

chunked_docs = chunk_documents(documents, size=2000, step=1000)
print(len(chunked_docs))  # 295
```

### Explanation

Size=2000: each chunk is a window of 2,000 characters.

Step=1000: the window slides forward 1,000 characters each time.

Overlap of 1,000 characters means no passage is split silently across a boundary.

Number of chunks = sum over all pages of ceil((len(page) - size) / step) + 1.

## Q5. RAG with chunking — token reduction

**Query: Same as Q3.**
**Index: Chunk index (295 chunks).**
**Model: gpt-5.4-mini**

**Answer: ~3× fewer input tokens**

### Why

With chunked retrieval, each result is at most 2,000 characters instead of an entire page. The 5 retrieved chunks collectively contain far less text, while still including the relevant passages. Input tokens dropped from ~7,000 to ~2,300.

### How

```python
chunk_index = Index(text_fields=["content"], keyword_fields=["filename"])
chunk_index.fit(chunked_docs)

def chunk_search(query):
    return chunk_index.search(query=query, num_results=5)

def chunk_rag(query):
    search_results = chunk_search(query)
    context = build_context(search_results)  # same builder, different data
    prompt = f"QUESTION:\n{query}\n\nCONTEXT:\n{context}"
    response = client.responses.create(model="gpt-5.4-mini", input=prompt)
    return response

result = chunk_rag("How does the agentic loop keep calling the model until it stops?")
print(result.usage.input_tokens)  # approximately 2,300
```

### Explanation

5 chunks × ~500 characters average → ~2,500‑character prompt → ~2,300 tokens.

~3× reduction for the same question, same model, same retrieval count — just by indexing smaller, more targeted pieces.

## Q6. Agentic RAG — how many search calls?

**Query: "How does the agentic loop work, and how is it different from plain RAG?"**
**Model: gpt-5.4-mini**
**Tool: search_lessons (wraps the chunk index from Q4–Q5)**
**Instructions: "You're a course teaching assistant. Answer the student's question using the search tool. Make multiple searches with different keywords before answering."**

**Answer: 4**

### Why

The agent is given a search tool and told to search multiple times with different keywords. For this question, it decided to search 4 separate times before synthesizing an answer — asking about "agentic loop", "plain RAG", "how agentic RAG differs from RAG", and "RAG vs agentic RAG comparison". The number varies slightly between runs, but 4 is the closest option.

### How

```python
from toyaikit.tools import Tools
from toyaikit.llm import OpenAIClient
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner

def search_lessons(query: str) -> str:
    """Search the lesson chunks for content relevant to the query."""
    results = chunk_index.search(query=query, num_results=5)
    docs = [f"FILE: {doc['filename']}\n\n{doc['content']}" for doc in results]
    return "\n".join(docs)

tools = Tools()
tools.add_tool(search_lessons)

instructions = """
You're a course teaching assistant. Answer the student's question using the
search tool. Make multiple searches with different keywords before answering.
"""

runner = OpenAIResponsesRunner(
    tools=tools,
    developer_prompt=instructions,
    chat_interface=IPythonChatInterface(),
    llm_client=OpenAIClient(model="gpt-5.4-mini")
)

result = runner.loop(
    prompt="How does the agentic loop work, and how is it different from plain RAG?"
)

# The loop internally counts tool calls. Observed: 4 search calls.
```

### The agentic loop (what's happening under the hood)

```python
while True:
    response = call_model(messages)

    if response.has_tool_calls:
        run_tools(response)
        continue

    return response.final_answer
```

### Explanation

The model decides on its own how many times to search.

It searches with different phrasings to gather diverse context.

It stops when it believes it has enough information — no external limit.

This is the defining difference from the fixed, single‑retrieval RAG pipeline in Q3–Q5.
