"""
Smoke-test for the LangGraph IC orchestrator.

Run from project root:
    python scripts/test_orchestrator.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.orchestrator import run_ic_simulation
from src.models.deal import DealInput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def test_full_workflow() -> None:
    deal = DealInput(
        company_name="Acme AI",
        industry="AI / Machine Learning",
        deal_stage="Series B",
        investment_amount_usd_m=30.0,
        shock_scenario="Interest rates rise 200bps",
    )

    state = run_ic_simulation(deal)

    print("\n── IC Simulation Result ──────────────────────────────────")
    print(f"Company        : {state['company_name']}")
    print(f"Stage log      : {state['stage_log']}")
    print(f"Error log      : {state['error_log']}")

    chairman = state.get("chairman_output")
    assert chairman is not None, "chairman_output must be present"
    print(f"\nFinal Decision : {chairman.final_decision.value}")
    print(f"Quorum met     : {chairman.quorum_met}")
    print(f"Vote tally     : {chairman.vote_tally}")
    print(f"Rationale      : {chairman.resolution_rationale}")
    print("──────────────────────────────────────────────────────────\n")

    # All four parallel agent outputs must be present
    for field in ("financial_output", "risk_output", "bull_output", "bear_output"):
        assert state.get(field) is not None, f"{field} must not be None"

    print("test_full_workflow PASSED")


def test_minimal_deal() -> None:
    """Verify the graph runs with minimum required inputs."""
    deal = DealInput(company_name="MinCo", industry="FinTech")
    state = run_ic_simulation(deal)
    assert state["chairman_output"] is not None
    print("test_minimal_deal PASSED")


if __name__ == "__main__":
    test_full_workflow()
    test_minimal_deal()
