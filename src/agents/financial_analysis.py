import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class FinancialAnalysisAgent(BaseAgent):
    """
    Reviews financial model, valuation, and return scenarios.
    Runs in parallel with Risk, Bull, Bear after DataCollection.
    Placeholder — LLM call wired in Phase 4.
    """

    agent_id = "financial_analysis"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        output = AgentOutput(
            agent_id=self.agent_id,
            section="Financial Analysis",
            findings=[
                f"[placeholder] Valuation of {company} benchmarked against sector comps",
                "[placeholder] Revenue growth trajectory reviewed",
                "[placeholder] Unit economics assessed",
            ],
            concerns=[
                "[placeholder] Limited operating history",
                "[placeholder] Path to profitability unclear",
            ],
            vote=Vote.CONDITIONAL,
            vote_rationale=(
                f"[placeholder] {company} shows promising growth but valuation "
                "requires additional diligence on burn rate and gross margins."
            ),
            confidence=0.0,  # populated by LLM in Phase 4
        )
        return {
            "financial_output": output,
            "stage_log": ["financial_analysis: done"],
        }
