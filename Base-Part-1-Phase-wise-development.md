# Codebase Intelligence Agent — Complete Project Outline

> **One line**: A fully local, zero-cost CLI tool that clones any GitHub repo, understands it deeply, and answers developer questions with verified, cited answers — using small local models, no cloud dependency.

---

## Core Philosophy

```
Understand first. Generate later. Verify always.
Never depend on infrastructure you don't control.
Add a component only when you've hit the wall that needs it.
```

---

## The Problem You Are Solving

Developers open an unfamiliar codebase and have no fast way to answer:
- "How does auth work here?"
- "Where is the payment logic?"
- "What does this service depend on?"
- "Which files would break if I change this function?"

Existing tools either require expensive LLM APIs, assume you already know the codebase, or give hallucinated answers with no citation.

---

## What You Are Building (Full Vision)

```
User: clone <github_url>
User: ask "how does login work?"

System:
1. Clone + scan repo
2. Detect tech stack (Python, Docker, React, etc.)
3. Parse files into symbols + chunks
4. Store in SQLite + Vector DB + Graph DB
5. Retrieve relevant context (keyword + semantic + structural)
6. Route to right model (local SLM / Gemini / Groq)
7. Generate verified, cited markdown answer
8. Check every cited file/function actually exists

Output: login_flow.md with real file citations
```

---

## Architecture Overview

```
[GitHub Repo]
      |
      v
[Scanner + Tech Detector]
      |
      v
[Parser: symbols, chunks, relations]
      |
      +------------------+------------------+
      |                  |                  |
      v                  v                  v
[SQLite            [Vector DB          [Graph DB
 metadata]          embeddings]         relations]
      |                  |                  |
      +------------------+------------------+
                         |
                         v
               [Context Builder]
               keyword + semantic + structural
                         |
                         v
               [Model Router]
               Ollama / Gemini / Groq via LiteLLM
                         |
                         v
               [Verifier]
               files exist? symbols real? imports valid?
                         |
                         v
               [Output: Markdown / Docs / Query Answer]
```

---

## Phase 0 — Environment Setup
**Goal**: working local AI stack, zero cost

- [ ] Install Ollama, pull `qwen2.5-coder:7b` (Q4 quantized)
- [ ] Install Python 3.11+, create a clean virtual environment
- [ ] Get free Gemini API key (ai.google.dev) — backup/comparison only
- [ ] Pick one real mid-size GitHub repo as your test target
- [ ] Set up basic project folder structure (see below)
- [ ] Verify Ollama responds to a simple prompt via Python `requests`

**Stack decided here**:
- Primary model: Ollama local (your own hardware / Colab T4 for experiments)
- Backup: Gemini free tier / Groq free tier
- Language: Python
- No frameworks yet — everything raw

---

## Phase 1 — Raw RAG Loop (Week 1)
**Goal**: understand retrieval with your own eyes, not a framework's

### What you build
- **Repo cloner**: `git clone` into a temp dir, walk all files
- **Chunker**: split files into small pieces (by function, by N lines — try both)
- **Embedder**: `sentence-transformers` library, local, free, no API
- **Vector store**: plain Python list or SQLite table — no Qdrant yet
- **Retriever**: cosine similarity by hand, return top-k chunks
- **Prompter**: stuff chunks into a prompt, send to Ollama
- **Logger**: print retrieved chunks every single time

### What you learn
- Why chunk size matters (too big = noise, too small = no context)
- Why retrieval quality is the bottleneck, not generation quality
- What cosine similarity actually means on real code

### Checkpoint to pass before Phase 2
Retrieved chunks for "how does auth work?" must actually contain auth-related code.
If they don't, fix retrieval before moving on. This is not optional.

---

## Phase 2 — Tool Calling, Single Agent (Week 2)
**Goal**: agent decides what to look at, not you

### What you build
- **Tool loop** (implement by hand, no LangChain):
  ```
  1. Send tools list + conversation to model
  2. Model returns: "call read_file with {path: auth.py}"
  3. Your code executes it (not the model)
  4. Feed result back into conversation
  5. Repeat until model gives final answer
  ```
- **3 starter tools**:
  - `read_file(path)` — returns file content
  - `search_repo(query)` — calls Phase 1 RAG retriever
  - `list_dir(path)` — lists directory contents
- **SQLite logger**: every tool call, every result, every model response saved
  - This is your episodic memory. No special memory system needed yet.

### What you learn
- What "agentic" actually means at the code level
- How tool call schemas work (JSON schema, model parses it)
- Where agents get stuck in loops or make wrong tool choices
- What your SQLite log tells you about agent behaviour

### Checkpoint
Agent successfully answers "how does auth work?" by calling tools autonomously,
without you telling it which files to read.

---

## Phase 3 — Verifier + Output (Week 3)
**Goal**: trust the output, ship something

### What you build
- **Verifier** (runs on every model output before showing user):
  - Does every cited file path actually exist in the repo?
  - Does every cited function name exist in that file?
  - Are claimed imports real?
  - Flag unverifiable claims, don't silently pass them
- **Markdown generator**: structured output with real file citations
- **CLI wrapper**:
  ```bash
  tool clone https://github.com/user/repo
  tool ask "how does login work?"
  tool ask "what does UserService depend on?"
  ```

### What you learn
- How much LLMs hallucinate even with good retrieval
- How fast deterministic checks catch what the model gets wrong
- What a real developer tool feels like to use

### Checkpoint
Use the tool on 3 different repos. Every answer must have at least 2 citations
that point to real files with real content. No fake function names in output.

---

## Phase 4 — Ship v1 (Week 4)
**Goal**: something real other developers can use

- Write a clear README (setup, usage, model requirements)
- Test on 5 repos of different languages/sizes
- Record a 60-second demo GIF
- Post to GitHub, optionally HN/Reddit devtools
- Collect feedback — what questions does it fail on? Those failures tell you what to build next

---

## Future Phases (research-driven, add only when v1 reveals the need)

### F1 — Real Symbol Extraction
Replace LLM-guessed code understanding with a real AST parser.

- **Tool**: `tree-sitter` (supports 40+ languages, Python bindings available)
- **What it gives you**: exact function names, classes, imports, call sites — not guesses
- **What to store**: SQLite table of `(file, symbol_name, symbol_type, line_start, line_end)`
- **Research topic**: tree-sitter grammars, AST traversal patterns, language-specific edge cases

### F2 — Tech Stack Detection + Routing
Let the agent explore differently based on what kind of repo it is.

- Detect: Dockerfile, package.json, requirements.txt, go.mod, pom.xml etc.
- Route to different exploration strategies (backend-first, frontend-first, infra-first)
- **Research topic**: polyglot repo detection, monorepo structures, dependency graph inference

### F3 — Graph Layer
Answer structural questions SQL can't easily express.

- Start with: SQLite recursive CTEs and parent/child tables (not a graph DB)
- Add Kuzu (embedded graph DB, no server) only when you hit a query pattern SQL can't handle
- **Nodes**: files, functions, classes, API routes, DB tables
- **Edges**: imports, calls, depends_on, writes_to, reads_from
- **Research topic**: static analysis for call graphs, confidence scores (static-verified vs LLM-inferred)
- **Question to verify before building**: what specific query does your SQLite approach fail at?

### F4 — Real Vector DB
Replace your Phase 1 plain-list store with a proper vector DB.

- **Options**: Qdrant (local mode), Chroma (simplest API)
- Only add this when: collection size slows down similarity search, or you need metadata filtering
- **Research topic**: HNSW indexing, payload filters, hybrid search (dense + sparse)

### F5 — Multi-Provider Router (LiteLLM)
Intelligently route different task types to different models.

- Planner role → stronger model (Gemini free tier or Groq Llama 70B)
- Interface/boilerplate writer role → smaller local SLM (3B-7B)
- Verifier role → deterministic tools first, model second
- **Research topic**: model cascading, task-based routing, cost vs quality tradeoffs per task type
- **Only build when**: you have measured that one model isn't enough for all task types

### F6 — Second Agent
Only add when you can name what the first agent structurally cannot do alone.

- Pattern: Orchestrator agent plans → Specialist agent executes one domain
- Candidate split: Explorer agent (reads/searches) + Writer agent (generates output)
- **Research topic**: agent handoff protocols, shared memory between agents, avoiding deliberation loops that waste tokens
- **Warning**: every agent-to-agent handoff = another full LLM call. Count the cost before adding agents.

### F7 — Episodic + Long-Term Memory
Smarter memory than "what happened in this session."

- Episodic: your Phase 2 SQLite log, with semantic search over past sessions
- Long-term: summaries of past repo explorations, so the agent "remembers" a repo it explored before
- **Research topic**: memory consolidation, when to summarize vs when to retrieve raw, forgetting strategies for large repos

### F8 — Evaluation System
Know if the tool is getting better or worse as you add things.

- Build a small test set: 20-30 question/answer pairs on repos you know well
- Run eval after every change
- **Research topic**: RAG evaluation metrics (faithfulness, answer relevance, context precision), LLM-as-judge pitfalls

---

## Folder Structure

```
codebase-agent/
  cli/
    main.py              # entry point: clone, ask, etc.

  core/
    scanner.py           # repo walker, file hash tracker
    chunker.py           # file -> chunks
    embedder.py          # chunks -> vectors
    retriever.py         # cosine similarity search
    tool_loop.py         # tool calling 4-step loop
    verifier.py          # file/symbol existence checks

  tools/
    read_file.py
    list_dir.py
    search_repo.py       # calls retriever

  storage/
    sqlite_store.py      # metadata, task log, tool call log
    vector_store.py      # Phase 1: plain list. Phase 4: Qdrant

  models/
    base.py              # interface all providers implement
    ollama.py            # local Ollama adapter
    gemini.py            # Gemini free tier adapter
    router.py            # Phase 5: LiteLLM-based routing

  output/
    markdown_writer.py   # generates cited markdown

  data/
    agent.db             # SQLite database
    vector/              # vector store files
    cache/               # embedding cache (hash -> vector)

  prompts/
    system.md
    tool_caller.md
    markdown_writer.md
```

---

## Memory Model (Simple Version)

| Type | What it is | Where stored |
|---|---|---|
| In-context | Current conversation + tool results | LLM context window |
| Episodic | Log of every tool call this session | SQLite `tool_log` table |
| Semantic | Embeddings of repo chunks | Vector store |
| Structural | File/symbol/relation facts | SQLite `symbols` table |
| Long-term | Summaries of past repo explorations | SQLite `repo_memory` (Future F7) |

---

## Model Strategy

| Task | Model | Why |
|---|---|---|
| Planning what to search | Gemini free / Groq | Needs reasoning, rare call |
| Executing tool calls | Ollama 7B local | Fast, repeated, cheap |
| Writing markdown output | Ollama 7B local | Templated, constrained |
| Verification | Deterministic code first | Don't pay for what code can check |

Never use a big model for a task a small one or a Python function can do.

---

## Research Topics to Follow (Self-Directed)

These are areas where reading papers and blog posts will actually move you forward:

- **RAG evaluation**: how to measure retrieval quality (not just generation quality)
- **Chunking strategies**: semantic chunking vs fixed-size vs AST-aware
- **Tool call reliability**: how different model sizes handle multi-step tool use
- **Graph RAG**: Microsoft's GraphRAG paper — structural retrieval over knowledge graphs
- **Memory architectures**: MemGPT / Letta project — how they handle context window limits
- **Speculative decoding**: not for you now, but understand it for future
- **Model routing / cascading**: FrugalGPT paper is the primary source, short read

---

## What Success Looks Like at Each Gate

| Phase | Success = |
|---|---|
| Phase 0 | Ollama responds to Python `requests` call |
| Phase 1 | Retrieval for "auth" returns auth-related chunks |
| Phase 2 | Agent calls `search_repo` then `read_file` autonomously |
| Phase 3 | Every cited file in the output actually exists |
| Phase 4 | 3 other developers use it and report what breaks |
| F1 | Symbol table matches `grep` output on same repo |
| F3 | You've hit a query SQLite CTEs can't handle |
| F5 | You've measured a specific task where 7B fails and 70B doesn't |

---

> **The rule**: open the next phase only when you've hit the wall the next phase solves.
> A problem you haven't hit yet is not a reason to build a solution.
