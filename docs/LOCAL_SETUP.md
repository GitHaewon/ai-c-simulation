# Local Setup Guide

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.11+   |
| Git         | any     |
| Anthropic API key | [console.anthropic.com](https://console.anthropic.com) |

---

## 1. Clone & Install

```powershell
git clone https://github.com/GitHaewon/ai-c-simulation.git
cd ai-c-simulation

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> If the activation script is blocked on Windows, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

---

## 2. Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...     # Required
APP_ENV=development
LOG_LEVEL=INFO
```

---

## 3. Index Demo Documents (one-time)

This step loads the sample deal documents into the Hybrid RAG engine (ChromaDB).

```powershell
python data/samples/index_demo_data.py
```

Expected output:
```
[INFO] Indexed acme_ai_im.txt → N chunk(s)
[INFO] Indexed market_research.txt → N chunk(s)
[INFO] ChromaDB total: N chunks
```

---

## 4. Run Options

### Option A — Streamlit UI (recommended)

```powershell
streamlit run app/main.py
```

Open `http://localhost:8501` in your browser.

**How to use:**
1. Enter a company name and industry in the sidebar
2. (Optional) define a shock scenario
3. Click **Run IC Simulation**
4. View results in the three tabs: IC Memo · Shock Simulation · AI IC Debate
5. Download the memo as Markdown, JSON, or PPTX

### Option B — CLI Demo Runner

```powershell
python scripts/run_demo.py
```

Runs the pre-configured Acme AI demo and saves outputs to `data/output/`:
- `ic_memo.json`
- `ic_memo.md`
- `ic_memo.pptx`

---

## 5. Run Tests

```powershell
# Individual smoke tests
python scripts/test_claude_client.py
python scripts/test_orchestrator.py
python scripts/test_rag.py
python scripts/test_shock_simulation.py
python scripts/test_memo_generator.py
```

---

## Project Structure (quick reference)

```
src/
  agents/       Multi-agent IC nodes (LangGraph)
  core/         ClaudeClient, ICPipeline
  models/       Pydantic data models
  prompts/      LLM prompt templates
  services/     Deterministic logic (memo, shock, viz)
  tools/        Hybrid RAG engine

app/            Streamlit UI
data/samples/   Demo deal + documents
scripts/        CLI runners and tests
docs/           This file and architecture notes
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ANTHROPIC_API_KEY is not set` | Check `.env` and that `.venv` is activated |
| `chromadb` import error | `pip install chromadb` (may need Rust toolchain on first install) |
| `sentence-transformers` slow first run | Downloading model weights (~130MB) — one-time only |
| `streamlit: command not found` | Ensure `.venv` is activated |
| PPTX download hangs in browser | Try a different browser; file is written to a temp path |
