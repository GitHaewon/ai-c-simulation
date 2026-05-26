import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class BullAgent(BaseAgent):
    """
    Constructs the strongest possible investment thesis (pro-deal advocate).
    Runs in parallel with Financial, Risk, Bear after DataCollection.
    Placeholder — LLM call wired in Phase 4.
    """

    agent_id = "bull"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        industry = state["industry"]
        output = AgentOutput(
            agent_id=self.agent_id,
            section="Bull Case",
            findings=[
                f"[placeholder] {company} is a category leader in {industry}",
                "[placeholder] Strong network effects and defensible moat",
                "[placeholder] Large and growing total addressable market",
                "[placeholder] Exceptional founding team with domain expertise",
            ],
            concerns=[],  # bull advocate minimises concerns
            vote=Vote.APPROVE,
            vote_rationale=(
                f"[placeholder] {company} represents a compelling opportunity "
                "with strong upside potential in a high-growth market."
            ),
            confidence=0.0,
        )
        return {
            "bull_output": output,
            "stage_log": ["bull: done"],
        }
