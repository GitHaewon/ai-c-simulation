import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class BearAgent(BaseAgent):
    """
    Constructs the strongest possible counter-thesis (anti-deal advocate).
    Runs in parallel with Financial, Risk, Bull after DataCollection.
    Placeholder — LLM call wired in Phase 4.
    """

    agent_id = "bear"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        industry = state["industry"]
        output = AgentOutput(
            agent_id=self.agent_id,
            section="Bear Case",
            findings=[
                f"[placeholder] {company} faces structural headwinds in {industry}",
                "[placeholder] Valuation premium leaves little margin of safety",
                "[placeholder] Competitive moat is narrower than it appears",
                "[placeholder] Macro environment poses near-term execution risk",
            ],
            concerns=[
                "[placeholder] Burn rate unsustainable beyond 18 months",
                "[placeholder] Customer concentration risk in top 3 accounts",
            ],
            vote=Vote.REJECT,
            vote_rationale=(
                f"[placeholder] {company}'s risk/reward profile is unfavourable "
                "at current valuation; recommend waiting for a better entry point."
            ),
            confidence=0.0,
        )
        return {
            "bear_output": output,
            "stage_log": ["bear: done"],
        }
