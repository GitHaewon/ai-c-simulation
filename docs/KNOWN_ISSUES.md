# Known Issues & Pre-Production Improvements

---

## Top 5 Most Dangerous Bugs

### 1. Unvalidated LLM JSON causes silent pipeline failure
**Location:** `src/agents/base.py` — `_call_structured()` / `_parse_json()`
**Risk:** If an agent returns malformed JSON (e.g., truncated due to max_tokens, markdown wrapping, or hallucinated schema), `_parse_json()` falls back to an empty `{}`. The next layer receives missing fields and either crashes with an unhandled `KeyError`/`ValidationError`, or silently produces a memo with blank sections.
**Impact:** Full pipeline failure or corrupted memo with no visible error to the user.
**Fix required:** Retry with a correction prompt on parse failure; raise a typed exception after MAX_RETRIES exhausted; never pass `{}` downstream.

---

### 2. ChromaDB state persists across runs without versioning
**Location:** `data/chroma/` (ChromaDB persistent storage)
**Risk:** If the chunk schema changes (e.g., new metadata fields in `ChunkMetadata`) and the old ChromaDB collection is not deleted, `from_chroma_dict()` will fail or return stale/incompatible data. There is no collection version check at startup.
**Impact:** Retrieval returns wrong or no results; agents receive empty context; memos are grounded on nothing.
**Fix required:** Add a collection version tag. On startup, compare the stored version against the current schema version; if mismatched, drop and re-index.

---

### 3. Shock scenario string is passed to agents but never parsed into typed parameters
**Location:** `src/core/pipeline.py` — `_build_financials()` and `src/services/shock_simulator.py`
**Risk:** The `shock_scenario` field is a free-text string (e.g., "Interest rates rise 200bps and a key competitor raises $500M"). The shock simulator currently runs fixed parameterized shocks (±100/200/300 bps, ±10/20% FX, ±20/40% market) regardless of what the user typed. The user's actual scenario text is never used to select or parameterize the shock.
**Impact:** The "active shock" label in the UI shows the user's text, but the underlying calculation is unrelated to it. This is misleading and constitutes a feature gap that looks like a bug to end users.
**Fix required:** Parse the shock_scenario string with an LLM call or regex into typed parameters (`ShockParams`) and pass them to the simulator; fall back to default scenarios if parsing fails.

---

### 4. LangGraph state fan-in race condition on `error_log`
**Location:** `src/models/state.py` — `ICState` / `src/agents/orchestrator.py`
**Risk:** `stage_log` and `error_log` use `Annotated[list[str], operator.add]` for concurrent-safe writes. However, any agent that writes to a non-annotated field (e.g., accidentally setting `financial_output` from two nodes simultaneously if the graph is rewired) will cause LangGraph to raise a `InvalidUpdateError` or silently overwrite state.
**Impact:** In the current graph topology this is safe, but any future graph change (adding a node, changing fan-out) can trigger non-deterministic state corruption with no obvious error message.
**Fix required:** Add a startup assertion that validates the graph topology; add integration tests that verify parallel writes do not corrupt state.

---

### 5. API key exposed in `.env.example` (historical — must verify rotation)
**Location:** Git history (commit before the key was replaced with a placeholder)
**Risk:** The real Anthropic API key `sk-ant-api03-nH0BpxwZNg94...` was committed to `.env.example` in an earlier session. Even though the file now contains only a placeholder, the key may be in git history and could be extracted with `git log -p`.
**Impact:** If the key has not been rotated, any person with access to the repository can make API calls billed to the account owner.
**Fix required:** **Immediately revoke the exposed key** at [console.anthropic.com](https://console.anthropic.com) and generate a new one. Then run `git filter-repo` or `BFG Repo Cleaner` to purge the key from git history before making the repository public.

---

## Pre-Production Improvements Required

### Architecture

| # | Issue | Priority |
|---|-------|----------|
| 1 | **Agent retry + correction loop** — currently agents call Claude once; structured output calls must retry with a correction prompt on schema validation failure | HIGH |
| 2 | **Shock scenario parsing** — parse free-text shock input into typed parameters; currently the user's text is displayed but not used in computation | HIGH |
| 3 | **ChromaDB collection versioning** — add version tag to prevent stale index issues across code changes | HIGH |
| 4 | **Default financials are hardcoded** — `ICPipeline._build_financials()` uses fixed defaults (revenue=$5M, growth=50%, multiple=8x) when the user does not provide them; this makes all deals look alike | MEDIUM |
| 5 | **No authentication on Streamlit** — any person who can reach `localhost:8501` can run the pipeline and consume API credits | MEDIUM |
| 6 | **PPTX template is hardcoded** — slide layout, colors, and fonts are defined inline in `pptx_builder.py`; should be driven by a configurable template file | LOW |

### Observability

| # | Issue | Priority |
|---|-------|----------|
| 7 | **No structured logging to file** — logs go only to stderr; add `logging.FileHandler` with rotation for production debugging | MEDIUM |
| 8 | **No token usage tracking** — Claude API token counts are logged per-call but not aggregated; add a per-run token budget and alert when approaching limits | MEDIUM |
| 9 | **Retrieval quality is not evaluated** — add a retrieval evaluation harness (Precision@K, MRR) to catch regressions when chunking or embedding parameters change | LOW |

### Security

| # | Issue | Priority |
|---|-------|----------|
| 10 | **API key rotation** (see Bug #5 above) | CRITICAL |
| 11 | **No rate limiting on the pipeline** — a user can click "Run IC Simulation" repeatedly; add a per-session cooldown or a queue | MEDIUM |
| 12 | **Uploaded documents not sanitized** — if document upload is added in future, validate file type, size, and content before indexing | HIGH (when implemented) |

### Testing

| # | Issue | Priority |
|---|-------|----------|
| 13 | **Integration tests use placeholder agents** — `test_orchestrator.py` tests graph structure but not real LLM outputs; add integration tests with mocked Claude responses validated against the Pydantic schema | HIGH |
| 14 | **No end-to-end regression test** — there is no single test that runs the full pipeline (RAG + agents + simulation + memo) and asserts on the output structure | HIGH |
| 15 | **Windows console encoding** — `print()` with non-ASCII characters fails under CP949; run all scripts with `PYTHONIOENCODING=utf-8` in CI | LOW |
