"""
Smoke-test for the IC Memo generation pipeline.

Run from project root:
    python scripts/test_memo_generator.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.agent_output import AgentOutput, ChairmanOutput, DataCollectionOutput, Vote
from src.models.simulation import DealFinancials
from src.services.memo_builder import build_memo
from src.services.memo_exporter import export_json, export_markdown, export_pptx
from src.services.shock_simulator import run_simulation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

OUT_DIR = Path("data/output")


# ── Mock agent outputs (skeleton values) ──────────────────────────────────────

DATA_COLLECTION = DataCollectionOutput(
    company_name="Acme AI",
    industry="AI / Machine Learning",
    key_facts=[
        "Acme AI operates in the AI infrastructure sector",
        "Revenue $12M FY2024, +180% YoY growth",
        "Gross margin 72%, burn rate $800K/month",
        "Top 3 customers represent 61% of ARR",
    ],
    data_sources=["Company IM (2024-12-01)", "Market Research 2025"],
)

FINANCIAL_OUTPUT = AgentOutput(
    agent_id="financial_analysis",
    section="Financial Analysis",
    findings=[
        "Revenue trajectory consistent with top-quartile SaaS benchmarks",
        "Gross margin expansion supports path to profitability by Year 3",
        "EV/Revenue entry multiple of 10x is within precedent range",
    ],
    concerns=[
        "Burn rate unsustainable beyond 18 months without additional capital",
        "Limited operating history — only 2 full fiscal years available",
    ],
    vote=Vote.CONDITIONAL,
    vote_rationale="Strong growth but burn management requires conditions.",
    confidence=0.72,
)

RISK_OUTPUT = AgentOutput(
    agent_id="risk",
    section="Risk Assessment",
    findings=["Risk profile manageable with proposed conditions"],
    concerns=[
        "Customer concentration — top 3 accounts = 61% ARR",
        "Key-person dependency on founding CTO",
        "Regulatory uncertainty — EU AI Act implementation timeline unclear",
        "Burn rate unsustainable beyond 18 months without Series C",
    ],
    vote=Vote.CONDITIONAL,
    vote_rationale="Several downside scenarios require mitigation before approval.",
    confidence=0.68,
)

BULL_OUTPUT = AgentOutput(
    agent_id="bull",
    section="Bull Case",
    findings=[
        "Category leader in AI infrastructure with strong network effects",
        "Large and growing TAM — $250B by 2028 at 38% CAGR",
        "Defensible moat through proprietary dataset and model fine-tuning IP",
        "Exceptional founding team with repeat exits in deep tech",
    ],
    concerns=[],
    vote=Vote.APPROVE,
    vote_rationale="Compelling risk/reward at current entry valuation.",
    confidence=0.80,
)

BEAR_OUTPUT = AgentOutput(
    agent_id="bear",
    section="Bear Case",
    findings=[
        "Hyperscaler commoditisation threatens margin sustainability",
        "Valuation premium leaves limited margin of safety in downside",
        "Customer concentration creates binary revenue risk",
        "Rising interest rates compress AI multiples sector-wide",
    ],
    concerns=[],
    vote=Vote.REJECT,
    vote_rationale="Risk/reward unfavourable at 10x revenue with these concentrations.",
    confidence=0.65,
)

CHAIRMAN_OUTPUT = ChairmanOutput(
    final_decision=Vote.CONDITIONAL,
    vote_tally={
        "financial_analysis": "CONDITIONAL",
        "risk": "CONDITIONAL",
        "bull": "APPROVE",
        "bear": "REJECT",
    },
    quorum_met=True,
    resolution_rationale=(
        "The committee reaches a CONDITIONAL approval. "
        "Acme AI presents a compelling growth story in a large market; "
        "however, customer concentration and burn rate require mitigation "
        "conditions prior to closing."
    ),
    conditions=[
        "Customer concentration covenant: top-3 ARR share below 50% within 18 months",
        "Series C milestone: signed term sheet before draw-down of tranche 2",
        "Management key-man insurance: CTO and CEO coverage of $10M each",
    ],
)


def test_full_memo_pipeline() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Simulation
    financials = DealFinancials(
        company_name="Acme AI",
        invested_capital_usd_m=30.0,
        revenue_usd_m=12.0,
        revenue_growth_rate=0.60,
        ebitda_margin=0.15,
        ev_revenue_multiple=10.0,
        holding_period_years=5,
        discount_rate=0.12,
        debt_usd_m=0.0,
        foreign_revenue_pct=0.40,
    )
    sim = run_simulation(financials)

    # Build memo
    memo = build_memo(
        company_name="Acme AI",
        industry="AI / Machine Learning",
        deal_stage="Series B",
        investment_amount_usd_m=30.0,
        data_collection=DATA_COLLECTION,
        financial_output=FINANCIAL_OUTPUT,
        risk_output=RISK_OUTPUT,
        bull_output=BULL_OUTPUT,
        bear_output=BEAR_OUTPUT,
        chairman_output=CHAIRMAN_OUTPUT,
        simulation=sim,
    )

    # JSON
    json_path = OUT_DIR / "acme_ai_memo.json"
    export_json(memo, json_path)
    print(f"JSON  → {json_path}")

    # Markdown
    md_path = OUT_DIR / "acme_ai_memo.md"
    md_content = export_markdown(memo, md_path)
    print(f"MD    → {md_path}")
    print("\n-- Markdown Preview (first 600 chars) -------------------")
    preview = md_content[:600].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
    print(preview, "...")

    # PPTX
    pptx_path = OUT_DIR / "acme_ai_memo.pptx"
    export_pptx(memo, pptx_path)
    print(f"\nPPTX  → {pptx_path}")

    # Assertions
    assert json_path.exists()
    assert md_path.exists()
    assert pptx_path.exists()
    assert memo.recommendation.decision == Vote.CONDITIONAL
    assert len(memo.risks.risks) > 0
    assert len(memo.shock_summary.scenarios) > 0

    print("\ntest_full_memo_pipeline PASSED")


if __name__ == "__main__":
    test_full_memo_pipeline()
