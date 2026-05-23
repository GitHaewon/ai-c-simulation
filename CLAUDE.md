# CLAUDE.md — AI Investment Committee Simulation & IC Memo Generation System

This file is the authoritative reference for all AI-assisted development on this project.
Read it fully before writing any code, designing any prompt, or modifying any structure.

---

## 1. Project Goals

Build a system that simulates a real-world Investment Committee (IC) process end-to-end and produces a professional IC memo as output.

| Goal | Description |
|------|-------------|
| IC Workflow Automation | Replicate the sequential stages of a real IC: deal intake → due diligence → committee deliberation → vote → memo |
| Multi-Agent Orchestration | Each IC member role is an independent LLM agent with a defined persona, scope, and authority |
| Hybrid RAG | Combine dense vector retrieval (semantic) and sparse keyword retrieval (BM25) to ground agents in deal documents and market data |
| Shock Simulation | Stress-test investment theses against user-defined macro/sector shocks before finalizing the memo |
| IC Memo Generation | Produce a structured, human-review-ready memo from the committee's deliberation output |

---

## 2. System Architecture

```
User Input (Deal Data)
        │
        ▼
┌───────────────────┐
│  Orchestrator     │  ← coordinates agent sequence, manages state
└────────┬──────────┘
         │
    ┌────┴─────────────────────────────────┐
    │         Agent Layer                  │
    │  ┌──────────┐  ┌──────────────────┐  │
    │  │ Lead     │  │ Financial        │  │
    │  │ Partner  │  │ Analyst          │  │
    │  └──────────┘  └──────────────────┘  │
    │  ┌──────────┐  ┌──────────────────┐  │
    │  │ Legal &  │  │ Risk             │  │
    │  │ Compliance│  │ Officer          │  │
    │  └──────────┘  └──────────────────┘  │
    │  ┌──────────┐                        │
    │  │ Portfolio│                        │
    │  │ Manager  │                        │
    │  └──────────┘                        │
    └────────┬─────────────────────────────┘
             │
    ┌────────▼──────────┐
    │  Hybrid RAG Layer │  ← dense (vector) + sparse (BM25) retrieval
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │  Shock Simulator  │  ← stress test against macro/sector scenarios
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │  Memo Builder     │  ← assembles structured IC memo from agent outputs
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │  Streamlit UI     │  ← deal input, live deliberation view, memo export
    └───────────────────┘
```

### Directory Map

```
src/
  agents/      ← agent class definitions and orchestrator
  prompts/     ← all system and user prompt templates (.txt or .yaml)
  tools/       ← agent tools: retrieval, calculator, web search, …
  models/      ← Pydantic data models (Deal, AgentOutput, ICMemo, …)
  services/    ← deterministic business logic (voting engine, memo builder, shock simulator)
app/
  pages/       ← Streamlit page modules
  components/  ← reusable Streamlit UI components
tests/
  unit/        ← pure function tests (models, services)
  integration/ ← end-to-end agent and RAG pipeline tests
config/        ← YAML/TOML configuration files
data/
  samples/     ← sample deal inputs for development and testing
  templates/   ← IC memo output templates
```

---

## 3. Agent Roles

Each agent has a fixed **role**, **persona**, **scope**, and **output schema**. Agents do not share internal state directly — they communicate through the orchestrator.

| Agent | Role | Primary Scope |
|-------|------|---------------|
| **Lead Partner** | Chair of the IC | Investment thesis validation, final recommendation |
| **Financial Analyst** | Numbers owner | Financial model review, valuation, return scenarios |
| **Legal & Compliance** | Gate keeper | Regulatory risk, deal structure, red flags |
| **Risk Officer** | Devil's advocate | Downside scenarios, concentration risk, exit risk |
| **Portfolio Manager** | Portfolio lens | Portfolio fit, diversification, follow-on capacity |

### Agent Output Contract

Every agent must return a structured object containing:
- `agent_id` — which agent produced this
- `section` — which part of the memo this contributes to
- `findings` — key observations (list of strings)
- `concerns` — flagged risks (list of strings)
- `vote` — `APPROVE | CONDITIONAL | REJECT`
- `vote_rationale` — one-paragraph justification
- `confidence` — float 0.0–1.0

This schema is defined in `src/models/` and must not be bypassed.

---

## 4. Coding Conventions

### General

- **Python 3.11+** only
- Type hints on every function signature — no bare `Any` unless truly unavoidable
- Pydantic v2 for all data models; never use raw `dict` to pass structured data between layers
- `ruff` for linting and formatting (line length: 100); `mypy` for type checking — both must pass in CI
- No `print()` in production code — use `logging` with the module-level logger
- One class or one logical group of functions per file; keep files under ~300 lines

### Naming

| Kind | Convention | Example |
|------|-----------|---------|
| Files | `snake_case` | `lead_partner_agent.py` |
| Classes | `PascalCase` | `LeadPartnerAgent` |
| Functions / variables | `snake_case` | `build_memo_section` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_AGENT_RETRIES` |
| Pydantic models | `PascalCase` | `DealInput`, `ICMemo` |
| Prompt template files | `snake_case.txt` | `lead_partner_system.txt` |

### Imports

Order: stdlib → third-party → internal. Separate each group with a blank line.

```python
import logging
from pathlib import Path

from pydantic import BaseModel

from src.models.deal import DealInput
```

### Comments

- Write comments only when the **why** is non-obvious
- No block comments narrating what the code does — the code does that
- One-line docstring max on public functions; skip it if the name is self-explanatory

---

## 5. Deterministic Logic vs. LLM Reasoning — Separation Principle

This is the most important architectural rule.

| Layer | Handled by | Examples |
|-------|-----------|---------|
| **Deterministic** | Pure Python (`src/services/`) | Vote tallying, quorum check, IRR/MOIC calculation, memo section assembly, schema validation, shock parameter application |
| **LLM Reasoning** | Agent calls (`src/agents/`) | Qualitative analysis, risk narrative, investment thesis, vote rationale, deal judgment |

### Rules

1. **Never call an LLM to compute a number** that can be computed deterministically (IRR, MOIC, debt coverage, portfolio weight, etc.).
2. **Never use LLM output directly** as a control-flow value — always parse it into a typed Pydantic model first.
3. **All LLM outputs must be validated** against their schema before passing to the next layer. If validation fails, retry with a correction prompt; do not silently pass bad data.
4. The voting engine, memo assembler, and shock simulator live in `src/services/` and contain **zero LLM calls**.
5. When in doubt: if the answer is always the same given the same inputs, it is deterministic — keep it out of the LLM.

---

## 6. Hybrid RAG Principles

### Architecture

Hybrid RAG = **dense retrieval (vector)** + **sparse retrieval (BM25)** → **reciprocal rank fusion (RRF)** → reranker → context window.

```
Query
  ├─► Dense Retriever  (embedding similarity)  ─┐
  └─► Sparse Retriever (BM25 keyword match)    ─┴─► RRF → Reranker → Top-K chunks → Agent context
```

### Rules

1. **Chunk size**: 512 tokens with 64-token overlap — do not change without benchmarking retrieval quality.
2. **Metadata always travels with chunks**: source document, page/section, date, deal ID — agents must cite sources in their findings.
3. **Retrieval is a tool**, not a preprocessing step — agents call retrieval tools on demand; do not pre-load all documents into the context window.
4. **Sparse retrieval is mandatory** for financial figures, names, and ticker symbols — embedding models are unreliable for exact numeric and entity matching.
5. **Top-K after reranking**: 5 chunks per agent call unless the agent explicitly requests more.
6. All retrieval calls must be logged with the query, retrieved chunk IDs, and scores for evaluation and debugging.

---

## 7. Prompt Engineering Principles

### Structure

Every prompt template is stored in `src/prompts/` as a `.txt` or `.yaml` file. Prompts are **never** hard-coded as inline strings in agent or service files.

### System Prompt Rules

1. State the agent's **role and persona** in the first two sentences.
2. State the agent's **scope boundary** — what it must NOT do (e.g., Financial Analyst must not give legal opinions).
3. State the **output format** explicitly and include a JSON schema or example.
4. Include a **chain-of-thought instruction**: "Think step by step before producing your final answer."
5. Include an **uncertainty instruction**: "If you do not have sufficient information, state what is missing rather than guessing."

### User Prompt Rules

1. Always inject retrieved context under a clearly labelled section header (`## Retrieved Context`).
2. Always inject the deal summary under `## Deal Summary`.
3. Keep injected context under 2,000 tokens per call — truncate and note truncation if necessary.
4. Never inject raw file bytes or unstructured dumps.

### Versioning

- Prompt files are versioned alongside the codebase in git.
- When a prompt changes, update the version comment at the top of the file: `# version: 1.2.0`.
- Prompt changes that affect agent output schema are breaking changes — treat them as such.

### What LLMs Must Not Decide

- Numeric computations (see Section 5)
- Which documents to retrieve (the retrieval tool decides based on the query)
- Whether to proceed to the next pipeline stage (the orchestrator decides)
- Final vote tallying (the voting engine in `src/services/` decides)

---

## 8. Git Convention

### Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready, always deployable |
| `dev` | Integration branch — merge feature branches here first |
| `feat/<short-name>` | New feature |
| `fix/<short-name>` | Bug fix |
| `chore/<short-name>` | Tooling, config, dependency updates |
| `docs/<short-name>` | Documentation only |

All work happens on feature branches. **Never commit directly to `main`.**

### Commit Messages

Format: `<type>(<scope>): <short imperative summary>`

```
feat(agents): add LeadPartner agent with vote output
fix(rag): correct BM25 score normalization in hybrid fusion
chore(deps): add langchain-community 0.2.x
docs(prompts): document system prompt versioning policy
```

Types: `feat` `fix` `chore` `docs` `test` `refactor` `perf`

- Subject line: max 72 characters, imperative mood, no period
- Body (optional): explain **why**, not what
- Reference issues: `Closes #12` at the end of the body

### Pull Requests

- PR title follows the same `type(scope): summary` format
- All PRs require at least one review before merging to `main`
- Squash merge into `main`; merge commit into `dev`
- Delete the feature branch after merge

### Tags

Use semantic versioning: `v0.1.0`, `v0.2.0`, `v1.0.0`

---

## 9. Prohibited Actions

The following are **hard stops** — do not do these under any circumstances.

### Code Quality

- Do not use `Any` as a return type or parameter type without a comment explaining why
- Do not suppress type errors with `# type: ignore` without a comment
- Do not catch bare `except:` — always catch a specific exception
- Do not use `eval()` or `exec()` anywhere in the codebase
- Do not hard-code API keys, credentials, or secrets — always read from environment variables
- Do not commit `.env` files — `.env.example` is the only allowed env file in git

### LLM Usage

- Do not call an LLM to perform arithmetic or aggregation that Python can compute
- Do not pass unvalidated LLM output to the next pipeline stage
- Do not embed prompt text inline in agent Python files — use `src/prompts/`
- Do not set `temperature > 0.3` for structured output calls (vote, schema output)
- Do not use streaming responses for structured output — use non-streaming and validate the full response

### Architecture

- Do not add business logic to Streamlit page files — pages call services, they do not implement logic
- Do not let agents call other agents directly — all inter-agent communication goes through the orchestrator
- Do not put retrieval logic inside agent classes — agents call retrieval tools; tools live in `src/tools/`
- Do not skip the Pydantic model layer — raw dicts must not flow between `src/` modules

### Git

- Do not force-push to `main` or `dev`
- Do not commit directly to `main`
- Do not commit files larger than 10 MB (use Git LFS or external storage)
- Do not commit Jupyter notebooks with cell outputs included

---

*Last updated: 2026-05-24*
