# AI Investment Committee Simulation & IC Memo Generation System

> Simulate a multi-agent Investment Committee (IC) process and automatically generate professional IC memos from deal inputs.

---

## Overview

This system leverages large language model (LLM) agents to replicate the dynamics of a real-world Investment Committee. Given a deal's key information, multiple AI agents assume distinct IC member roles (e.g., Lead Partner, CFO, Legal Counsel, Risk Officer) and conduct a structured deliberation. The outcome is a polished IC memo ready for human review.

### Key Features (planned)

- **Multi-agent IC simulation** — each agent holds a defined role, perspective, and voting weight
- **IC Memo auto-generation** — structured output covering investment thesis, risks, financials, and recommendation
- **Interactive review UI** — Streamlit-based interface for deal input and memo export
- **Configurable agent profiles** — customize committee composition per deal type

---

## Project Structure

```
ai-ic-simulation/
├── src/
│   ├── agents/          # IC member agent definitions and orchestration
│   ├── prompts/         # System & user prompt templates
│   ├── tools/           # Agent tools (search, calculator, document retrieval, …)
│   ├── models/          # Pydantic data models (Deal, ICMemo, VoteResult, …)
│   └── services/        # Business logic (memo builder, voting engine, …)
├── app/
│   ├── pages/           # Streamlit page modules
│   └── components/      # Reusable UI components
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── architecture/    # System design diagrams and ADRs
│   └── api/             # API reference
├── config/              # Configuration files (YAML/TOML)
├── scripts/             # Utility and setup scripts
├── data/
│   ├── samples/         # Sample deal inputs for testing
│   └── templates/       # IC memo output templates
├── .env.example         # Required environment variables (copy to .env)
├── requirements.txt     # Python dependencies (to be added)
└── README.md
```

---

## Getting Started

> **Prerequisites:** Python 3.11+, an Anthropic API key

```bash
# 1. Clone the repository
git clone https://github.com/<org>/ai-ic-simulation.git
cd ai-ic-simulation

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies (once requirements.txt is ready)
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in your API keys
```

---

## Roadmap

- [ ] Phase 1 — Repository & collaboration setup *(current)*
- [ ] Phase 2 — Core data models and prompt templates
- [ ] Phase 3 — Individual IC agent implementation
- [ ] Phase 4 — Multi-agent orchestration and voting engine
- [ ] Phase 5 — IC Memo generation pipeline
- [ ] Phase 6 — Streamlit UI
- [ ] Phase 7 — Testing, evaluation, and refinement

---

## Team

| Name | GitHub |
|------|--------|
| Park Haewon | [@ejin-14](https://github.com/ejin-14) |

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
