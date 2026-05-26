# AI Investment Committee Simulation & IC Memo Generation System

> Simulate a full multi-agent Investment Committee process and automatically generate professional IC memos — with shock stress-testing and live deliberation view.

---

## Overview

Six AI agents assume distinct IC roles (Data Collection, Financial Analyst, Risk Officer, Bull Advocate, Bear Advocate, Chairman) and run in parallel on any deal input. The Chairman synthesizes votes into a final decision. The output is a structured IC memo exportable as Markdown, JSON, or PPTX.

### Features

- **Multi-agent IC simulation** — LangGraph parallel fan-out/fan-in; each agent has a fixed persona, scope, and vote authority
- **Hybrid RAG** — dense (ChromaDB + BGE) + sparse (BM25) retrieval with Reciprocal Rank Fusion; agents cite sources
- **Shock simulation** — deterministic IRR/MOIC stress-test (rate shock, FX shock, market downturn) with tornado chart
- **IC Memo generation** — auto-assembled from agent outputs; exports to Markdown, JSON, and 7-slide PPTX
- **Streamlit UI** — live deliberation transcript, scenario charts, memo download

---

## Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Anthropic API key | [console.anthropic.com](https://console.anthropic.com) |

### Install

```powershell
git clone https://github.com/GitHaewon/ai-c-simulation.git
cd ai-c-simulation

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

python -m pip install --upgrade pip
pip install -r requirements.txt
```

> If the activation script is blocked on Windows, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Configure

```powershell
Copy-Item .env.example .env
```

Open `.env` and set:

```
ANTHROPIC_API_KEY=sk-ant-...   # required
APP_ENV=development
LOG_LEVEL=INFO
```

### Index demo documents (one-time)

```powershell
python scripts/run_demo.py --index-only
```

### Run the app

```powershell
streamlit run app.py
```

Open `http://localhost:8501`, enter a company name + industry in the sidebar, and click **Run IC Simulation**.

**Tabs:**
1. **IC Memo Draft** — full memo with download buttons (MD / JSON / PPTX)
2. **Shock Simulation** — IRR/MOIC scenario charts and tornado chart
3. **AI IC Debate** — live deliberation transcript with agent votes

---

## CLI Demo Runner

```powershell
python scripts/run_demo.py
```

Runs the pre-configured Acme AI deal and saves outputs to `data/output/`:
- `ic_memo.json`, `ic_memo.md`, `ic_memo.pptx`

---

## Run Tests

```powershell
python scripts/test_claude_client.py
python scripts/test_orchestrator.py
python scripts/test_rag.py
python scripts/test_shock_simulation.py
python scripts/test_memo_generator.py
```

---

## Project Structure

```
src/
  agents/       Multi-agent IC nodes (LangGraph)
  core/         ClaudeClient, ICPipeline
  models/       Pydantic data models
  prompts/      LLM prompt templates (versioned .txt)
  services/     Deterministic logic (memo, shock, viz)
  tools/        Hybrid RAG engine (BM25 + dense + RRF)

app/            Streamlit UI (pages + components)
data/samples/   Demo deal + indexed documents
scripts/        CLI runners and smoke tests
docs/           Setup guide and architecture notes
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ANTHROPIC_API_KEY is not set` | Check `.env` file exists and `.venv` is activated |
| `chromadb` import error | `pip install chromadb` (may need Rust toolchain on first install) |
| `sentence-transformers` slow first run | Downloading model weights (~130 MB) — one-time only |
| `streamlit: command not found` | Ensure `.venv` is activated |
| HuggingFace symlink warning on Windows | Harmless; enable Developer Mode to suppress it |
| PPTX download hangs in browser | Try a different browser; file is written to a temp path |
| Unicode errors in Windows terminal | Run `$env:PYTHONIOENCODING="utf-8"` before launching |
| Very high IRR (> 100%) in demo | Mathematically correct for 60% growth + 5-year hold; adjust inputs for realism |

---

## Known Issues & Pre-Production Improvements

See [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for the top bugs and required improvements before production.

---

## Team

| Name | GitHub |
|------|--------|
| Park Haewon | [@ejin-14](https://github.com/ejin-14) |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
