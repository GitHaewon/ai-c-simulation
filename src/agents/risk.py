import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    """
    Devil's advocate — downside scenarios, concentration risk, exit risk.
    Runs in parallel with Financial, Bull, Bear after DataCollection.
    Placeholder — LLM call wired in Phase 4.
    """

    agent_id = "risk"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        shock = state.get("shock_scenario", "")
        output = AgentOutput(
            agent_id=self.agent_id,
            section="Risk Assessment",
            findings=[
                f"[placeholder] Key risks identified for {company}",
                "[placeholder] Market concentration risk assessed",
                "[placeholder] Exit pathway and liquidity risk reviewed",
                *(
                    [f"[placeholder] Shock scenario applied: {shock}"]
                    if shock
                    else []
                ),
            ],
            concerns=[
                "[placeholder] Regulatory environment uncertain",
                "[placeholder] Key-person dependency",
                "[placeholder] Limited comparable exits in sector",
            ],
            vote=Vote.CONDITIONAL,
            vote_rationale=(
                "[placeholder] Risk profile is manageable but several downside "
                "scenarios require mitigation conditions before approval."
            ),
            confidence=0.0,
        )
        return {
            "risk_output": output,
            "stage_log": ["risk: done"],
        }
