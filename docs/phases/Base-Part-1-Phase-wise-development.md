# Hierarchical Cognitive Runtime — Research & Project Blueprint

> **Core Research Question**: Can a hierarchical cognitive runtime dynamically allocate computation between deterministic rules, small local models (SLMs), tools, and large models (LLMs) to perform complex software engineering tasks with comparable quality but significantly lower latency and token cost than routing all operations to a frontier LLM?

---

## 1. Executive Vision & Philosophy

Rather than building another static LLM wrapper or complex multi-agent framework, this project is structured as an **empirical research program**.

```
                   [ TASK INPUT ]
                         │
                         ▼
             ┌───────────────────────┐
             │   COMPLEXITY ROUTER   │
             │   & LEADER ENGINE     │
             └───────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  [ RULES / TOOLS ]   [ SLM ]         [ LLM ]
    Deterministic    Fast/Cheap    Reasoning/Plan
  (Zero LLM cost)   (Local 7B)     (Frontier/APIs)
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │ TELEMETRY & VERIFIER  │
             └───────────┬───────────┘
                         │
                         ▼
            [ VERIFIED RESULT + METRICS ]
```

### Strategic Rules
1. **Understand First, Generate Second, Verify Always.**
2. **Compute Allocation over Token Dumping**: Never use a 70B+ model for a task a 7B SLM, an AST parser, or a regex string filter can handle.
3. **No Unmeasured Complexity**: Never add an agent, memory type, or database without an empirical benchmark proving its necessity.
4. **Isolate Distractions**: All ideas not currently being tested belong in `IDEAS.md`, not in active code.

---

## 2. Minimal Initial Target Architecture (Version 1.0)

```
                       USER / TASK
                            │
                            ▼
                    ┌───────────────┐
                    │  LEADER LLM   │
                    │  (Planner)    │
                    └───────┬───────┘
                            │
                   Delegates Task Schema
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌───────────────────┐       ┌───────────────────┐
    │    CODE AGENT     │       │   SEARCH / RAG    │
    │  (Local SLM / 7B) │       │   RETRIEVER       │
    └─────────┬─────────┘       └─────────┬─────────┘
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  TOOL LAYER   │
                    │ (AST / Files) │
                    └───────┬───────┘
                            │
                            ▼
                      TARGET CODEBASE
```

---

## 3. The Core Measurement Rig (Build First)

Every execution generates a telemetry trace stored in `data/telemetry.db` (SQLite):

```json
{
  "task_id": "task_012",
  "task_type": "symbol_navigation",
  "baseline_run": false,
  "execution_path": ["LeaderLLM", "CodeAgent", "read_file_tool"],
  "models_used": ["qwen2.5-coder:7b", "gemini-2.5-flash"],
  "model_calls": 2,
  "input_tokens": 1420,
  "output_tokens": 310,
  "latency_ms": 1180,
  "tool_calls_count": 3,
  "cost_usd_estimate": 0.00014,
  "verification_passed": true,
  "accuracy_score": 1.0
}
```

### Metrics Recorded
- **Task Success Rate (%)**: Percentage of benchmarks passing deterministic verification.
- **Latency (p50 / p95)**: Wall-clock time to complete task.
- **Token Efficiency**: (Input + Output Tokens) per successful answer.
- **Compute Cost ($)**: Realized cost per benchmark run vs. baseline direct frontier LLM query.

---

## 4. Phased Development Roadmap

```
Phase 0: Research Spec & Telemetry Rig
   └── 1-2 Weeks | Setup docs, telemetry loggers, benchmark dataset.
Phase 1: Deterministic Code Intelligence Core
   └── 2-4 Weeks | Scanner, Tree-sitter AST, Vector RAG, Tool APIs.
Phase 2: Single Leader Orchestrator
   └── 2 Weeks   | Leader model delegating to execution routines.
Phase 3: Multi-SLM Compute Split
   └── 3 Weeks   | Local routing: Router SLM vs Code SLM vs Reasoning LLM.
Phase 4: Progressive Memory Architecture
   └── 3 Weeks   | Working memory -> Episodic -> Semantic Graph.
Phase 5: Dynamic Cost-Optimal Routing Engine
   └── 2 Weeks   | Adaptive model selection based on cost-quality trade-offs.
Phase 6: Self-Reflection & Evaluation
   └── Ongoing   | Failure log feedback loops and benchmark automation.
Extensions: Voice & Hardware Protocols
   └── Future    | Voice interface & hardware IO bindings.
```

---

### Phase 0 — Research Specification & Telemetry Setup
**Objective**: Build the measurement system and define the baseline before writing feature code.

- [ ] Create core documentation framework (`docs/` directory).
- [ ] Build `telemetry.py` to record task traces, latency, model usage, and costs.
- [ ] Write a 10-question ground-truth benchmark suite on a fixed target repository.
- [ ] Establish the **Baseline**: Run all 10 benchmark tasks directly through a single frontier LLM call without tools or local routing. Record latency, cost, and accuracy.

---

### Phase 1 — Deterministic Code Intelligence Engine
**Objective**: Build local code parsing and RAG infrastructure.

- [ ] **Repo Scanner & AST Parser**: Integrated `tree-sitter` scanner to parse functions, classes, and import relations.
- [ ] **Hybrid Retriever**:
  - Dense search: Local embeddings (`sentence-transformers`).
  - Sparse search: Exact symbol lookup in SQLite metadata table.
- [ ] **Core Tool Layer**:
  - `read_file(path, line_range)`
  - `find_symbol(symbol_name)`
  - `search_code(query)`
  - `list_dir(path)`
- [ ] **Verification Engine**: Deterministically test if file paths and symbol names cited in output actually exist.

---

### Phase 2 — Leader & Delegation Loop
**Objective**: Transition from direct scripting to an orchestrated task loop.

- [ ] Implement Leader interface: Decomposes human prompt into structured JSON subtasks.
- [ ] Build tool caller loop: Iteratively calls code retrieval tools until task goals are satisfied.
- [ ] Record evaluation metrics against Phase 0 baseline: Measure tool call efficiency vs raw context loading.

---

### Phase 3 — Heterogeneous Multi-SLM Operations
**Objective**: Replace single-model reliance with task-specialized SLMs.

- [ ] **Router SLM** (3B parameters / local rules): Fast task categorization (e.g., Code Search vs Modification vs Analysis).
- [ ] **Code SLM** (`qwen2.5-coder:7b`): Local code understanding and file content inspection.
- [ ] **Reasoning Model** (Gemini Free / Groq Llama-70B / Claude): Triggered only when architectural reasoning or multi-step logic is required.

---

### Phase 4 — Tiered Memory Architecture
**Objective**: Context-window reduction through structured retention layers.

```
┌────────────────────────────────────────────────────────┐
│ WORKING MEMORY     : Active task context (In-prompt)  │
├────────────────────────────────────────────────────────┤
│ EPISODIC MEMORY    : SQLite history of past tool runs  │
├────────────────────────────────────────────────────────┤
│ SEMANTIC MEMORY    : Vector embeddings of repo code    │
├────────────────────────────────────────────────────────┤
│ STRUCTURAL MEMORY  : Tree-sitter AST symbol database   │
└────────────────────────────────────────────────────────┘
```

- [ ] Benchmark: Test context size reduction and latency changes after shifting context from raw history to structured episodic summaries.

---

### Phase 5 — Dynamic Routing Engine
**Objective**: Route execution dynamically based on estimated context size, step complexity, and required model capabilities.

```
                      TASK INPUT
                          │
             ┌────────────┴────────────┐
             │ Complexity Classifier   │
             └────────────┬────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   Low Complexity   Medium Complexity High Complexity
   (Deterministic/  (7B Local SLM)     (Frontier LLM /
    AST Search)                         Multi-Step Plan)
```

- [ ] Benchmark against baseline: Evaluate total API cost savings and latency reduction while targetting zero accuracy loss on benchmark tests.

---

### Phase 6 — Reflection & Adaptive Learning
**Objective**: Establish automated self-evaluation and context correction loops.

- [ ] Analyze execution trace failures post-run.
- [ ] Implement self-correction loop: Re-run failed steps with augmented context when verifier flags missing citations or invalid code references.

---

### Extensions — Interface Layer (Voice & Hardware)
*Only to be touched after Phase 6 benchmarks confirm system stability.*

- [ ] Speech-To-Text / Text-To-Speech stream bindings.
- [ ] Hardware interface bindings (System processes, GPIO, CLI controllers).

---

## 5. Daily Execution System & Notebook Protocols

To prevent scope creep and maintain research velocity, all daily tasks follow a strict 3-notebook rule and a daily quota system.

### The Three Notebooks

1. `BUILD.md`
   - Active milestone focus only.
   - List of 1–3 concrete code tasks for the current day.
   - Completed tasks checklist.

2. `RESEARCH.md`
   - Log of all benchmark runs and experiment results.
   - Documented tradeoffs (e.g., "AST search vs Vector search for symbol lookup").
   - Failure analysis logs.

3. `IDEAS.md`
   - **The Containment Zone**: Every new idea, architecture expansion, or hardware concept is written here immediately.
   - **Strict Rule**: No idea in `IDEAS.md` may be implemented until the current phase checkpoint passes.

---

### Daily Quota Protocol
- **Target**: 60 minutes per day minimum.
- **Absolute Floor**: 20 minutes per day (e.g., write 1 test, update 1 benchmark log, parse 1 tool file).
- **Rule**: Never let the code repository sit inactive for a full calendar day.

---

## Strategic Evaluation & Next Steps

### 1. Assessment of the Strategy Shift
Shifting from a standard "Codebase CLI Tool" to an **empirical research program on compute allocation** changes the dynamic of your work:

* **Eliminates "Architectural Overwhelm"**: Instead of worrying about how to build a giant system with 10 features, every feature must now justify its existence through a measurable metric (latency, token savings, or accuracy).
* **High-Value Resume & Portfolio Differentiation**: Anyone can follow a tutorial to set up LangChain or AutoGen wrappers. Building an empirically evaluated cognitive runtime with latency/cost telemetry demonstrates deep systems engineering and research discipline.
* **Protects Existing Code**: You do not throw away your repository. Your existing scanner, chunker, and embedder logic become the foundation for **Phase 1** tools.

---

### 2. What to Watch Out For (Potential Pitfalls)
1. **The Benchmark Creation Trap**: Do not spend two weeks building an overly complex benchmark suite. Start with **10 simple human-written questions** about a repository you know well.
2. **Framework Dependency**: Avoid heavy agent frameworks (LangChain, CrewAI, AutoGen). They mask model latency, add hidden token overhead, and make precise system telemetry difficult. Keep your runtime logic in standard Python.
3. **Idea Intrusion**: When working on Phase 1, you will inevitably think about graph memory or voice control. Put them in `IDEAS.md` immediately and return to the task at hand.

---

### 3. The Concrete Starting Point (Day 1 / Tomorrow)

Do not redesign the codebase tomorrow. Execute these **three distinct tasks**:

#### Step 1: Create the Doc Structure (10 Minutes)
Create these exact files in your repository root:
- `docs/RESEARCH_QUESTION.md`
- `BUILD.md`
- `RESEARCH.md`
- `IDEAS.md`

#### Step 2: Write `RESEARCH_QUESTION.md` (20 Minutes)
Copy and save the core question, metrics, and baseline plan:
```markdown
# Research Question
Can a hierarchical cognitive runtime dynamically allocate computation between deterministic rules, local SLMs, tools, and LLMs to perform software engineering tasks with comparable quality but lower cost and latency than a direct LLM call?

## Metrics
- Task Accuracy (%)
- Latency p50/p95 (ms)
- Input/Output Tokens per successful task
- Estimated Cost ($)

## Baseline
- Direct prompt containing full file context sent to a single frontier LLM model call.
```

#### Step 3: Define 10 Ground-Truth Benchmark Tasks (30 Minutes)
Pick **one repo** you know well. Create `data/benchmarks.json` with 10 concrete questions/tasks:
```json
[
  {
    "id": "task_01",
    "question": "Where is the main entry point defined, and what primary dependencies does it initialize?",
    "target_files": ["src/main.py"],
    "expected_symbols": ["main", "init_app"]
  },
  {
    "id": "task_02",
    "question": "Which file handles user database connection configurations?",
    "target_files": ["src/db/config.py"],
    "expected_symbols": ["get_db_connection"]
  }
]
```

At the end of these 60 minutes, your research environment will be set up, your goals will be clear, and you will be ready to begin building Phase 1.